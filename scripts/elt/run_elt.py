"""Chạy ELT đầu-cuối cho VigiLens: Extract -> Parse -> Quality -> Load (PostgreSQL) -> Index (ChromaDB).

Cách dùng:
    python -m scripts.elt.run_elt --profile bundle          # dùng gói 50 mẫu đã tải
    python -m scripts.elt.run_elt --profile live            # gọi lại PubMed/DailyMed/openFDA
    python -m scripts.elt.run_elt --profile research        # gói nguồn công khai trong docs/research
    python -m scripts.elt.run_elt --profile all --skip-rag
    python -m scripts.elt.run_elt --profile bundle --offline --dry-run

Kết quả: kho PostgreSQL ``vigilens_elt``, chỉ mục ChromaDB, manifest và báo cáo trong ``data/elt/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from scripts.elt import config, fetch, load_pg, quality
from scripts.elt.manifest import RunManifest
from scripts.elt.parse import (
    ParsedDocument,
    dailymed_index_entries,
    parse_dailymed_xml,
    parse_faers_json,
    parse_pubmed_tagged,
    parse_pubmed_xml,
    parse_reference_file,
)
from src.config import get_settings


def new_run_id(profile: str) -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{profile}"


# ------------------------------------------------------------------ Parse theo gói 50 mẫu
def parse_bundle(manifest: RunManifest) -> tuple[list[ParsedDocument], dict]:
    """Phân tích lại từ bản thô của gói và đối chiếu băm với tệp JSON đã phát hành."""
    spec = config.load_spec()
    root = config.BUNDLE_DIR
    documents: list[ParsedDocument] = []
    cache: dict[str, list[ParsedDocument]] = {}
    cross = {"records": 0, "hash_matches": 0, "hash_mismatches": [], "raw_missing": [], "raw_hash_mismatch": []}

    def records_of(path: Path) -> list[dict]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return list(payload.get("documents") or [])
        return list(payload)

    for pair in spec["pairs"]:
        pair_dir = root / pair["drug"]
        pair_id = pair["pair_id"]
        for filename in ("pubmed.json", "dailymed.json", "faers.json"):
            path = pair_dir / filename
            if not path.exists():
                manifest.note(f"bundle: thiếu {path.relative_to(config.ROOT)}")
                continue
            for record in records_of(path):
                cross["records"] += 1
                raw_ref = (record.get("metadata") or {}).get("raw_ref")
                if not raw_ref:
                    cross["raw_missing"].append(record.get("doc_id"))
                    continue
                raw_path = root / raw_ref
                if not raw_path.exists():
                    cross["raw_missing"].append(raw_ref)
                    continue
                if raw_ref not in cache:
                    raw = raw_path.read_bytes()
                    if record.get("metadata", {}).get("raw_hash") and \
                            record["metadata"]["raw_hash"] != hashlib.sha256(raw).hexdigest():
                        cross["raw_hash_mismatch"].append(raw_ref)
                    if record["source"] == "pubmed":
                        parsed = parse_pubmed_tagged(raw, pair_id=pair_id, raw_path=str(raw_path.relative_to(config.ROOT)),
                                                     query=pair.get("pubmed_query", ""))
                    elif record["source"] == "dailymed":
                        parsed = [parse_dailymed_xml(raw, pair_id=pair_id,
                                                     raw_path=str(raw_path.relative_to(config.ROOT)),
                                                     expected_setid=record.get("source_id"))]
                    else:
                        parsed = parse_faers_json(raw, pair_id=pair_id,
                                                  raw_path=str(raw_path.relative_to(config.ROOT)), drug=pair["drug"])
                    cache[raw_ref] = parsed
                match = next((d for d in cache[raw_ref] if d.doc_id == record.get("doc_id")), None)
                if match is not None and match.text_sha256 == record.get("hash"):
                    cross["hash_matches"] += 1
                else:
                    cross["hash_mismatches"].append(record.get("doc_id"))
    for parsed in cache.values():
        documents.extend(parsed)
    manifest.stats["bundle_cross_check"] = cross
    return documents, cross


# ------------------------------------------------------------------ Parse trực tiếp từ API
def parse_live(fetcher: fetch.Fetcher, manifest: RunManifest) -> list[ParsedDocument]:
    spec = config.load_spec()
    documents: list[ParsedDocument] = []
    for pair in spec["pairs"]:
        pair_id = pair["pair_id"]
        for result in fetch.fetch_pubmed_by_pmids(fetcher, pair["pubmed_pmids"]):
            if result.ok:
                documents.extend(parse_pubmed_xml(result.body, pair_id=pair_id, raw_path=result.path))
            else:
                manifest.note(f"pubmed efetch lỗi: {result.error}")
        index = fetch.fetch_dailymed_index(fetcher, pair["drug"])
        published: dict[str, dict] = {}
        if index.ok:
            published = {entry["setid"]: entry for entry in dailymed_index_entries(index.body)}
        else:
            manifest.note(f"dailymed index lỗi: {index.error}")
        for setid in pair["dailymed_setids"]:
            result = fetch.fetch_dailymed_label(fetcher, setid)
            if result.ok:
                try:
                    documents.append(parse_dailymed_xml(
                        result.body, pair_id=pair_id, raw_path=result.path,
                        expected_setid=setid, published_date=(published.get(setid) or {}).get("published_date"),
                    ))
                except ValueError as exc:
                    manifest.note(f"dailymed parse lỗi {setid}: {exc}")
            else:
                manifest.note(f"dailymed label lỗi {setid}: {result.error}")
        for report_id in pair["faers_report_ids"]:
            result = fetch.fetch_faers_report(fetcher, report_id)
            if result.ok:
                try:
                    documents.extend(parse_faers_json(result.body, pair_id=pair_id,
                                                      raw_path=result.path, drug=pair["drug"]))
                except ValueError as exc:
                    manifest.note(f"faers parse lỗi {report_id}: {exc}")
            else:
                manifest.note(f"faers report lỗi {report_id}: {result.error}")
    return documents


# ------------------------------------------------------------------ Parse gói nghiên cứu đã cam kết
def parse_research(manifest: RunManifest) -> list[ParsedDocument]:
    packet = config.RESEARCH_DIR
    documents: list[ParsedDocument] = []
    if not packet.exists():
        manifest.note("research: không thấy thư mục docs/research/2026-10-05/data-real")
        return documents
    metadata_path = packet / "label-metadata-and-sections.json"
    label_meta = {}
    if metadata_path.exists():
        label_meta = {item["file"]: item for item in json.loads(metadata_path.read_text(encoding="utf-8"))}
    for path in sorted(packet.glob("pubmed-*.xml")):
        documents.extend(parse_pubmed_xml(path.read_bytes(), pair_id=None,
                                          raw_path=str(path.relative_to(config.ROOT))))
    for path in sorted(packet.glob("dailymed-label-*.xml")):
        meta = label_meta.get(path.name, {})
        try:
            documents.append(parse_dailymed_xml(
                path.read_bytes(), pair_id=None, raw_path=str(path.relative_to(config.ROOT)),
                expected_setid=meta.get("setid"), published_date=None,
            ))
        except ValueError as exc:
            manifest.note(f"research dailymed lỗi {path.name}: {exc}")
    kinds = {"vn-adr-2024.html": "national_pv_bulletin", "vn-adr-2025.html": "national_pv_bulletin",
             "vn-latest-bulletin-index.html": "national_pv_bulletin_index",
             "openfda-event-docs.html": "data_source_documentation",
             "adr-cognitive-task-study.txt": "workflow_primary_study",
             "who-umc-causality.pdf": "case_assessment_guidance"}
    for path in sorted(packet.iterdir()):
        if path.suffix.lower() not in {".html", ".txt", ".pdf"} or path.name == "README.md":
            continue
        if path.name in {"manifest.json"}:
            continue
        try:
            documents.append(parse_reference_file(path, kind=kinds.get(path.name, "reference_material")))
        except RuntimeError as exc:
            manifest.note(f"research bỏ qua {path.name}: {exc}")
    return documents


# ------------------------------------------------------------------ Tổng hợp
def write_staging(run_id: str, documents: list[ParsedDocument], verdicts: dict[str, quality.DocVerdict]) -> Path:
    path = config.STAGING / f"{run_id}-documents.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for doc in documents:
            verdict = verdicts.get(doc.doc_id)
            handle.write(json.dumps({
                "doc_id": doc.doc_id, "source": doc.source, "source_id": doc.source_id,
                "version": doc.version, "pair_id": doc.pair_id, "content_level": doc.content_level,
                "title": doc.title[:300], "text_sha256": doc.text_sha256, "text_chars": len(doc.text),
                "raw_path": doc.raw_path, "raw_sha256": doc.raw_sha256,
                "decision": verdict.decision if verdict else "keep",
                "flags": verdict.flags if verdict else [],
            }, ensure_ascii=False) + "\n")
    return path


def write_reports(run_id: str, stats: dict, findings: list[quality.Finding],
                  verdicts: dict[str, quality.DocVerdict], manifest: RunManifest) -> dict:
    payload = {
        "run_id": run_id,
        "profile": manifest.profile,
        "generated_at": datetime.now(UTC).isoformat(),
        "stats": stats,
        "decisions": {doc_id: verdict.decision for doc_id, verdict in verdicts.items()},
        "findings": [finding.__dict__ for finding in findings],
        "manifest_stats": manifest.stats,
    }
    json_path = config.REPORTS / f"{run_id}-quality.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path = config.REPORTS / f"{run_id}-quality.md"
    md_path.write_text(quality.render_markdown(stats, findings, payload["decisions"], run_id), encoding="utf-8")
    return {"quality_json": str(json_path.relative_to(config.ROOT)),
            "quality_md": str(md_path.relative_to(config.ROOT))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ELT pipeline cho VigiLens (PubMed, DailyMed, FAERS, gói mẫu)")
    parser.add_argument("--profile", choices=["bundle", "live", "research", "all"], default="bundle")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--offline", action="store_true", help="Không gọi mạng; chỉ dùng bản thô/gói đã có.")
    parser.add_argument("--force", action="store_true", help="Tải lại gói 50 mẫu dù đã có.")
    parser.add_argument("--skip-rag", action="store_true")
    parser.add_argument("--skip-db", action="store_true", help="Chỉ extract/parse/quality, không ghi PostgreSQL.")
    parser.add_argument("--dry-run", action="store_true", help="Không ghi DB và không dựng chỉ mục.")
    parser.add_argument("--reset-index", action="store_true", help="Xoá bộ sưu tập Chroma trước khi dựng.")
    parser.add_argument("--reset-db", action="store_true", help="Xoá và tạo lại toàn bộ lược đồ kho ELT.")
    parser.add_argument("--pair-id", default="", help="Chỉ xử lý một cặp thuốc–biến cố.")
    args = parser.parse_args(argv)

    config.ensure_dirs()
    run_id = args.run_id or new_run_id(args.profile)
    manifest = RunManifest(run_id, args.profile, config.ROOT)
    manifest.note(f"profile={args.profile} offline={args.offline} dry_run={args.dry_run}")

    documents: list[ParsedDocument] = []
    fetcher = fetch.Fetcher(config.RAW_ROOT, manifest, offline=args.offline, force=args.force)
    try:
        if args.profile in {"bundle", "all"}:
            if not args.offline:
                manifest.stats["bundle_download"] = fetch.download_bundle(manifest, force=args.force)
            elif config.BUNDLE_ZIP.exists() and not config.BUNDLE_DIR.exists():
                manifest.stats["bundle_download"] = {"zip": str(config.BUNDLE_ZIP.relative_to(config.ROOT)),
                                                     "status": "offline_zip_present"}
            if config.BUNDLE_ZIP.exists() or config.BUNDLE_DIR.exists():
                manifest.stats["bundle_extract"] = fetch.extract_bundle(manifest)
                parsed, cross = parse_bundle(manifest)
                manifest.stats["bundle_parsed"] = {"documents": len(parsed), **cross}
                documents.extend(parsed)
            else:
                manifest.note("bundle: chưa có zip và đang chạy offline; bỏ qua")
        if args.profile in {"research", "all"}:
            manifest.stats["research_packet"] = fetch.verify_research_packet(manifest)
            documents.extend(parse_research(manifest))
        if args.profile in {"live", "all"}:
            documents.extend(parse_live(fetcher, manifest))
    finally:
        fetcher.close()

    if args.pair_id:
        documents = [doc for doc in documents if doc.pair_id in {args.pair_id, None}]
    unique: dict[str, ParsedDocument] = {}
    for doc in documents:
        unique.setdefault(doc.doc_id, doc)
    documents = list(unique.values())

    results = quality.evaluate_all(documents)
    keep, quarantine, rejected = quality.partition(results)
    verdicts = quality.verdict_map(results)
    findings = [finding for _, verdict in results for finding in verdict.findings]
    stats = quality.dataset_stats(documents, findings)
    stats["keep"] = len(keep)
    stats["quarantine"] = len(quarantine)
    stats["rejected"] = len(rejected)
    manifest.stats["quality"] = stats

    staging_path = write_staging(run_id, documents, verdicts)
    reports = write_reports(run_id, stats, findings, verdicts, manifest)

    loaded: dict = {}
    rag: dict = {}
    if not (args.dry_run or args.skip_db):
        from src.services.warehouse import db as wh_db

        engine = wh_db.get_warehouse_engine()
        if args.reset_db:
            from src.services.warehouse.models import WarehouseBase

            WarehouseBase.metadata.drop_all(engine)
        wh_db.create_schema(engine)
        loaded["pairs"] = load_pg.load_pairs(engine, config.load_spec())
        # Cổng chất lượng: `reject` bị loại khỏi kho (xem docs/data/cong-chat-luong.md).
        # Truyền cả ba nhóm để bộ nạp tự chặn `reject` và xoá bản ghi cũ nếu tài liệu
        # từng đạt ở lần chạy trước (bài bị gỡ, hoặc văn bản co xuống dưới ngưỡng);
        # phát hiện của cả ba nhóm vẫn được ghi qua load_findings để phục vụ báo cáo.
        loaded.update(load_pg.load_documents(engine, run_id, documents, verdicts))
        loaded["findings"] = load_pg.load_findings(engine, run_id, findings)
        load_pg.load_run(engine, run_id, args.profile, manifest.git_sha, "loaded", stats, manifest.notes)
        loaded["artifacts"] = load_pg.load_artifacts(engine, run_id, manifest.to_dict())
        load_pg.load_ingestion_event(
            engine, event_id=f"elt-{run_id}", kind="elt_run",
            title=f"ELT {args.profile}: {stats.get('keep', 0)} tài liệu đạt, {stats.get('quarantine', 0)} cách ly",
            detail={"run_id": run_id, "stats": stats, "reports": reports, "staging": str(staging_path.relative_to(config.ROOT))},
        )
        loaded["table_counts"] = wh_db.table_counts(engine)
        if not (args.skip_rag or not get_settings().rag_enabled):
            from src.services.rag import build as rag_build

            try:
                rag = rag_build.build_index(engine, run_id=run_id, reset=args.reset_index)
                rag["index_stats"] = rag_build.index_stats(engine)
            except Exception as exc:  # noqa: BLE001 - kho đã nạp xong, cần chỉ dẫn rõ ràng
                # Kho PostgreSQL đã cập nhật nhưng chỉ mục vector thì chưa, nên số đoạn hai bên
                # sẽ lệch cho tới khi dựng lại chỉ mục. In chỉ dẫn thay vì chỉ ném lỗi thô.
                print(json.dumps({
                    "run_id": run_id,
                    "warehouse": "đã nạp xong",
                    "rag_error": f"{exc.__class__.__name__}: {exc}",
                    "khắc_phục": "chạy lại: python -m scripts.elt.load_chroma --reset-index",
                }, indent=2, ensure_ascii=False), file=sys.stderr)
                raise
    manifest.stats["loaded"] = loaded
    manifest.stats["rag"] = rag
    manifest.stats["reports"] = reports
    manifest.stats["staging"] = str(staging_path.relative_to(config.ROOT))
    manifest_path = manifest.write(config.MANIFESTS)

    print(json.dumps({
        "run_id": run_id,
        "documents": len(documents),
        "keep": len(keep), "quarantine": len(quarantine), "rejected": len(rejected),
        "manifest": str(manifest_path.relative_to(config.ROOT)),
        "reports": reports,
        "staging": str(staging_path.relative_to(config.ROOT)),
        "loaded": {k: v for k, v in loaded.items() if k != "table_counts"},
        "rag": {k: v for k, v in rag.items() if k != "index_stats"},
        "notes": manifest.notes[:20],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
