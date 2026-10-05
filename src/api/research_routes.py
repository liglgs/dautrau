"""Coordinator-only simulated-time release. Never registered as an agent tool."""

import hmac
import json

from fastapi import APIRouter, Header
from sqlalchemy import select

from src.api.vmec_routes import enqueue_successor, reopen_affected, touch
from src.config import get_settings
from src.db import CaseRecord, ReleaseEvent, SessionLocal, SourceRecord, uid
from src.vmec import KINDS, DomainError, checksum, parse_time

router = APIRouter(prefix="/research")


@router.post("/cases/{case_id}/events/release")
def release(case_id: str, body: dict, x_research_token: str | None = Header(None)):
    token = get_settings().research_token
    if not token or not x_research_token or not hmac.compare_digest(x_research_token, token):
        raise DomainError(403, "FORBIDDEN", "Chỉ điều phối viên nghiên cứu được phát sự kiện.")
    event_id = body.get("event_id")
    if not isinstance(event_id, str) or not event_id or len(event_id) > 100:
        raise DomainError(422, "INVALID_EVENT", "Thiếu event_id.")
    payload_hash = checksum(json.dumps(body, sort_keys=True, ensure_ascii=False))
    with SessionLocal.begin() as db:
        prior = db.get(ReleaseEvent, event_id)
        if prior:
            if prior.payload_hash != payload_hash:
                raise DomainError(409, "EVENT_CONFLICT", "event_id đã dùng cho payload khác.")
            return prior.receipt
        case = db.scalar(select(CaseRecord).where(CaseRecord.id == case_id).with_for_update())
        if not case:
            raise DomainError(404, "NOT_FOUND", "Không tìm thấy ca.")
        if body.get("expected_visible_at") != case.visible_at:
            raise DomainError(409, "CLOCK_CONFLICT", "Đồng hồ mô phỏng đã thay đổi.")
        new_clock = parse_time(body.get("new_visible_at"), True)
        if new_clock < parse_time(case.visible_at, True):
            raise DomainError(422, "CLOCK_REWIND", "Không được lùi đồng hồ mô phỏng.")
        data = body.get("source")
        if not isinstance(data, dict) or data.get("kind") not in KINDS or not isinstance(data.get("text"), str) or not data["text"].strip() or len(data["text"]) > 12000:
            raise DomainError(422, "INVALID_SOURCE", "Nguồn phát hành không hợp lệ.")
        if parse_time(data.get("available_at"), True) > new_clock or len(case.sources) >= 30:
            raise DomainError(422, "SOURCE_LIMIT", "Nguồn chưa được phép xuất hiện hoặc vượt giới hạn.")
        if any(s.source_id == data.get("source_id") and s.version == data.get("version") for s in case.sources):
            raise DomainError(409, "SOURCE_EXISTS", "Nguồn đã tồn tại.")
        for field in ("source_id", "filename", "author_role"):
            if not isinstance(data.get(field), str) or not data[field]:
                raise DomainError(422, "INVALID_SOURCE", f"Thiếu {field}.")
        if not isinstance(data.get("version"), int) or data["version"] < 1:
            raise DomainError(422, "INVALID_SOURCE", "Version nguồn không hợp lệ.")
        source = SourceRecord(case_id=case.id, source_id=data["source_id"], version=data["version"], kind=data["kind"], filename=data["filename"], author_role=data["author_role"], event_time=data.get("event_time"), recorded_at=data.get("recorded_at"), available_at=data["available_at"], text=data["text"], checksum=checksum(data["text"]))
        db.add(source)
        reopen_affected(case, [data["text"]])
        case.visible_at = body["new_visible_at"]
        case.extraction_pending = True
        touch(case, f"Điều phối: phát nguồn {data['source_id']}", input_change=True)
        enqueue_successor(db, case, event_id)
        receipt = {"event_id": event_id, "case_id": case.id, "receipt": uid("RELEASE"), "visible_at": case.visible_at}
        db.add(ReleaseEvent(event_id=event_id, case_id=case.id, payload_hash=payload_hash, receipt=receipt))
        return receipt
