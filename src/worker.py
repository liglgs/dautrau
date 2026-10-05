"""Database-backed single-agent worker; live mode never substitutes fixture output."""

import logging
import time
from datetime import timedelta

from sqlalchemy import select

from src.ai.model import choose_action, extract
from src.api.vmec_routes import create_draft
from src.db import CaseRecord, ReviewRecord, RunRecord, SessionLocal, TaskRecord, now, uid
from src.vmec import TYPES, DomainError, add_evidence, catalog_candidates, compare, source_dict, visible_sources

log = logging.getLogger(__name__)


def claim() -> str | None:
    with SessionLocal.begin() as db:
        run = db.scalar(select(RunRecord).where((RunRecord.status == "queued") | ((RunRecord.status == "running") & (RunRecord.lease_until < now()))).order_by(RunRecord.created_at).with_for_update(skip_locked=True).limit(1))
        if not run:
            return None
        run.status, run.lease_until = "running", now() + timedelta(minutes=3)
        return run.id


def save_checkpoint(run_id: str, state: dict, audit_entry: str | None = None):
    with SessionLocal.begin() as db:
        run = db.get(RunRecord, run_id)
        run.checkpoint = state
        run.lease_until = now() + timedelta(minutes=3)
        if audit_entry:
            case = db.get(CaseRecord, run.case_id)
            case.audit = [*case.audit, audit_entry]


def save_failure(run_id: str, error: DomainError):
    with SessionLocal.begin() as db:
        run = db.get(RunRecord, run_id)
        case = db.get(CaseRecord, run.case_id)
        run.status = "failed" if error.code != "BUDGET_EXHAUSTED" else "budget_exhausted"
        run.error = error.code
        run.lease_until = None
        case.audit = [*case.audit, f"Agent: {error.code}; chưa tạo kết luận"]


def process_run(run_id: str):
    with SessionLocal() as db:
        run = db.get(RunRecord, run_id)
        case = db.get(CaseRecord, run.case_id)
        sources = [(source_dict(s), s.id) for s in visible_sources(case)]
        prior_assertions = list(case.assertions)
        prior_issues = list(case.issues)
        response_trigger = bool(run.trigger_event_id and run.trigger_event_id.startswith("response:"))
        state = dict(run.checkpoint or {"decisions": 0, "tools": 0, "per_issue": {}})
    assertions = list(prior_assertions)
    known_sources = {(a.get("source_id"), a.get("source_version")) for a in assertions}
    for source, _ in sources:
        if (source["source_id"], source["version"]) in known_sources:
            continue
        # Each source is immutable. Model output is only a proposal until span checks pass.
        values = extract(source["text"], source["kind"])
        for value in values:
            if not isinstance(value, dict) or value.get("assertion_type") not in TYPES or not isinstance(value.get("name"), str) or not isinstance(value.get("quote"), str) or value["quote"] not in source["text"] or any(isinstance(value.get(field), str) and value[field].casefold() not in value["quote"].casefold() for field in ("name", "dose", "frequency")):
                raise DomainError(422, "EXTRACTION_INVALID", "Mô hình trả dữ kiện hoặc nguồn không hợp lệ.")
            with SessionLocal.begin() as db:
                run = db.get(RunRecord, run_id)
                case = db.scalar(select(CaseRecord).where(CaseRecord.id == run.case_id).with_for_update())
                source_record = next(s for s in case.sources if s.source_id == source["source_id"] and s.version == source["version"])
                eid = add_evidence(db, case, source_record, value["quote"])
            candidates = catalog_candidates(value["name"], value.get("dose"))
            assertion = {"id": uid("AST"), "revision": 1, "name": value["name"], "product": candidates[0]["code"] if len(candidates) == 1 else None,
                         "dose": value.get("dose") if isinstance(value.get("dose"), str) else None,
                         "frequency": value.get("frequency") if isinstance(value.get("frequency"), str) else None,
                         "side": "order" if source["kind"] == "admission_order" else "history",
                         "assertion_type": value["assertion_type"], "evidence_ids": [eid], "source_id": source["source_id"], "source_version": source["version"]}
            assertions.append(assertion)
    with SessionLocal.begin() as db:
        run = db.get(RunRecord, run_id)
        case = db.scalar(select(CaseRecord).where(CaseRecord.id == run.case_id).with_for_update())
        if case.input_revision != run.input_revision:
            run.input_revision = case.input_revision
            run.status = "queued"
            run.lease_until = None
            return
        case.assertions = assertions
        case.issues = prior_issues if response_trigger and len(assertions) == len(prior_assertions) else compare(assertions, prior_issues)
        case.extraction_pending = False
        case.revision += 1
        case.audit = [*case.audit, f"Agent: trích xuất {len(assertions)} dữ kiện, đối chiếu {len(case.issues)} vấn đề"]
        issues = list(case.issues)
    waiting = False
    for issue in issues:
        if issue["work_status"] in ("closed", "handed_off"):
            continue
        with SessionLocal() as db:
            task = db.scalar(select(TaskRecord).where(TaskRecord.issue_id == issue["id"], TaskRecord.status == "open").limit(1))
            answered = db.scalar(select(TaskRecord).where(TaskRecord.issue_id == issue["id"], TaskRecord.status == "answered").limit(1))
        if task:
            waiting = True
            continue
        if answered:
            # Human response is evidence, never an automatic closure.
            continue
        notes: list[dict] = []
        searched = False
        per_issue = dict(state.get("per_issue", {}))
        counters = dict(per_issue.get(issue["id"], {"decisions": 0, "reads": 0, "writes": 0}))
        for step in range(3):
            if state["decisions"] >= 150 or state["tools"] >= 200 or counters["decisions"] >= 12:
                raise DomainError(422, "BUDGET_EXHAUSTED", "Hết ngân sách xử lý.")
            action = choose_action(issue, notes, step)
            state["decisions"] += 1
            counters["decisions"] += 1
            per_issue[issue["id"]] = counters
            state["per_issue"] = per_issue
            kind = action.get("action")
            if kind == "search_case_notes":
                if searched:
                    raise DomainError(422, "AGENT_REPEAT", "Agent lặp lại tìm kiếm mà không có bằng chứng mới.")
                if counters["reads"] >= 8:
                    raise DomainError(422, "BUDGET_EXHAUSTED", "Hết ngân sách công cụ đọc.")
                query = str(action.get("query") or issue["title"]).casefold()
                with SessionLocal() as db:
                    case = db.get(CaseRecord, run.case_id)
                    notes = [{"source_id": s.source_id, "version": s.version, "text": s.text[:2500]} for s in visible_sources(case) if s.kind == "clinical_note" and any(word in s.text.casefold() for word in query.split())][:5]
                state["tools"] += 1
                counters["reads"] += 1
                searched = True
                save_checkpoint(run_id, state, f"Agent: search_case_notes cho {issue['id']}")
                continue
            if counters["writes"] >= 4:
                raise DomainError(422, "BUDGET_EXHAUSTED", "Hết ngân sách công cụ ghi.")
            with SessionLocal.begin() as db:
                run = db.get(RunRecord, run_id)
                case = db.scalar(select(CaseRecord).where(CaseRecord.id == run.case_id).with_for_update())
                current = next((i for i in case.issues if i["id"] == issue["id"]), None)
                if not current or case.input_revision != run.input_revision:
                    run.status, run.lease_until = "queued", None
                    return
                if kind == "create_verification_task":
                    fields = action.get("missing_fields")
                    if not isinstance(fields, list) or not fields or any(not isinstance(f, str) for f in fields):
                        raise DomainError(422, "AGENT_ACTION_INVALID", "Agent chưa chỉ rõ trường cần xác minh.")
                    assignee = "responder"
                    dedupe = f"{issue['id']}:{assignee}:{','.join(sorted(fields))}"
                    task = db.scalar(select(TaskRecord).where(TaskRecord.dedupe_key == dedupe, TaskRecord.status == "open"))
                    if not task:
                        task = TaskRecord(id=uid("TASK"), case_id=case.id, issue_id=issue["id"], assignee=assignee, question=str(action.get("question") or issue["title"]), missing_fields=fields, evidence_ids=current["evidence_ids"], status="open", dedupe_key=dedupe)
                        db.add(task)
                    changed = {**current, "work_status": "waiting_response", "revision": current["revision"] + 1}
                    waiting = True
                elif kind == "propose_issue_update":
                    changed = {**current, "work_status": "ready_for_review", "evidence_status": "documented_explanation" if notes else current["evidence_status"], "proposed_update": str(action.get("proposal") or "Cần người rà soát"), "revision": current["revision"] + 1}
                else:
                    raise DomainError(422, "AGENT_ACTION_INVALID", "Hành động agent không hợp lệ.")
                case.issues = [changed if i["id"] == issue["id"] else i for i in case.issues]
                case.revision += 1
                case.audit = [*case.audit, f"Agent: {kind} cho {issue['id']}"]
                state["tools"] += 1
                counters["writes"] += 1
                run.checkpoint = state
                run.lease_until = now() + timedelta(minutes=3)
            break
        else:
            raise DomainError(422, "BUDGET_EXHAUSTED", "Agent không chọn được bước phù hợp.")
    with SessionLocal.begin() as db:
        run = db.get(RunRecord, run_id)
        case = db.get(CaseRecord, run.case_id)
        run.status = "waiting_event" if waiting else "completed"
        run.lease_until = None
        run.checkpoint = state
        if case.lifecycle == "changes_pending" and not db.scalar(select(ReviewRecord).where(ReviewRecord.case_id == case.id, ReviewRecord.case_revision == case.revision, ReviewRecord.status == "draft").limit(1)):
            create_draft(db, case)


def process_once() -> bool:
    run_id = claim()
    if not run_id:
        return False
    try:
        process_run(run_id)
    except DomainError as exc:
        log.warning("Run %s failed: %s", run_id, exc.code)
        save_failure(run_id, exc)
    except Exception:
        log.exception("Unexpected worker failure for %s", run_id)
        save_failure(run_id, DomainError(503, "WORKER_ERROR", "Xử lý thất bại.", True))
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        if not process_once():
            time.sleep(1)
