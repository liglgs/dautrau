"""Idempotent synthetic demo seed. Run after `alembic upgrade head`."""

import os

from src.api.security import password_hash
from src.db import CaseRecord, SessionLocal, SourceRecord, User
from src.vmec import checksum

USERS = [
    ("reviewer", "Linh · Người rà soát", "reviewer"),
    ("clinician", "Minh · Bác sĩ duyệt", "clinician"),
    ("clinician2", "An · Bác sĩ nhận bàn giao", "clinician"),
    ("responder", "Hà · Người phản hồi", "responder"),
    ("admin", "Quản trị demo", "admin"),
]


def seed():
    password = os.environ.get("DEMO_PASSWORD", "demo12345")
    if os.environ.get("APP_ENV") == "production" and password == "demo12345":
        raise RuntimeError("Production requires DEMO_PASSWORD")
    with SessionLocal.begin() as db:
        for ident, name, role in USERS:
            if not db.get(User, ident):
                db.add(User(id=ident, name=name, role=role, password_hash=password_hash.hash(password)))
        db.flush()
        for n in range(1, 4):
            ident = f"SIM-00{n}"
            if db.get(CaseRecord, ident):
                continue
            stamp = "2026-09-01T08:15:00+07:00"
            case = CaseRecord(id=ident, patient_id=f"P-{ident}", encounter_id=f"E-{ident}", reconciliation_at="2026-09-01T08:00:00+07:00", visible_at=stamp, assigned=["reviewer", "clinician", "clinician2"], scenario=["matched", "verification", "late"][n-1], assertions=[], issues=[], audit=["Đã nạp nguồn mô phỏng; chưa chạy AI"], extraction_pending=True)
            db.add(case)
            db.flush()
            history = ("Người bệnh khai đang dùng Thuốc B, liều 500 mg, 1 lần/ngày." if n == 1 else "Đơn cũ ghi Thuốc A, liều chưa rõ. Chưa xác minh người bệnh còn dùng.")
            order = "Y lệnh nhập viện: Thuốc B, liều 500 mg, 1 lần/ngày."
            for index, (kind, text) in enumerate((("medication_history" if n == 1 else "prior_prescription", history), ("admission_order", order)), 1):
                db.add(SourceRecord(case_id=ident, source_id=f"{ident}-S{index}", version=1, kind=kind, filename=f"{kind}.txt", author_role="reviewer" if index == 1 else "clinician", event_time=case.reconciliation_at, recorded_at=stamp, available_at=stamp, text=text, checksum=checksum(text)))


if __name__ == "__main__":
    seed()
