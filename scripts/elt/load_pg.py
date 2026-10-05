"""Tầng Load: ghi bản ghi chuẩn, cặp thuốc–biến cố, phát hiện chất lượng và vết chạy vào PostgreSQL."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from scripts.elt.parse import ParsedDocument
from scripts.elt.quality import DocVerdict, Finding
from src.services.warehouse.models import (
    DailymedLabel,
    Document,
    DocumentChunk,
    DocumentSection,
    Drug,
    DrugEventPair,
    EltArtifact,
    EltRun,
    FaersReport,
    FaersReportDrug,
    FaersReportReaction,
    IngestionEvent,
    PubmedRecord,
    QualityFinding,
)


def _drug_id(name: str) -> str:
    return "drug:" + "-".join((name or "").strip().lower().split())


def load_pairs(engine: Engine, spec: dict, *, status: str = "candidate_not_gold", source: str = "bundle") -> int:
    count = 0
    with engine.begin() as conn:
        for pair in spec.get("pairs", []):
            drug_name = pair["drug"]
            drug_id = _drug_id(drug_name)
            # Chú ý: với Core connection, `select(Entity)` trả về cột chứ không trả về đối tượng ORM.
            # Vì vậy luôn chọn đúng cột cần kiểm tra (xem `tests/test_services/test_elt_warehouse.py`).
            existing_id = conn.execute(
                select(Drug.drug_id).where(Drug.drug_id == drug_id)
            ).scalar_one_or_none()
            if existing_id is None:
                conn.execute(Drug.__table__.insert().values(
                    drug_id=drug_id, name=drug_name, ingredient=pair.get("drug_ingredient", drug_name),
                    verified=True, source="dataset-spec", aliases=[], metadata_json={},
                ))
            values = {
                "drug_id": drug_id, "drug_name": drug_name,
                "event_term": pair["event"], "status": status, "source": source,
                "metadata_json": {
                    "pubmed_query": pair.get("pubmed_query"),
                    "pubmed_pmids": pair.get("pubmed_pmids", []),
                    "dailymed_setids": pair.get("dailymed_setids", []),
                    "faers_report_ids": pair.get("faers_report_ids", []),
                },
            }
            # Cập nhật tại chỗ thay vì xoá rồi chèn lại: `documents.pair_id` tham chiếu bảng này,
            # nên xoá sẽ vi phạm khoá ngoại khi kho đã có tài liệu (chạy lại lần hai).
            existing_pair = conn.execute(
                select(DrugEventPair.pair_id).where(DrugEventPair.pair_id == pair["pair_id"])
            ).scalar_one_or_none()
            if existing_pair is None:
                conn.execute(DrugEventPair.__table__.insert().values(pair_id=pair["pair_id"], **values))
            else:
                conn.execute(
                    DrugEventPair.__table__.update()
                    .where(DrugEventPair.pair_id == pair["pair_id"])
                    .values(**values)
                )
            count += 1
    return count


def _delete_child_rows(conn, doc_id: str) -> None:
    """Xoá các bảng con gắn với một tài liệu (không gồm đoạn vector và phát hiện chất lượng)."""
    conn.execute(delete(DocumentSection).where(DocumentSection.doc_id == doc_id))
    conn.execute(delete(PubmedRecord).where(PubmedRecord.doc_id == doc_id))
    conn.execute(delete(DailymedLabel).where(DailymedLabel.doc_id == doc_id))
    conn.execute(delete(FaersReportDrug).where(FaersReportDrug.doc_id == doc_id))
    conn.execute(delete(FaersReportReaction).where(FaersReportReaction.doc_id == doc_id))
    conn.execute(delete(FaersReport).where(FaersReport.doc_id == doc_id))


def _delete_document_rows(conn, doc_id: str, run_id: str | None = None) -> None:
    """Xoá một tài liệu và mọi bản ghi con (thứ tự an toàn cho khoá ngoại).

    ``run_id`` chỉ giới hạn phạm vi xoá ``quality_findings``: phát hiện của lần chạy
    hiện tại bị bỏ đi cùng tài liệu, còn phát hiện của các lần chạy trước giữ nguyên
    để không mất dấu vết kiểm toán.
    """
    _delete_child_rows(conn, doc_id)
    conn.execute(delete(DocumentChunk).where(DocumentChunk.doc_id == doc_id))
    findings = delete(QualityFinding).where(QualityFinding.doc_id == doc_id)
    if run_id is not None:
        findings = findings.where(QualityFinding.run_id == run_id)
    conn.execute(findings)
    conn.execute(delete(Document).where(Document.doc_id == doc_id))


def load_documents(
    engine: Engine,
    run_id: str,
    documents: list[ParsedDocument],
    verdicts: dict[str, DocVerdict],
) -> dict:
    inserted = updated = 0
    changed: list[str] = []
    skipped_rejected = 0
    removed_rejected = 0
    with engine.begin() as conn:
        for doc in documents:
            verdict = verdicts.get(doc.doc_id)
            decision = verdict.decision if verdict else "keep"
            flags = list(verdict.flags) if verdict else []
            if decision == "reject":
                # Hợp đồng cổng chất lượng: bản ghi bị loại không vào kho (xem docs/data/cong-chat-luong.md).
                # Tài liệu đã nằm trong kho từ lần chạy trước (ví dụ bài bị gỡ, hoặc văn bản co
                # xuống dưới ngưỡng) cũng phải bị xoá, nếu không nó vẫn trả về qua RAG.
                skipped_rejected += 1
                exists = conn.execute(
                    select(Document.doc_id).where(Document.doc_id == doc.doc_id)
                ).scalar_one_or_none()
                if exists is not None:
                    _delete_document_rows(conn, doc.doc_id, run_id=run_id)
                    removed_rejected += 1
                continue
            values = {
                "doc_id": doc.doc_id,
                "source": doc.source,
                "source_id": doc.source_id,
                "version": int(doc.version),
                "title": doc.title,
                "text": doc.text,
                "text_sha256": doc.text_sha256,
                "source_url": doc.source_url,
                "retrieved_at": datetime.now(UTC),
                "content_level": doc.content_level,
                "pair_id": doc.pair_id,
                "run_id": run_id,
                "quality_status": decision,
                "quality_flags": flags,
                "metadata_json": doc.metadata,
            }
            existing_hash = conn.execute(
                select(Document.text_sha256).where(Document.doc_id == doc.doc_id)
            ).scalar_one_or_none()
            if existing_hash is None:
                conn.execute(Document.__table__.insert().values(**values))
                inserted += 1
            else:
                if existing_hash != doc.text_sha256:
                    changed.append(doc.doc_id)
                conn.execute(Document.__table__.update().where(Document.doc_id == doc.doc_id).values(**values))
                updated += 1
                # Xoá bản ghi con trước khi ghi lại (không xoá bản ghi chính vì đang cập nhật tại chỗ).
                _delete_child_rows(conn, doc.doc_id)
            for ordinal, section in enumerate(doc.sections):
                conn.execute(DocumentSection.__table__.insert().values(
                    doc_id=doc.doc_id, ordinal=ordinal, title=str(section.get("title", ""))[:300],
                    start=int(section.get("start", 0)), end=int(section.get("end", 0)),
                ))
            _load_source_row(conn, doc)
    return {"inserted": inserted, "updated": updated, "content_changed": changed,
            "skipped_rejected": skipped_rejected, "removed_rejected": removed_rejected}


def _load_source_row(conn, doc: ParsedDocument) -> None:
    structured = doc.structured
    if doc.source == "pubmed":
        conn.execute(PubmedRecord.__table__.insert().values(
            doc_id=doc.doc_id, pmid=structured.get("pmid", doc.source_id),
            journal=str(structured.get("journal") or "")[:300],
            publication_date=str(structured.get("publication_date") or "")[:120],
            publication_types=list(structured.get("publication_types") or []),
            doi=list(structured.get("doi") or []),
            authors=list(structured.get("authors") or []),
            has_abstract=bool(structured.get("has_abstract")),
        ))
    elif doc.source == "dailymed":
        conn.execute(DailymedLabel.__table__.insert().values(
            doc_id=doc.doc_id, setid=str(structured.get("setid", doc.source_id)),
            effective_time=structured.get("effective_time"),
            published_date=structured.get("published_date"),
            routes=list(structured.get("routes") or []),
            ingredients=list(structured.get("ingredients") or []),
            n_sections=int(structured.get("n_sections") or 0),
            single_ingredient=bool(structured.get("single_ingredient")),
        ))
    elif doc.source == "faers":
        conn.execute(FaersReport.__table__.insert().values(
            doc_id=doc.doc_id, safetyreportid=str(structured.get("safetyreportid", doc.source_id)),
            report_version=int(structured.get("report_version") or doc.version),
            receivedate=_truncate(structured.get("receivedate"), 20),
            occurcountry=_truncate(structured.get("occurcountry"), 40),
            serious=_truncate(structured.get("serious"), 20), patient_sex=_truncate(structured.get("patient_sex"), 20),
            patient_age=_float_or_none(structured.get("patient_age")),
            patient_age_unit=_truncate(structured.get("patient_age_unit"), 20),
            reporter_country=_truncate(structured.get("reporter_country"), 120),
            n_drugs=int(structured.get("n_drugs") or 0), n_reactions=int(structured.get("n_reactions") or 0),
            total_hits=structured.get("total_hits"),
            matched_drugs=list(structured.get("matched_drugs") or []),
            reactions=[r for r in (structured.get("reactions") or [])],
        ))
        for ordinal, row in enumerate(structured.get("drugs") or []):
            conn.execute(FaersReportDrug.__table__.insert().values(
                doc_id=doc.doc_id, ordinal=ordinal,
                medicinalproduct=str(row.get("medicinalproduct") or "")[:400],
                generic_name=str(row.get("generic_name") or "")[:400],
                brand_name=str(row.get("brand_name") or "")[:400],
                substance_name=str(row.get("substance_name") or "")[:400],
                route=_truncate(row.get("route"), 80), dose_text=_truncate(row.get("dose_text"), 200),
                characterization=_truncate(row.get("characterization"), 20),
                indication=_truncate(row.get("indication"), 400),
            ))
        for ordinal, row in enumerate(structured.get("reactions") or []):
            conn.execute(FaersReportReaction.__table__.insert().values(
                doc_id=doc.doc_id, ordinal=ordinal,
                term=str(row.get("term") or "")[:400], outcome=_truncate(row.get("outcome"), 20),
            ))


def _truncate(value, size: int):
    return None if value is None else str(value)[:size]


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_findings(engine: Engine, run_id: str, findings: list[Finding]) -> int:
    with engine.begin() as conn:
        conn.execute(delete(QualityFinding).where(QualityFinding.run_id == run_id))
        for finding in findings:
            conn.execute(QualityFinding.__table__.insert().values(
                run_id=run_id, doc_id=finding.doc_id, pair_id=finding.pair_id, source=finding.source,
                check_name=finding.check_name, severity=finding.severity,
                decision=finding.decision, detail=finding.detail[:2000],
            ))
    return len(findings)


def load_run(engine: Engine, run_id: str, profile: str, git_sha: str, status: str,
             stats: dict, notes: list[str]) -> None:
    with engine.begin() as conn:
        existing = conn.execute(select(EltRun).where(EltRun.run_id == run_id)).scalar_one_or_none()
        values = {
            "run_id": run_id, "profile": profile, "git_sha": git_sha, "status": status,
            "finished_at": datetime.now(UTC), "stats": stats, "notes": json.dumps(notes, ensure_ascii=False),
        }
        if existing is None:
            conn.execute(EltRun.__table__.insert().values(**values))
        else:
            conn.execute(EltRun.__table__.update().where(EltRun.run_id == run_id).values(**values))


def load_artifacts(engine: Engine, run_id: str, manifest: dict) -> int:
    with engine.begin() as conn:
        conn.execute(delete(EltArtifact).where(EltArtifact.run_id == run_id))
        for entry in manifest.get("artifacts", []):
            conn.execute(EltArtifact.__table__.insert().values(
                artifact_id=f"{run_id}:{entry['artifact_id']}", run_id=run_id,
                source=entry.get("source", ""), kind=entry.get("kind", ""),
                url=str(entry.get("url", ""))[:2000], params=entry.get("params") or {},
                status=entry.get("status"), sha256=entry.get("sha256", ""),
                bytes=int(entry.get("bytes") or 0), local_path=entry.get("path", ""),
                error=(entry.get("error") or None),
            ))
    return len(manifest.get("artifacts", []))


def load_ingestion_event(engine: Engine, *, event_id: str, kind: str, title: str,
                         detail: dict, status: str = "completed") -> None:
    with engine.begin() as conn:
        conn.execute(IngestionEvent.__table__.delete().where(IngestionEvent.event_id == event_id))
        conn.execute(IngestionEvent.__table__.insert().values(
            event_id=event_id, kind=kind, status=status, title=title[:300], detail=detail,
        ))
