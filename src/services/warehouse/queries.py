"""Truy vấn đọc trên kho ELT (dùng cho API tra cứu thuốc và trang quản trị)."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.engine import Engine

from src.services.warehouse.db import read_session
from src.services.warehouse.models import (
    DailymedLabel,
    Document,
    Drug,
    DrugEventPair,
    EltRun,
    FaersReport,
    IngestionEvent,
    PubmedRecord,
    QualityFinding,
)


def normalize_name(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def lookup_drug(engine: Engine, name: str, limit: int = 20) -> dict:
    """Tra cứu thuốc theo tên hoặc alias, kèm cặp thuốc–biến cố và số tài liệu theo nguồn."""
    needle = normalize_name(name)
    if not needle:
        return {"query": name, "matched": False, "drugs": [], "pairs": [], "documents": {}}
    with read_session(engine) as conn:
        rows = conn.execute(
            select(Drug).where(
                func.lower(Drug.name).contains(needle) | func.lower(Drug.ingredient).contains(needle)
            ).limit(limit)
        ).scalars().all()
        drugs = [{"drug_id": r.drug_id, "name": r.name, "ingredient": r.ingredient,
                  "verified": bool(r.verified), "aliases": list(r.aliases or [])} for r in rows]
        pair_rows = conn.execute(
            select(DrugEventPair).where(func.lower(DrugEventPair.drug_name).contains(needle)).limit(limit)
        ).scalars().all()
        pairs = [{"pair_id": p.pair_id, "drug_name": p.drug_name, "event_term": p.event_term,
                  "status": p.status, "source": p.source} for p in pair_rows]
        pair_ids = [p.pair_id for p in pair_rows]
        documents: dict[str, dict] = {}
        if pair_ids:
            counts = conn.execute(
                select(Document.source, func.count(Document.doc_id))
                .where(Document.pair_id.in_(pair_ids), Document.quality_status == "keep")
                .group_by(Document.source)
            ).all()
            documents = {source: int(count) for source, count in counts}
    return {
        "query": name,
        "matched": bool(drugs or pairs),
        "drugs": drugs,
        "pairs": pairs,
        "documents": documents,
    }


def warehouse_overview(engine: Engine) -> dict:
    with read_session(engine) as conn:
        by_source = conn.execute(
            select(Document.source, func.count(Document.doc_id), func.max(Document.retrieved_at))
            .group_by(Document.source)
        ).all()
        by_status = conn.execute(
            select(Document.quality_status, func.count(Document.doc_id)).group_by(Document.quality_status)
        ).all()
        # Phát hiện chất lượng tích luỹ theo từng lần chạy, nên chỉ thống kê lần chạy ELT mới nhất
        # (cộng thêm các phát hiện của tài liệu nạp tay, không thuộc lần chạy nào) để số liệu không bị nhân lên.
        latest_run = conn.execute(
            select(EltRun.run_id).order_by(EltRun.started_at.desc(), EltRun.run_id.desc()).limit(1)
        ).scalar_one_or_none()
        known_runs = select(EltRun.run_id)
        flags = conn.execute(
            select(QualityFinding.check_name, QualityFinding.severity, func.count(QualityFinding.id))
            .where(
                or_(
                    QualityFinding.run_id == latest_run,
                    QualityFinding.run_id.not_in(known_runs),
                )
            )
            .group_by(QualityFinding.check_name, QualityFinding.severity)
        ).all()
        sources = []
        for source, count, latest in by_source:
            rows = conn.execute(
                select(Document.content_level, func.count(Document.doc_id))
                .where(Document.source == source)
                .group_by(Document.content_level)
            ).all()
            sources.append({
                "source": source,
                "documents": int(count),
                "latest_retrieved_at": latest.isoformat() if latest else None,
                "by_content_level": {level or "unknown": int(n) for level, n in rows},
            })
    return {
        "documents_by_source": sources,
        "documents_by_quality_status": {status: int(count) for status, count in by_status},
        "quality_findings_run_id": latest_run,
        "quality_findings": [
            {"check_name": name, "severity": severity, "count": int(count)} for name, severity, count in flags
        ],
    }


def list_documents(engine: Engine, *, source: str | None = None, pair_id: str | None = None,
                   quality_status: str | None = None, limit: int = 50) -> list[dict]:
    stmt = select(Document).order_by(Document.retrieved_at.desc(), Document.doc_id).limit(max(1, min(limit, 500)))
    if source:
        stmt = stmt.where(Document.source == source)
    if pair_id:
        stmt = stmt.where(Document.pair_id == pair_id)
    if quality_status:
        stmt = stmt.where(Document.quality_status == quality_status)
    with read_session(engine) as conn:
        rows = conn.execute(stmt).scalars().all()
    return [
        {
            "doc_id": d.doc_id,
            "source": d.source,
            "source_id": d.source_id,
            "version": d.version,
            "title": d.title[:300],
            "source_url": d.source_url,
            "quality_status": d.quality_status,
            "quality_flags": list(d.quality_flags or []),
            "pair_id": d.pair_id,
            "retrieved_at": d.retrieved_at.isoformat() if d.retrieved_at else None,
        }
        for d in rows
    ]


def document_detail(engine: Engine, doc_id: str) -> dict | None:
    with read_session(engine) as conn:
        doc = conn.execute(select(Document).where(Document.doc_id == doc_id)).scalar_one_or_none()
        if doc is None:
            return None
        detail = {
            "doc_id": doc.doc_id,
            "source": doc.source,
            "source_id": doc.source_id,
            "version": doc.version,
            "title": doc.title,
            "text_sha256": doc.text_sha256,
            "source_url": doc.source_url,
            "quality_status": doc.quality_status,
            "quality_flags": list(doc.quality_flags or []),
            "sections": [{"title": s.title, "start": s.start, "end": s.end} for s in doc.sections],
        }
        if doc.source == "pubmed":
            row = conn.execute(select(PubmedRecord).where(PubmedRecord.doc_id == doc_id)).scalar_one_or_none()
            if row:
                detail["pubmed"] = {
                    "pmid": row.pmid, "journal": row.journal, "publication_date": row.publication_date,
                    "publication_types": list(row.publication_types or []), "doi": list(row.doi or []),
                    "authors": list(row.authors or []), "has_abstract": bool(row.has_abstract),
                }
        elif doc.source == "dailymed":
            row = conn.execute(select(DailymedLabel).where(DailymedLabel.doc_id == doc_id)).scalar_one_or_none()
            if row:
                detail["dailymed"] = {
                    "setid": row.setid, "effective_time": row.effective_time,
                    "published_date": row.published_date, "routes": list(row.routes or []),
                    "ingredients": list(row.ingredients or []), "n_sections": row.n_sections,
                }
        elif doc.source == "faers":
            row = conn.execute(select(FaersReport).where(FaersReport.doc_id == doc_id)).scalar_one_or_none()
            if row:
                detail["faers"] = {
                    "safetyreportid": row.safetyreportid, "receivedate": row.receivedate,
                    "serious": row.serious, "patient_age": row.patient_age,
                    "patient_sex": row.patient_sex, "n_drugs": row.n_drugs, "n_reactions": row.n_reactions,
                    "reactions": list(row.reactions or []), "matched_drugs": list(row.matched_drugs or []),
                }
    return detail


def ingestion_events(engine: Engine, limit: int = 30) -> list[dict]:
    with read_session(engine) as conn:
        rows = conn.execute(
            select(IngestionEvent).order_by(IngestionEvent.created_at.desc()).limit(max(1, min(limit, 200)))
        ).scalars().all()
    return [
        {"event_id": r.event_id, "kind": r.kind, "status": r.status, "title": r.title,
         "detail": r.detail, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]
