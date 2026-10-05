"""Deterministic import, evidence and reconciliation rules for synthetic cases."""

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from src.db import CaseRecord, EvidenceRecord, SourceRecord, uid


class DomainError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        self.status, self.code, self.message, self.retryable = status, code, message, retryable
        super().__init__(message)


KINDS = {"prior_prescription", "medication_history", "admission_order", "clinical_note"}
TYPES = {"prescribed", "patient_reported_taking", "ordered", "documented_not_taking", "uncertain"}
PRODUCTS = [
    {"code": f"MED-{i:02d}", "aliases": [f"Thuốc {chr(65+i)}", f"MED-{i:02d}"], "strength": "500 mg", "form": "viên"}
    for i in range(26)
]


def checksum(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_time(value: str | None, required: bool = False) -> datetime | None:
    if value is None and not required:
        return None
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            raise ValueError("timezone required")
        return result
    except (ValueError, TypeError):
        raise DomainError(422, "INVALID_TIME", "Thời điểm phải là ISO-8601 có múi giờ.")


def parse_import(manifest_raw: str, files: list[tuple[str, bytes]], *, case: CaseRecord | None = None) -> tuple[dict, list[dict]]:
    try:
        manifest = json.loads(manifest_raw)
    except (ValueError, TypeError):
        raise DomainError(422, "INVALID_MANIFEST", "Manifest không phải JSON hợp lệ.")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise DomainError(422, "INVALID_MANIFEST", "Schema manifest phải là 1.0.")
    for key in ("case_id", "patient_id", "encounter_id", "reconciliation_at", "initial_visible_at", "documents"):
        if not manifest.get(key):
            raise DomainError(422, "INVALID_MANIFEST", f"Thiếu {key}.")
    if any(not isinstance(manifest[k], str) or len(manifest[k]) > 80 for k in ("case_id", "patient_id", "encounter_id")):
        raise DomainError(422, "INVALID_MANIFEST", "Mã ca/người bệnh/đợt nhập viện không hợp lệ.")
    if not isinstance(manifest["documents"], list) or not 1 <= len(manifest["documents"]) <= 8:
        raise DomainError(422, "SOURCE_LIMIT", "Mỗi gói cần 1–8 nguồn TXT.")
    parse_time(manifest["reconciliation_at"], True)
    parse_time(manifest["initial_visible_at"], True)
    if case and any(manifest[k] != getattr(case, k) for k in ("case_id", "patient_id", "encounter_id", "reconciliation_at") if k != "case_id"):
        raise DomainError(422, "CASE_MISMATCH", "Metadata không khớp ca đang mở.")
    if case and (manifest["case_id"] != case.id or manifest["initial_visible_at"] != case.visible_at):
        raise DomainError(422, "CASE_MISMATCH", "Không được đổi mã ca hoặc đồng hồ mô phỏng.")
    names = [name for name, _ in files]
    if len(names) != len(set(names)):
        raise DomainError(422, "DUPLICATE_FILE", "Tên tệp TXT bị trùng.")
    uploaded = dict(files)
    docs = []
    total = 0
    seen = set()
    for item in manifest["documents"]:
        if not isinstance(item, dict):
            raise DomainError(422, "INVALID_SOURCE", "Metadata nguồn không hợp lệ.")
        allowed = {"source_id", "version", "kind", "filename", "author_role", "event_time", "recorded_at", "available_at"}
        if set(item) - allowed:
            raise DomainError(422, "INVALID_SOURCE", "Metadata nguồn có trường ngoài schema.")
        filename = item.get("filename")
        if not isinstance(filename, str) or not filename.endswith(".txt") or "/" in filename or "\\" in filename or ".." in filename:
            raise DomainError(422, "INVALID_FILENAME", "Chỉ nhận tên tệp .txt tương đối.")
        if filename not in uploaded:
            raise DomainError(422, "MISSING_FILE", f"Thiếu tệp {filename}.")
        if item.get("kind") not in KINDS or not isinstance(item.get("source_id"), str) or not 1 <= len(item["source_id"]) <= 80 or not isinstance(item.get("version"), int) or isinstance(item.get("version"), bool) or item["version"] < 1 or not isinstance(item.get("author_role"), str) or not 1 <= len(item["author_role"]) <= 40 or len(filename) > 160:
            raise DomainError(422, "INVALID_SOURCE", "Loại, ID, phiên bản hoặc tác giả nguồn không hợp lệ.")
        key = (item["source_id"], item["version"])
        if key in seen:
            raise DomainError(422, "DUPLICATE_SOURCE", "Nguồn/phiên bản bị trùng.")
        seen.add(key)
        for time_key in ("event_time", "recorded_at"):
            parse_time(item.get(time_key))
        available = parse_time(item.get("available_at"), True)
        if available > parse_time(manifest["initial_visible_at"], True):
            raise DomainError(422, "SOURCE_NOT_VISIBLE", "Nguồn tương lai phải được phát hành riêng.")
        try:
            text = uploaded[filename].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise DomainError(422, "INVALID_UTF8", f"Tệp {filename} không phải UTF-8.")
        if not text.strip() or len(text) > 12000:
            raise DomainError(422, "SOURCE_LIMIT", f"Tệp {filename} rỗng hoặc vượt 12.000 ký tự.")
        total += len(text)
        docs.append({**item, "text": text, "checksum": checksum(text)})
    if set(names) != {doc["filename"] for doc in docs} or total > 96000:
        raise DomainError(422, "SOURCE_LIMIT", "Tệp không tham chiếu hoặc tổng nguồn vượt giới hạn.")
    return manifest, docs


def add_sources(db: Session, case: CaseRecord, docs: list[dict]):
    if len(case.sources) + len(docs) > 30:
        raise DomainError(422, "SOURCE_LIMIT", "Tối đa 30 nguồn mọi phiên bản/ca.")
    current = {(s.source_id, s.version) for s in case.sources}
    for item in docs:
        if (item["source_id"], item["version"]) in current:
            raise DomainError(409, "SOURCE_EXISTS", "Nguồn/phiên bản đã tồn tại.")
        db.add(SourceRecord(case_id=case.id, **item))


def add_evidence(db: Session, case: CaseRecord, source: SourceRecord, quote: str) -> str:
    if not quote or quote not in source.text:
        raise DomainError(422, "INVALID_EVIDENCE", "Trích đoạn không xuất hiện trong nguồn gốc.")
    start = source.text.index(quote)
    prior = next((e for e in case.evidence if e.source_id == source.source_id and e.version == source.version and e.start == start and e.quote == quote), None)
    if prior:
        return prior.id
    record = EvidenceRecord(id=uid("EVID"), case_id=case.id, source_id=source.source_id, version=source.version, start=start, end=start + len(quote), quote=quote, context=source.text[max(0, start-80):min(len(source.text), start+len(quote)+80)])
    db.add(record)
    db.flush()
    return record.id


def source_dict(source: SourceRecord) -> dict:
    return {k: getattr(source, k) for k in ("source_id", "version", "kind", "filename", "author_role", "event_time", "recorded_at", "available_at", "text")}


def evidence_dict(e: EvidenceRecord) -> dict:
    return {k: getattr(e, k) for k in ("id", "source_id", "version", "start", "end", "quote", "context")}


def visible_sources(case: CaseRecord) -> list[SourceRecord]:
    clock = parse_time(case.visible_at, True)
    return [s for s in case.sources if parse_time(s.available_at, True) <= clock]


def catalog_candidates(raw: str, dose: str | None = None) -> list[dict]:
    name = raw.casefold().strip()
    candidates = [p for p in PRODUCTS if name in [alias.casefold() for alias in p["aliases"]]]
    stated_strength = parse_dose(dose)
    if stated_strength is not None:
        candidates = [p for p in candidates if parse_dose(p["strength"]) == stated_strength]
    return candidates


def parse_dose(value: str | None) -> Decimal | None:
    if not value:
        return None
    parts = value.lower().replace(",", ".").split()
    if len(parts) != 2 or parts[1] not in ("g", "mg", "mcg"):
        return None
    try:
        return Decimal(parts[0]) * {"g": 1000, "mg": 1, "mcg": Decimal("0.001")}[parts[1]]
    except InvalidOperation:
        return None


def parse_frequency(value: str | None) -> int | None:
    if not value:
        return None
    match = re.fullmatch(r"\s*(\d+)\s*lần/ngày\s*", value.casefold())
    return int(match.group(1)) if match and int(match.group(1)) > 0 else None


def compare(assertions: list[dict], previous: list[dict] | None = None) -> list[dict]:
    """Conservative, product-specific comparison; never infers clinical intent."""
    old = {i.get("signature"): i for i in (previous or [])}
    history = [a for a in assertions if a["side"] == "history"]
    orders = [a for a in assertions if a["side"] == "order"]
    issues: list[dict] = []

    def emit(kind: str, title: str, refs: list[dict], field: str):
        sig = f"{kind}:{':'.join(sorted(a['id'] for a in refs))}:{field}"
        prior = old.get(sig)
        evidence_ids = list(dict.fromkeys(e for a in refs for e in a["evidence_ids"]))
        unchanged = prior and prior.get("evidence_ids") == evidence_ids
        item = dict(prior) if unchanged else {
            "id": prior["id"] if prior else uid("ISS"), "revision": (prior["revision"] + 1) if prior else 1,
            "work_status": "new", "evidence_status": "unknown", "history": (prior.get("history", []) + [f"Trước cập nhật: {prior['evidence_status']}"]) if prior else [],
            "evidence_generation": (prior.get("evidence_generation", 0) + 1) if prior else 1,
        }
        item.update({"title": title, "type": kind, "signature": sig, "evidence_ids": evidence_ids, "assertion_refs": [a["id"] for a in refs]})
        if not unchanged:
            item.pop("confirmation", None)
        issues.append(item)

    for a in history:
        matching = [b for b in orders if a.get("product") and a["product"] == b.get("product")]
        if not a.get("product"):
            emit("information_gap", f"Cần xác minh sản phẩm/hàm lượng: {a['name']}", [a], "product")
            continue
        if a["assertion_type"] in ("prescribed", "uncertain"):
            emit("information_gap", f"Cần xác minh trạng thái/tên: {a['name']}", [a], "status")
            continue
        if not matching and a["assertion_type"] == "patient_reported_taking":
            uncertain_order = [b for b in orders if b.get("name", "").casefold() == a["name"].casefold() and not b.get("product")]
            if uncertain_order:
                emit("information_gap", f"Chưa rõ sản phẩm/hàm lượng: {a['name']}", [a, *uncertain_order], "product")
            else:
                emit("presence_difference", f"Tiền sử có {a['name']}, y lệnh chưa ghi", [a], "presence")
        for b in matching:
            da, db = parse_dose(a.get("dose")), parse_dose(b.get("dose"))
            fa, fb = parse_frequency(a.get("frequency")), parse_frequency(b.get("frequency"))
            if da is not None and db is not None and da != db:
                emit("regimen_difference", f"Khác liều: {a['name']}", [a, b], "dose")
            elif da is None or db is None or fa is None or fb is None:
                emit("information_gap", f"Thiếu liều/tần suất rõ: {a['name']}", [a, b], "regimen")
            elif fa != fb:
                emit("regimen_difference", f"Khác tần suất: {a['name']}", [a, b], "frequency")
    for b in orders:
        if not b.get("product") and not any(a.get("name", "").casefold() == b["name"].casefold() for a in history):
            emit("information_gap", f"Chưa rõ sản phẩm/hàm lượng y lệnh: {b['name']}", [b], "product")
        if b.get("product") and not any(
            a.get("product") == b["product"] or
            (not a.get("product") and a.get("name", "").casefold() == b["name"].casefold())
            for a in history
        ):
            emit("presence_difference", f"Y lệnh có {b['name']}, tiền sử chưa ghi", [b], "presence")
    return issues
