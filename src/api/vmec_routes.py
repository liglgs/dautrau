"""Versioned application API. Mutations are committed with their idempotency receipt."""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.security import check_origin, clinician, current_user, new_session, password_hash, reviewer, token_hash
from src.config import get_settings
from src.db import (
    CaseRecord,
    HandoffRecord,
    LoginSession,
    ReceiptRecord,
    ReviewRecord,
    RunRecord,
    SourceRecord,
    TaskRecord,
    User,
    get_db,
    uid,
)
from src.vmec import (
    DomainError,
    add_evidence,
    add_sources,
    checksum,
    evidence_dict,
    parse_import,
    source_dict,
    visible_sources,
)

router = APIRouter()


def user_dict(user: User) -> dict:
    return {"id": user.id, "name": user.name, "role": user.role}


def task_dict(task: TaskRecord) -> dict:
    return {k: getattr(task, k) for k in ("id", "case_id", "issue_id", "revision", "assignee", "question", "missing_fields", "evidence_ids", "status", "response", "reason")}


def handoff_dict(h: HandoffRecord) -> dict:
    return {k: getattr(h, k) for k in ("id", "case_id", "issue_id", "revision", "recipient", "reason", "acknowledged")}


def review_dict(r: ReviewRecord) -> dict:
    return {k: getattr(r, k) for k in ("id", "case_id", "revision", "case_revision", "status", "approved_by", "approved_at", "snapshot")}


def run_dict(run: RunRecord) -> dict:
    return {"id": run.id, "status": run.status, "error": run.error}


def get_case(db: Session, case_id: str, user: User, lock: bool = False) -> CaseRecord:
    stmt = select(CaseRecord).where(CaseRecord.id == case_id)
    if lock:
        stmt = stmt.with_for_update()
    case = db.scalar(stmt)
    if not case or user.id not in case.assigned or user.role == "responder":
        raise DomainError(404, "NOT_FOUND", "Không tìm thấy ca trong phạm vi được cấp.")
    return case


def latest_run(db: Session, case_id: str) -> RunRecord | None:
    return db.scalar(select(RunRecord).where(RunRecord.case_id == case_id).order_by(RunRecord.created_at.desc(), RunRecord.id.desc()).limit(1))


def case_dict(db: Session, case: CaseRecord) -> dict:
    sources = visible_sources(case)
    source_keys = {(s.source_id, s.version) for s in sources}
    return {
        "id": case.id, "patient_id": case.patient_id, "encounter_id": case.encounter_id,
        "reconciliation_at": case.reconciliation_at, "visible_at": case.visible_at,
        "lifecycle": case.lifecycle, "revision": case.revision, "input_revision": case.input_revision,
        "assigned": case.assigned, "scenario": case.scenario, "run": run_dict(latest_run(db, case.id)) if latest_run(db, case.id) else None,
        "sources": [source_dict(s) for s in sources],
        "evidence": [evidence_dict(e) for e in case.evidence if (e.source_id, e.version) in source_keys],
        "assertions": case.assertions, "issues": case.issues, "audit": case.audit,
        "extraction_pending": case.extraction_pending,
    }


def revision(current: int, expected: int | None):
    if expected is None or current != expected:
        raise DomainError(409, "REVISION_CONFLICT", f"Phiên bản đã đổi (hiện tại: {current}). Hãy tải lại.")


def required(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainError(422, "REQUIRED", f"Cần nhập {label}.")
    return value.strip()


def validate_evidence(case: CaseRecord, ids: list) -> list[str]:
    sources = {(s.source_id, s.version): s for s in visible_sources(case)}
    known = {
        e.id for e in case.evidence
        if (source := sources.get((e.source_id, e.version))) is not None
        and source.text[e.start:e.end] == e.quote
    }
    if not isinstance(ids, list) or not ids or any(e not in known for e in ids):
        raise DomainError(422, "EVIDENCE_REQUIRED", "Cần nguồn hợp lệ thuộc ca này.")
    return list(dict.fromkeys(ids))


def touch(case: CaseRecord, message: str, *, input_change: bool = False):
    case.revision += 1
    if input_change:
        case.input_revision += 1
    case.audit = [*case.audit, message]
    if case.lifecycle == "approved":
        case.lifecycle = "changes_pending"


def reopen_affected(case: CaseRecord, texts: list[str]):
    """For small synthetic cases, reopen issues whose referenced drug occurs in new text."""
    combined = "\n".join(texts).casefold()
    assertion_names = {a["id"]: a["name"].casefold() for a in case.assertions}
    changed = []
    for issue in case.issues:
        names = [assertion_names.get(ref) for ref in issue.get("assertion_refs", [])]
        if any(name and name in combined for name in names):
            issue = {**issue, "revision": issue["revision"] + 1,
                     "evidence_generation": issue.get("evidence_generation", 0) + 1,
                     "work_status": "new", "evidence_status": "unknown",
                     "history": [*issue.get("history", []), f"Trước nguồn mới: {issue['evidence_status']}"]}
            issue.pop("confirmation", None)
        changed.append(issue)
    case.issues = changed


def perform(db: Session, request: Request, actor: str, payload: object, action):
    check_origin(request)
    key = request.headers.get("Idempotency-Key")
    if not key or len(key) > 160:
        raise DomainError(422, "IDEMPOTENCY_REQUIRED", "Thiếu Idempotency-Key hợp lệ.")
    payload_hash = checksum(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str))
    old = db.scalar(select(ReceiptRecord).where(ReceiptRecord.actor == actor, ReceiptRecord.method == request.method, ReceiptRecord.path == request.url.path, ReceiptRecord.key == key))
    if old:
        if old.payload_hash != payload_hash:
            raise DomainError(409, "IDEMPOTENCY_CONFLICT", "Khóa thao tác đã dùng cho nội dung khác.")
        return old.response
    result = action()
    db.add(ReceiptRecord(actor=actor, method=request.method, path=request.url.path, key=key, payload_hash=payload_hash, status_code=200, response=result))
    db.commit()
    return result


@router.post("/sessions")
def login(request: Request, response: Response, body: dict, db: Session = Depends(get_db)):
    check_origin(request)
    user = db.get(User, body.get("user_id", ""))
    if not user or not password_hash.verify(body.get("password", ""), user.password_hash):
        raise DomainError(401, "INVALID_CREDENTIALS", "Tài khoản hoặc mật khẩu không đúng.")
    token = new_session(db, user)
    db.commit()
    response.set_cookie("medreview_session", token, httponly=True, secure=get_settings().session_cookie_secure, samesite="lax", max_age=8*3600, path="/")
    return user_dict(user)


@router.get("/sessions/current")
def session_current(user: User = Depends(current_user)):
    return user_dict(user)


@router.delete("/sessions/current")
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    check_origin(request)
    db.delete(db.get(LoginSession, token_hash(request.cookies["medreview_session"])))
    db.commit()
    response.delete_cookie("medreview_session", path="/")
    return {"ok": True}


@router.get("/cases")
def cases(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == "responder":
        return []
    return [case_dict(db, c) for c in db.scalars(select(CaseRecord).order_by(CaseRecord.id)) if user.id in c.assigned]


@router.get("/cases/{case_id}")
def case_detail(case_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return case_dict(db, get_case(db, case_id, user))


async def upload_parts(manifest: str, files: list[UploadFile]) -> tuple[dict, list[dict]]:
    return parse_import(manifest, [(f.filename or "", await f.read()) for f in files])


@router.post("/cases/import")
async def import_case(request: Request, manifest: str = Form(...), files: list[UploadFile] = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviewer(user)
    m, docs = await upload_parts(manifest, files)
    def action():
        if db.get(CaseRecord, m["case_id"]):
            raise DomainError(409, "CASE_EXISTS", "Mã ca đã tồn tại.")
        case = CaseRecord(id=m["case_id"], patient_id=m["patient_id"], encounter_id=m["encounter_id"], reconciliation_at=m["reconciliation_at"], visible_at=m["initial_visible_at"], assigned=list(dict.fromkeys([user.id, "reviewer", "clinician", "clinician2"])), assertions=[], issues=[], audit=["Đã nhập gói TXT/JSON"], extraction_pending=True)
        db.add(case)
        db.flush()
        add_sources(db, case, docs)
        return {"case_id": case.id, "source_count": len(docs), "receipt": uid("IMPORT")}
    return perform(db, request, user.id, {"manifest": m, "sources": [(d["filename"], d["checksum"]) for d in docs]}, action)


@router.post("/cases/{case_id}/sources")
async def append_sources(case_id: str, request: Request, manifest: str = Form(...), files: list[UploadFile] = File(...), expected_revision: int = Form(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviewer(user)
    case = get_case(db, case_id, user, True)
    m, docs = await upload_parts(manifest, files)
    parse_import(manifest, [(d["filename"], d["text"].encode()) for d in docs], case=case)
    def action():
        revision(case.revision, expected_revision)
        add_sources(db, case, docs)
        reopen_affected(case, [d["text"] for d in docs])
        case.extraction_pending = True
        touch(case, f"{user.name}: bổ sung nguồn; cần rà lại", input_change=True)
        enqueue_successor(db, case, f"source:{request.headers['Idempotency-Key']}")
        return {"case_id": case.id, "source_count": len(docs), "receipt": uid("SOURCE")}
    return perform(db, request, user.id, {"manifest": m, "sources": [(d["filename"], d["checksum"]) for d in docs], "revision": expected_revision}, action)


@router.get("/cases/{case_id}/sources")
def case_sources(case_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [source_dict(s) for s in visible_sources(get_case(db, case_id, user))]


@router.get("/cases/{case_id}/evidence/{evidence_id}")
def evidence(case_id: str, evidence_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    case = get_case(db, case_id, user)
    e = next((e for e in case.evidence if e.id == evidence_id), None)
    if not e or (e.source_id, e.version) not in {(s.source_id, s.version) for s in visible_sources(case)}:
        raise DomainError(404, "NOT_FOUND", "Không tìm thấy evidence.")
    return evidence_dict(e)


@router.get("/cases/{case_id}/assertions")
def assertions(case_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_case(db, case_id, user).assertions


@router.get("/cases/{case_id}/issues")
def issues(case_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_case(db, case_id, user).issues


@router.get("/cases/{case_id}/timeline")
def timeline(case_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"source_id": s.source_id, "event_time": s.event_time, "label": s.filename} for s in visible_sources(get_case(db, case_id, user))]


@router.get("/cases/{case_id}/audit")
def audit(case_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_case(db, case_id, user).audit


@router.post("/cases/{case_id}/runs")
def start_run(case_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviewer(user)
    case = get_case(db, case_id, user, True)
    def action():
        revision(case.revision, body.get("expected_revision"))
        active = db.scalar(select(RunRecord).where(RunRecord.case_id == case_id, RunRecord.status.in_(["queued", "running", "waiting_event"])).limit(1))
        if active:
            return run_dict(active)
        previous = latest_run(db, case_id)
        if previous and previous.status in ("failed", "budget_exhausted"):
            required(body.get("reason"), "lý do chạy lại")
        run = RunRecord(id=uid("RUN"), case_id=case_id, status="queued", input_revision=case.input_revision, checkpoint={"decisions": 0, "tools": 0, "per_issue": {}})
        db.add(run)
        if case.lifecycle == "draft":
            case.lifecycle = "reviewing"
        touch(case, f"{user.name}: bắt đầu lượt xử lý")
        return run_dict(run)
    return perform(db, request, user.id, body, action)


@router.get("/runs/{run_id}")
def run_detail(run_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    run = db.get(RunRecord, run_id)
    if not run:
        raise DomainError(404, "NOT_FOUND", "Không tìm thấy lượt chạy.")
    get_case(db, run.case_id, user)
    return run_dict(run)


def issue_case(db: Session, issue_id: str, user: User) -> tuple[CaseRecord, dict]:
    for candidate in db.scalars(select(CaseRecord)):
        if any(i["id"] == issue_id for i in candidate.issues):
            case = get_case(db, candidate.id, user, True)
            return case, next(i for i in case.issues if i["id"] == issue_id)
    raise DomainError(404, "NOT_FOUND", "Không tìm thấy vấn đề.")


def replace_issue(case: CaseRecord, changed: dict):
    case.issues = [changed if i["id"] == changed["id"] else i for i in case.issues]


@router.patch("/cases/{case_id}/assertions/{assertion_id}")
def edit_assertion(case_id: str, assertion_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviewer(user)
    case = get_case(db, case_id, user, True)
    def action():
        revision(case.revision, body.get("expected_revision"))
        assertion = next((a for a in case.assertions if a["id"] == assertion_id), None)
        if not assertion:
            raise DomainError(404, "NOT_FOUND", "Không tìm thấy dữ kiện.")
        ids = validate_evidence(case, body.get("evidence_ids"))
        changed = dict(assertion)
        for field in ("name", "product", "dose", "frequency"):
            if field in body:
                if body[field] is not None and not isinstance(body[field], str):
                    raise DomainError(422, "INVALID_ASSERTION", "Giá trị dữ kiện không hợp lệ.")
                changed[field] = body[field]
        required(changed.get("name"), "tên thuốc")
        changed["evidence_ids"] = ids
        changed["revision"] += 1
        case.assertions = [changed if a["id"] == assertion_id else a for a in case.assertions]
        # Affected issues are recomputed by the next run, never silently confirmed.
        for issue in case.issues:
            if assertion_id in issue.get("assertion_refs", []):
                issue = dict(issue)
                issue["history"] = [*issue.get("history", []), f"Xác nhận cũ: {issue['evidence_status']}"]
                issue["evidence_status"] = "unknown"
                issue["work_status"] = "new"
                issue["revision"] += 1
                issue["evidence_generation"] = issue.get("evidence_generation", 0) + 1
                issue.pop("confirmation", None)
                replace_issue(case, issue)
        touch(case, f"{user.name}: sửa dữ kiện có nguồn", input_change=True)
        return changed
    return perform(db, request, user.id, body, action)


@router.get("/tasks")
def tasks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    all_tasks = db.scalars(select(TaskRecord).order_by(TaskRecord.id)).all()
    return [task_dict(t) for t in all_tasks if t.assignee == user.id or (user.role in ("reviewer", "clinician") and user.id in db.get(CaseRecord, t.case_id).assigned)]


def permitted_task(db: Session, task_id: str, user: User) -> TaskRecord:
    task = db.get(TaskRecord, task_id)
    if not task:
        raise DomainError(404, "NOT_FOUND", "Không tìm thấy nhiệm vụ.")
    if task.assignee != user.id and not (user.role in ("reviewer", "clinician") and user.id in db.get(CaseRecord, task.case_id).assigned):
        raise DomainError(404, "NOT_FOUND", "Không tìm thấy nhiệm vụ.")
    return task


@router.get("/tasks/{task_id}")
def task_detail(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = permitted_task(db, task_id, user)
    case = db.get(CaseRecord, task.case_id)
    visible_keys = {(s.source_id, s.version) for s in visible_sources(case)}
    snippets = [evidence_dict(e) for e in case.evidence
                if e.id in task.evidence_ids and (e.source_id, e.version) in visible_keys]
    if user.role == "responder":
        snippets = [{**e, "context": e["quote"]} for e in snippets]
    return {**task_dict(task), "shared_evidence": snippets}


def enqueue_successor(db: Session, case: CaseRecord, trigger: str):
    current = latest_run(db, case.id)
    if current is None:
        return  # first run is explicitly started by a reviewer
    if current and current.status in ("queued", "running", "waiting_event"):
        if current.status == "waiting_event":
            current.status = "queued"
            current.input_revision = case.input_revision
            current.trigger_event_id = trigger
        return
    if current and current.trigger_event_id == trigger:
        return
    db.add(RunRecord(id=uid("RUN"), case_id=case.id, status="queued", input_revision=case.input_revision, parent_run_id=current.id if current else None, trigger_event_id=trigger, checkpoint={"decisions": 0, "tools": 0, "per_issue": {}}))


@router.post("/tasks/{task_id}/responses")
def respond(task_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = permitted_task(db, task_id, user)
    def action():
        case = db.scalar(select(CaseRecord).where(CaseRecord.id == task.case_id).with_for_update())
        revision(task.revision, body.get("expected_revision"))
        if task.status != "open":
            raise DomainError(409, "TASK_CLOSED", "Nhiệm vụ không còn mở.")
        response = required(body.get("response"), "phản hồi")
        if len(response) > 12000 or len(case.sources) >= 30:
            raise DomainError(422, "SOURCE_LIMIT", "Phản hồi hoặc số nguồn vượt giới hạn.")
        task.status, task.response, task.revision = "answered", response, task.revision + 1
        sid = uid("RESP")
        source = SourceRecord(case_id=case.id, source_id=sid, version=1, kind="verification_response", filename=f"{sid}.txt", author_role=user.role, event_time=None, recorded_at=case.visible_at, available_at=case.visible_at, text=response, checksum=checksum(response))
        db.add(source)
        db.flush()
        eid = add_evidence(db, case, source, response)
        issue = next(i for i in case.issues if i["id"] == task.issue_id)
        issue = {**issue, "work_status": "ready_for_review", "revision": issue["revision"] + 1, "evidence_generation": issue.get("evidence_generation", 0) + 1, "evidence_ids": list(dict.fromkeys([*issue["evidence_ids"], eid]))}
        replace_issue(case, issue)
        touch(case, f"{user.name}: phản hồi; chờ rà soát", input_change=True)
        enqueue_successor(db, case, f"response:{task.id}")
        return {"receipt": uid("RESPONSE"), "task": task_dict(task)}
    return perform(db, request, user.id, body, action)


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviewer(user)
    task = permitted_task(db, task_id, user)
    def action():
        case = db.scalar(select(CaseRecord).where(CaseRecord.id == task.case_id).with_for_update())
        revision(task.revision, body.get("expected_revision"))
        if task.status != "open":
            raise DomainError(409, "TASK_CLOSED", "Nhiệm vụ không còn mở.")
        task.reason = required(body.get("reason"), "lý do hủy")
        task.status, task.revision = "cancelled", task.revision + 1
        issue = next(i for i in case.issues if i["id"] == task.issue_id)
        replace_issue(case, {**issue, "work_status": "ready_for_review", "revision": issue["revision"] + 1})
        touch(case, f"{user.name}: hủy nhiệm vụ có lý do")
        return task_dict(task)
    return perform(db, request, user.id, body, action)


@router.post("/issues/{issue_id}/tasks")
def create_task(issue_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviewer(user)
    case, issue = issue_case(db, issue_id, user)
    def action():
        revision(issue["revision"], body.get("expected_revision"))
        if issue["work_status"] in ("closed", "handed_off"):
            raise DomainError(409, "ISSUE_CLOSED", "Vấn đề đã kết thúc.")
        assignee = required(body.get("assignee"), "người nhận")
        if assignee != "responder" and assignee not in case.assigned:
            raise DomainError(422, "ASSIGNEE_REQUIRED", "Người nhận chưa được phân công.")
        question = required(body.get("question"), "câu hỏi")
        field = required(body.get("missing_field"), "trường cần xác minh")
        ids = validate_evidence(case, body.get("evidence_ids"))
        dedupe = f"{issue_id}:{assignee}:{field}"
        old = db.scalar(select(TaskRecord).where(TaskRecord.dedupe_key == dedupe, TaskRecord.status == "open"))
        if old:
            return task_dict(old)
        task = TaskRecord(id=uid("TASK"), case_id=case.id, issue_id=issue_id, revision=1, assignee=assignee, question=question, missing_fields=[field], evidence_ids=ids, status="open", dedupe_key=dedupe)
        db.add(task)
        replace_issue(case, {**issue, "work_status": "waiting_response", "revision": issue["revision"] + 1})
        touch(case, f"{user.name}: tạo yêu cầu xác minh")
        return task_dict(task)
    return perform(db, request, user.id, body, action)


@router.post("/issues/{issue_id}/confirmations")
def confirm(issue_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviewer(user)
    case, issue = issue_case(db, issue_id, user)
    def action():
        revision(issue["revision"], body.get("expected_revision"))
        kind = body.get("type")
        allowed = {"confirmed_information_resolved", "confirmed_no_difference", "confirmed_intentional", "confirmed_unintentional"}
        if kind not in allowed:
            raise DomainError(422, "INVALID_CONFIRMATION", "Loại xác nhận không phù hợp vấn đề.")
        if (issue["type"] == "information_gap") != (kind == "confirmed_information_resolved"):
            raise DomainError(422, "INVALID_CONFIRMATION", "Loại xác nhận không phù hợp vấn đề.")
        if kind in ("confirmed_intentional", "confirmed_unintentional"):
            clinician(user)
        reason = required(body.get("reason"), "lý do")
        ids = validate_evidence(case, body.get("evidence_ids"))
        details = {}
        if kind == "confirmed_information_resolved":
            fields = body.get("verified_fields")
            if not isinstance(fields, list) or not fields or any(not isinstance(field, str) or not field.strip() for field in fields):
                raise DomainError(422, "VERIFIED_FIELDS_REQUIRED", "Cần nêu trường đã xác minh.")
            details["verified_fields"] = list(dict.fromkeys(field.strip() for field in fields))
        elif kind == "confirmed_no_difference":
            refs = body.get("compared_assertion_ids")
            fields = body.get("comparison_fields")
            issue_refs = set(issue.get("assertion_refs", []))
            if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs) or len(set(refs)) < 2 or not all(ref in issue_refs for ref in refs):
                raise DomainError(422, "COMPARISON_ASSERTIONS_REQUIRED", "Cần đối chiếu ít nhất hai dữ kiện của vấn đề.")
            if not isinstance(fields, list) or not fields or any(field not in {"product", "presence", "dose", "frequency"} for field in fields):
                raise DomainError(422, "COMPARISON_FIELDS_REQUIRED", "Cần nêu trường đã đối chiếu.")
            details = {"compared_assertion_ids": list(dict.fromkeys(refs)), "comparison_fields": list(dict.fromkeys(fields))}
        changed = {**issue, "confirmation": {"type": kind, "reason": reason, "actor": user.id, "evidence_ids": ids, **details}, "evidence_status": kind, "work_status": "ready_for_review", "revision": issue["revision"] + 1}
        replace_issue(case, changed)
        touch(case, f"{user.name}: xác nhận {issue_id}")
        return changed
    return perform(db, request, user.id, body, action)


@router.post("/issues/{issue_id}/close")
def close_issue(issue_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviewer(user)
    case, issue = issue_case(db, issue_id, user)
    def action():
        revision(issue["revision"], body.get("expected_revision"))
        confirmation = issue.get("confirmation")
        if not confirmation or confirmation["type"] not in ("confirmed_information_resolved", "confirmed_no_difference", "confirmed_intentional", "confirmed_unintentional"):
            raise DomainError(422, "CONFIRMATION_REQUIRED", "Cần xác nhận có nguồn trước khi đóng.")
        if confirmation["type"] in ("confirmed_intentional", "confirmed_unintentional"):
            clinician(user)
        if db.scalar(select(TaskRecord).where(TaskRecord.issue_id == issue_id, TaskRecord.status == "open").limit(1)):
            raise DomainError(422, "TASK_OPEN", "Cần trả lời hoặc hủy nhiệm vụ trước khi đóng.")
        changed = {**issue, "work_status": "closed", "revision": issue["revision"] + 1}
        replace_issue(case, changed)
        touch(case, f"{user.name}: đóng {issue_id}")
        return changed
    return perform(db, request, user.id, body, action)


@router.post("/issues/{issue_id}/handoffs")
def handoff(issue_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviewer(user)
    case, issue = issue_case(db, issue_id, user)
    def action():
        revision(issue["revision"], body.get("expected_revision"))
        recipient = required(body.get("recipient"), "người nhận")
        reason = required(body.get("reason"), "lý do bàn giao")
        if recipient == user.id or recipient not in case.assigned:
            raise DomainError(422, "INVALID_RECIPIENT", "Người nhận phải được phân công ca và khác người gửi.")
        old = db.scalar(select(HandoffRecord).where(HandoffRecord.issue_id == issue_id, HandoffRecord.acknowledged.is_(False)))
        if old:
            return handoff_dict(old)
        h = HandoffRecord(id=uid("HANDOFF"), case_id=case.id, issue_id=issue_id, revision=1, recipient=recipient, reason=reason)
        db.add(h)
        replace_issue(case, {**issue, "revision": issue["revision"] + 1})
        touch(case, f"{user.name}: đề nghị bàn giao")
        return handoff_dict(h)
    return perform(db, request, user.id, body, action)


@router.get("/handoffs")
def handoffs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [handoff_dict(h) for h in db.scalars(select(HandoffRecord)) if h.recipient == user.id or (user.role in ("reviewer", "clinician") and user.id in db.get(CaseRecord, h.case_id).assigned)]


@router.post("/handoffs/{handoff_id}/ack")
def ack(handoff_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    h = db.get(HandoffRecord, handoff_id)
    if not h or user.id != h.recipient:
        raise DomainError(404, "NOT_FOUND", "Không tìm thấy bàn giao được giao.")
    def action():
        case = db.scalar(select(CaseRecord).where(CaseRecord.id == h.case_id).with_for_update())
        revision(h.revision, body.get("expected_revision"))
        issue = next(i for i in case.issues if i["id"] == h.issue_id)
        if issue["work_status"] == "closed":
            raise DomainError(409, "ISSUE_CLOSED", "Vấn đề đã đóng.")
        h.acknowledged, h.revision = True, h.revision + 1
        for task in db.scalars(select(TaskRecord).where(TaskRecord.issue_id == h.issue_id, TaskRecord.status == "open")):
            task.status = "handed_off"
            task.revision += 1
        replace_issue(case, {**issue, "work_status": "handed_off", "evidence_status": "inconclusive", "revision": issue["revision"] + 1})
        touch(case, f"{user.name}: nhận bàn giao")
        return handoff_dict(h)
    return perform(db, request, user.id, body, action)


def create_draft(db: Session, case: CaseRecord) -> ReviewRecord:
    snapshot = {"assertions": case.assertions, "issues": case.issues, "sources": [source_dict(s) for s in visible_sources(case)], "evidence": [evidence_dict(e) for e in case.evidence], "audit": case.audit, "reconciliation_at": case.reconciliation_at, "interaction_warning": "Tương tác thuốc chưa được đánh giá"}
    review = ReviewRecord(id=uid("REV"), case_id=case.id, revision=1, case_revision=case.revision, status="draft", snapshot=snapshot)
    db.add(review)
    return review


def validate_approval(db: Session, case: CaseRecord):
    source_by_key = {(s.source_id, s.version): s for s in visible_sources(case)}
    evidence = {e.id: e for e in case.evidence}
    def valid(ids: list[str]) -> bool:
        return bool(ids) and all(
            eid in evidence and
            (evidence[eid].source_id, evidence[eid].version) in source_by_key and
            source_by_key[(evidence[eid].source_id, evidence[eid].version)].text[evidence[eid].start:evidence[eid].end] == evidence[eid].quote
            for eid in ids
        )
    if any(not valid(a.get("evidence_ids", [])) for a in case.assertions):
        raise DomainError(422, "INVALID_EVIDENCE", "Dữ kiện thiếu nguồn hợp lệ.")
    if db.scalar(select(TaskRecord).where(TaskRecord.case_id == case.id, TaskRecord.status == "open").limit(1)):
        raise DomainError(422, "TASK_OPEN", "Còn nhiệm vụ xác minh đang mở.")
    for issue in case.issues:
        if issue["work_status"] == "closed":
            confirmation = issue.get("confirmation")
            if not confirmation or confirmation.get("type") != issue["evidence_status"] or not valid(confirmation.get("evidence_ids", [])):
                raise DomainError(422, "INVALID_CONFIRMATION", "Vấn đề đóng thiếu xác nhận có nguồn.")
            if confirmation["type"] in ("confirmed_intentional", "confirmed_unintentional"):
                actor = db.get(User, confirmation.get("actor"))
                if not actor or actor.role != "clinician":
                    raise DomainError(422, "INVALID_CONFIRMATION", "Xác nhận ý định không thuộc bác sĩ.")
        if issue["work_status"] == "handed_off":
            handoff = db.scalar(select(HandoffRecord).where(HandoffRecord.issue_id == issue["id"], HandoffRecord.acknowledged.is_(True)).limit(1))
            if not handoff or issue["evidence_status"] != "inconclusive":
                raise DomainError(422, "HANDOFF_NOT_ACKNOWLEDGED", "Bàn giao chưa được nhận hợp lệ.")


@router.post("/cases/{case_id}/drafts")
def draft(case_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviewer(user)
    case = get_case(db, case_id, user, True)
    def action():
        revision(case.revision, body.get("expected_revision"))
        db.flush()
        return review_dict(create_draft(db, case))
    return perform(db, request, user.id, body, action)


@router.get("/cases/{case_id}/reviews")
def reviews(case_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_case(db, case_id, user)
    return [review_dict(r) for r in db.scalars(select(ReviewRecord).where(ReviewRecord.case_id == case_id).order_by(ReviewRecord.created_at, ReviewRecord.id))]


@router.get("/reviews/{review_id}")
def review_detail(review_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    review = db.get(ReviewRecord, review_id)
    if not review:
        raise DomainError(404, "NOT_FOUND", "Không tìm thấy phiên bản.")
    get_case(db, review.case_id, user)
    return review_dict(review)


@router.post("/reviews/{review_id}/approve")
def approve(review_id: str, request: Request, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    clinician(user)
    review = db.get(ReviewRecord, review_id)
    if not review:
        raise DomainError(404, "NOT_FOUND", "Không tìm thấy phiên bản.")
    case = get_case(db, review.case_id, user, True)
    def action():
        revision(review.revision, body.get("expected_revision"))
        revision(case.revision, body.get("expected_case_revision"))
        revision(case.revision, review.case_revision)
        if review.status != "draft" or case.extraction_pending or any(i["work_status"] not in ("closed", "handed_off") for i in case.issues):
            raise DomainError(422, "APPROVAL_BLOCKED", "Còn việc mở hoặc dữ kiện chưa kiểm tra.")
        validate_approval(db, case)
        for old in db.scalars(select(ReviewRecord).where(ReviewRecord.case_id == case.id, ReviewRecord.status == "approved")):
            old.status = "superseded"
        review.status, review.revision = "approved", review.revision + 1
        review.approved_by, review.approved_at = user.name, datetime.now(UTC).isoformat()
        case.lifecycle = "approved"
        case.audit = [*case.audit, f"{user.name}: duyệt {review.id}"]
        return review_dict(review)
    return perform(db, request, user.id, body, action)
