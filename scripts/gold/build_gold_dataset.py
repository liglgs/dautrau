"""Dựng bộ chuẩn vàng giai đoạn 1 (nguồn công khai quốc tế) cho VigiLens.

Đầu vào: ``data/gold/spec.json`` (danh sách hoạt chất, biến cố, từ đồng nghĩa, quy tắc).
Đầu ra: ``data/gold/drug-event-pairs.jsonl`` (mỗi dòng một cặp thuốc–biến cố) và
``data/gold/manifest.json`` (băm tệp, nguồn, số liệu tổng hợp, giới hạn).

Nguyên tắc:

* Nhãn do máy đề xuất từ nhãn thuốc gốc của FDA (openFDA drug/label, SPL) và đối chiếu
  thống kê báo cáo FAERS (openFDA drug/event). Nhãn KHÔNG phải chuẩn vàng đã duyệt:
  mỗi dòng mang ``review.status = "candidate_not_gold"`` cho tới khi dược sĩ duyệt.
* Không bịa dữ liệu: thiếu nhãn ⇒ ``label_evidence.status = "no_label"``; lỗi mạng ⇒
  ghi lỗi và dừng, không ghi nhãn âm tính giả.
* Bản thô của mọi yêu cầu mạng được lưu ở ``data/gold/raw/`` (không commit) để chạy
  lại ở chế độ ``--offline`` cho ra tệp giống hệt.
* Không chứng minh nhân quả: số FAERS là số báo cáo tự nguyện khớp truy vấn, không
  phải tỉ lệ mắc và không có mẫu số.

Chạy:

    python -m scripts.gold.build_gold_dataset --force
    python -m scripts.gold.build_gold_dataset --offline
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = ROOT / "data" / "gold" / "spec.json"
DEFAULT_OUT = ROOT / "data" / "gold" / "drug-event-pairs.jsonl"
DEFAULT_MANIFEST = ROOT / "data" / "gold" / "manifest.json"
DEFAULT_RAW = ROOT / "data" / "gold" / "raw"

LABEL_ENDPOINT = "https://api.fda.gov/drug/label.json"
EVENT_ENDPOINT = "https://api.fda.gov/drug/event.json"
LABEL_QUERY_LIMIT = 25
METHOD_VERSION = "gold-label-match-v1"
THROTTLE_SECONDS = 0.6
USER_AGENT = "VigiLens-Gold/1.0 (+https://github.com/kp21-tech/nbtvfdcvbhtyjgtref; research dataset builder)"
REVIEW_LIMITATIONS = [
    "Nhãn do máy đề xuất, chưa có dược sĩ/chuyên gia cảnh giác dược duyệt (candidate_not_gold).",
    "Nhãn dương tính là bằng chứng nhãn CÓ nêu tên biến cố, không phải bằng chứng nhân quả.",
    "Nhãn âm tính chỉ nói biến cố không được nêu trong các mục đã kiểm tra của nhãn đã chọn; không phải bằng chứng thuốc không gây biến cố.",
    "Chỉ dùng nhãn Hoa Kỳ (FDA SPL); không đối chiếu với tờ hướng dẫn của Việt Nam.",
    "Số FAERS là báo cáo tự nguyện, có trùng lặp và không có mẫu số; không dùng để tính tỉ lệ.",
    "Chuỗi MedDRA dùng để truy vấn chưa đối chiếu từ điển MedDRA có bản quyền.",
    "Bộ dữ liệu là ảnh chụp tại thời điểm lấy: chạy lại sau này có thể ra số FAERS khác.",
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    """Đường dẫn tương đối so với gốc repo; nếu nằm ngoài thì giữ nguyên."""
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# ------------------------------------------------------------------ khớp chuỗi
def term_pattern(term: str) -> re.Pattern[str]:
    """Mẫu tìm một từ/cụm từ, chấp nhận khoảng trắng hoặc gạch nối giữa các từ."""
    words = [re.escape(word) for word in term.split()]
    body = r"[\s\-–—/]+".join(words)
    return re.compile(rf"(?<![\w-]){body}(?![\w-])", re.IGNORECASE)


def find_term(text: str, term: str) -> re.Match[str] | None:
    return term_pattern(term).search(text)


def quote_around(text: str, start: int, end: int, *, max_chars: int = 400) -> str:
    """Trả về câu chứa đoạn khớp, đã cắt khoảng trắng và giới hạn độ dài."""
    left = 0
    for boundary in re.finditer(r"[.;:!?]\s|\n", text[:start]):
        left = boundary.end()
    right = len(text)
    tail = re.search(r"[.;:!?](\s|$)|\n", text[end:])
    if tail:
        right = end + tail.start() + 1
    quote = " ".join(text[left:right].split())
    if len(quote) > max_chars:
        quote = quote[: max_chars - 1].rstrip() + "…"
    return quote


def match_any(text: str, synonyms: list[str], *, max_chars: int = 400) -> tuple[str, str] | None:
    """Trả về (từ đồng nghĩa khớp, câu chứa nó) hoặc None."""
    for synonym in synonyms:
        found = find_term(text, synonym)
        if found:
            return synonym, quote_around(text, found.start(), found.end(), max_chars=max_chars)
    return None


# ------------------------------------------------------------------ nhãn SPL
def section_texts(label: dict, sections: list[str]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for section in sections:
        value = label.get(section)
        if isinstance(value, list):
            joined = "\n".join(str(item) for item in value if item)
        elif isinstance(value, str):
            joined = value
        else:
            continue
        joined = joined.strip()
        if joined:
            texts[section] = joined
    return texts


CONJUNCTION = re.compile(r"\b(and|with|plus)\b|[,;/+]", re.IGNORECASE)


def is_single_ingredient(label: dict, generic_name: str) -> bool:
    """Nhãn chỉ chứa một hoạt chất (kể cả dạng muối), không phải thuốc phối hợp.

    openFDA gộp thuốc phối hợp vào cùng truy vấn theo tên chung, ví dụ
    "ASPIRIN AND EXTENDED-RELEASE DIPYRIDAMOLE". Nhãn phối hợp làm mờ quy kết
    thuốc–biến cố nên bị hạ ưu tiên.
    """
    names = (label.get("openfda") or {}).get("generic_name") or []
    target = " ".join(str(generic_name).lower().split())
    for raw_name in names:
        name = " ".join(str(raw_name).lower().split())
        if CONJUNCTION.search(name):
            continue
        if name == target or name.startswith(f"{target} ") or name.endswith(f" {target}"):
            return True
    return False


def select_label(results: list[dict], generic_name: str | None = None) -> dict | None:
    """Chọn nhãn mới nhất, ưu tiên nhãn một hoạt chất.

    Thứ tự: chỉ lấy nhãn có set_id; nếu biết tên chung thì ưu tiên nhãn một hoạt chất
    (nếu không có nhãn nào như vậy thì dùng toàn bộ, có ghi lại tên nhãn trong bản ghi);
    sau đó chọn effective_time lớn nhất, hòa thì set_id nhỏ hơn theo thứ tự từ điển.
    """
    usable = [row for row in results if isinstance(row, dict) and row.get("set_id")]
    if not usable:
        return None
    if generic_name:
        single = [row for row in usable if is_single_ingredient(row, generic_name)]
        if single:
            usable = single
    usable.sort(key=lambda row: str(row.get("set_id")))
    return max(usable, key=lambda row: str(row.get("effective_time") or ""))


def label_title(label: dict) -> str:
    for key in ("openfda",):
        brand = (label.get(key) or {}).get("brand_name") or []
        generic = (label.get(key) or {}).get("generic_name") or []
        parts = [*generic, *brand]
        if parts:
            return " / ".join(str(part) for part in parts[:2])
    for key in ("description", "indications_and_usage"):
        value = label.get(key)
        if isinstance(value, list) and value:
            return " ".join(str(value[0]).split())[:120]
    return ""


def label_url(set_id: str) -> str:
    return f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"


def label_api_url(generic_name: str) -> str:
    query = f'openfda.generic_name:"{generic_name}" AND _exists_:adverse_reactions'
    return f"{LABEL_ENDPOINT}?search={query}&limit={LABEL_QUERY_LIMIT}"


def faers_api_url(generic_name: str, meddra_pt: str | None = None) -> str:
    parts = [f'patient.drug.openfda.generic_name:"{generic_name}"']
    if meddra_pt:
        parts.append(f'patient.reaction.reactionmeddrapt:"{meddra_pt}"')
    return f"{EVENT_ENDPOINT}?search={' AND '.join(parts)}&limit=1"


# ------------------------------------------------------------------ tải và lưu thô
class RawStore:
    """Lưu bản thô của mọi phản hồi để chạy lại offline và truy vết."""

    def __init__(self, root: Path, *, offline: bool = False, force: bool = False):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.force = force
        self.index_path = self.root / "_index.json"
        self.index = json.loads(self.index_path.read_text(encoding="utf-8")) if self.index_path.exists() else {}
        self._client = httpx.Client(
            timeout=30, follow_redirects=True, trust_env=False, headers={"User-Agent": USER_AGENT}
        )
        self._last_call = 0.0
        self.fetched = 0
        self.served_from_cache = 0

    def _throttle(self) -> None:
        wait = THROTTLE_SECONDS - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def get_json(self, key: str, url: str) -> tuple[dict | None, str | None, int | None]:
        """Trả về (dữ liệu, lỗi, mã HTTP).

        openFDA trả HTTP 404 khi truy vấn không khớp bản ghi nào; đó là "không có kết
        quả", không phải lỗi mạng. Mã 404 được ghi lại và xử lý riêng ở tầng dựng bản
        ghi. Lỗi mạng/5xx được trả về nguyên văn để không sinh nhãn âm tính giả.
        """
        path = self.root / f"{key}.json"
        if path.exists() and not self.force:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.served_from_cache += 1
            return payload, None, int(self.index.get(key, {}).get("http_status", 200))
        if self.offline:
            return None, "offline_mode: thiếu bản thô", None
        last_error = ""
        for attempt in range(3):
            self._throttle()
            try:
                response = self._client.get(url)
            except httpx.HTTPError as exc:
                last_error = f"network: {exc.__class__.__name__}: {exc}"
                time.sleep(0.8 * (attempt + 1))
                continue
            if response.status_code in {200, 404}:
                body = response.content
                payload = json.loads(body.decode("utf-8")) if response.status_code == 200 else None
                path.write_bytes(body)
                self.index[key] = {
                    "url": url,
                    "http_status": response.status_code,
                    "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "sha256": sha256_bytes(body),
                    "bytes": len(body),
                }
                self.index_path.write_text(
                    json.dumps(self.index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                self.fetched += 1
                return payload, None, response.status_code
            last_error = f"http_{response.status_code}"
            if response.status_code in {429, 500, 502, 503, 504}:
                time.sleep(min(2.0 * (attempt + 1), 10.0))
                continue
            break
        return None, last_error, None

    def retrieved_at(self, key: str) -> str | None:
        entry = self.index.get(key) or {}
        return entry.get("retrieved_at")

    def close(self) -> None:
        self._client.close()


# ------------------------------------------------------------------ dựng bản ghi
def drug_slug(generic_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", generic_name.lower()).strip("-")


def build_pair(
    *,
    spec: dict,
    drug: dict,
    event: dict,
    label: dict | None,
    label_error: str | None,
    label_status: int | None,
    drug_total: int | None,
    drug_status: int | None,
    event_total: int | None,
    event_status: int | None,
    term_observed: bool | None,
    retrieved_at: str | None,
    label_retrieved_at: str | None,
) -> dict:
    checked_sections = list(spec["label_rule"]["checked_sections"])
    priority = list(spec["label_rule"]["section_priority"])
    max_chars = int(spec["label_rule"].get("quote_max_chars", 400))
    slug = drug_slug(drug["generic_name"])
    pair_id = f"gold-p1-{slug}--{event['slug']}"

    evidence: dict = {
        "status": "no_label",
        "set_id": None,
        "spl_version": None,
        "spl_effective_time": None,
        "label_title": None,
        "label_url": None,
        "checked_sections": checked_sections,
        "matched_section": None,
        "matched_term": None,
        "matched_quote": None,
        "query_http_status": label_status,
        "retrieved_at": label_retrieved_at,
        "error": label_error,
    }
    if label is not None:
        set_id = str(label.get("set_id"))
        evidence.update(
            {
                "set_id": set_id,
                "spl_version": label.get("version"),
                "spl_effective_time": label.get("effective_time"),
                "label_title": label_title(label),
                "label_url": label_url(set_id),
                "error": None,
            }
        )
        texts = section_texts(label, checked_sections)
        if not texts:
            evidence["status"] = "no_section"
        else:
            hit: tuple[str, str, str] | None = None
            for section in priority:
                text = texts.get(section)
                if not text:
                    continue
                found = match_any(text, event["synonyms"], max_chars=max_chars)
                if found:
                    hit = (section, found[0], found[1])
                    break
            if hit:
                evidence.update(
                    {"status": "listed", "matched_section": hit[0], "matched_term": hit[1], "matched_quote": hit[2]}
                )
            else:
                evidence["status"] = "not_listed"

    faers = {
        "reports_drug_total": drug_total,
        "reports_drug_and_event": event_total,
        "term_observed": term_observed,
        "drug_query_http_status": drug_status,
        "pair_query_http_status": event_status,
        "drug_query_url": faers_api_url(drug["generic_name"]),
        "pair_query_url": faers_api_url(drug["generic_name"], event["meddra_pt"]),
        "retrieved_at": retrieved_at,
        "caveat": "Báo cáo tự nguyện của FAERS; không có mẫu số, có thể trùng lặp, không chứng minh nhân quả.",
    }
    if event_status == 404:
        faers["no_result_note"] = "openFDA trả HTTP 404: không có báo cáo nào khớp truy vấn (0 báo cáo)."
    if drug_status == 404:
        faers["drug_no_result_note"] = "openFDA trả HTTP 404 cho truy vấn theo hoạt chất (0 báo cáo)."

    if evidence["status"] == "listed":
        gold_label = "label_listed"
    elif evidence["status"] in {"not_listed", "no_section"}:
        gold_label = "label_not_listed"
    else:
        gold_label = None

    return {
        "pair_id": pair_id,
        "drug": drug["generic_name"],
        "drug_vn_name": drug.get("vn_name"),
        "drug_class": drug.get("drug_class"),
        "event": event["name"],
        "event_slug": event["slug"],
        "meddra_pt_query": event["meddra_pt"],
        "event_synonyms_used": event["synonyms"],
        "label_evidence": evidence,
        "faers_reports": faers,
        "gold_label": gold_label,
        "gold_basis": METHOD_VERSION,
        "split": "test" if (drug["index"] - 1) % 3 == 0 else "development",
        "review": {
            "status": "candidate_not_gold",
            "proposed_by": "machine",
            "reviewer_role_required": "clinical_pharmacist_or_pharmacovigilance_specialist",
            "reviewer_id": None,
            "reviewed_at": None,
            "notes": None,
        },
        "limitations": REVIEW_LIMITATIONS,
    }


def build_records(
    spec: dict, store: RawStore, *, limit_drugs: int | None = None
) -> tuple[list[dict], list[str], list[str]]:
    """Trả về (bản ghi, lỗi chặn, ghi chú không-có-kết-quả)."""
    records: list[dict] = []
    errors: list[str] = []
    notes: list[str] = []
    drugs = spec["drugs"][:limit_drugs] if limit_drugs else spec["drugs"]
    for drug in drugs:
        name = drug["generic_name"]
        slug = drug_slug(name)
        label_key = f"label__{slug}"
        payload, error, status = store.get_json(label_key, label_api_url(name))
        label = None
        if error is not None:
            errors.append(f"{label_key}: {error}")
        elif status == 404:
            notes.append(f"{label_key}: openFDA 404 - không có nhãn khớp truy vấn")
            error = "http_404: openFDA không có nhãn khớp truy vấn"
        else:
            label = select_label(payload.get("results") or [], name)
            if label is None:
                notes.append(f"{label_key}: nhãn khớp nhưng không có set_id dùng được")
                error = "no_usable_label: phản hồi không có set_id"
        label_retrieved_at = store.retrieved_at(label_key)

        drug_key = f"faers__{slug}__all"
        drug_payload, drug_error, drug_status = store.get_json(drug_key, faers_api_url(name))
        if drug_error is not None:
            errors.append(f"{drug_key}: {drug_error}")
            drug_total = None
        elif drug_status == 404:
            notes.append(f"{drug_key}: openFDA 404 - không có báo cáo cho hoạt chất")
            drug_total = 0
        else:
            drug_total = (drug_payload.get("meta", {}).get("results", {}) or {}).get("total")
        retrieved_at = store.retrieved_at(drug_key)

        for event in spec["events"]:
            pair_key = f"faers__{slug}__{event['slug']}"
            pair_payload, pair_error, pair_status = store.get_json(pair_key, faers_api_url(name, event["meddra_pt"]))
            if pair_error is not None:
                errors.append(f"{pair_key}: {pair_error}")
                event_total = None
                term_observed = None
            elif pair_status == 404:
                notes.append(f"{pair_key}: openFDA 404 - không có báo cáo khớp cặp")
                event_total = 0
                term_observed = None
            else:
                event_total = (pair_payload.get("meta", {}).get("results", {}) or {}).get("total")
                term_observed = bool(event_total)
            records.append(
                build_pair(
                    spec=spec,
                    drug=drug,
                    event=event,
                    label=label,
                    label_error=error,
                    label_status=status,
                    drug_total=drug_total,
                    drug_status=drug_status,
                    event_total=event_total,
                    event_status=pair_status,
                    term_observed=term_observed,
                    retrieved_at=retrieved_at,
                    label_retrieved_at=label_retrieved_at,
                )
            )
    return records, errors, notes


def write_jsonl(path: Path, records: list[dict]) -> str:
    lines = [json.dumps(record, ensure_ascii=False, sort_keys=False) for record in records]
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    return sha256_text(text)


def build_manifest(
    *,
    spec: dict,
    spec_path: Path,
    records: list[dict],
    dataset_path: Path,
    dataset_sha256: str,
    errors: list[str],
    notes: list[str],
    store: RawStore,
) -> dict:
    statuses: dict[str, int] = {}
    per_event: dict[str, int] = {}
    per_drug: dict[str, dict[str, int]] = {}
    for record in records:
        status = record["label_evidence"]["status"]
        statuses[status] = statuses.get(status, 0) + 1
        per_event[record["event"]] = per_event.get(record["event"], 0) + 1
        bucket = per_drug.setdefault(record["drug"], {})
        bucket[status] = bucket.get(status, 0) + 1
    listed = statuses.get("listed", 0)
    total = len(records)
    return {
        "version": spec["spec_version"],
        "method_version": METHOD_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": "candidate_not_gold",
        "review": {
            "proposed_by": "machine",
            "approved_by": None,
            "approval_required": "dược sĩ lâm sàng hoặc chuyên gia cảnh giác dược",
            "approval_note": "Mỗi nhãn phải được người duyệt đối chiếu URL nhãn và câu trích trước khi dùng chính thức.",
        },
        "scope": spec["scope"],
        "spec_file": rel(spec_path),
        "spec_sha256": sha256_text(spec_path.read_text(encoding="utf-8")),
        "dataset_file": rel(dataset_path),
        "dataset_sha256": dataset_sha256,
        "counts": {
            "pairs_total": total,
            "label_listed": listed,
            "label_not_listed": statuses.get("not_listed", 0),
            "no_section": statuses.get("no_section", 0),
            "no_label": statuses.get("no_label", 0),
            "listed_ratio": round(listed / total, 4) if total else 0,
            "per_status": statuses,
            "per_event": per_event,
            "per_drug": per_drug,
        },
        "sources": spec["sources"],
        "raw_snapshots": {
            "directory": rel(store.root),
            "committed": False,
            "note": "Bản thô không commit vì dung lượng; mỗi bản ghi đã mang URL truy vấn và số liệu để đối chiếu lại.",
            "files": {
                key: {"url": value.get("url"), "sha256": value.get("sha256"), "retrieved_at": value.get("retrieved_at")}
                for key, value in sorted(store.index.items())
            },
        },
        "errors": errors,
        "no_result_notes": notes,
        "limitations": REVIEW_LIMITATIONS,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dựng bộ chuẩn vàng giai đoạn 1 từ nguồn công khai quốc tế.")
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--offline", action="store_true", help="Chỉ dùng bản thô đã lưu, không gọi mạng.")
    parser.add_argument("--force", action="store_true", help="Bỏ qua bản thô, gọi lại mạng.")
    parser.add_argument("--limit-drugs", type=int, default=None, help="Chỉ dựng cho N hoạt chất đầu (để thử).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    store = RawStore(args.raw, offline=args.offline, force=args.force)
    try:
        records, errors, notes = build_records(spec, store, limit_drugs=args.limit_drugs)
    finally:
        store.close()
    for line in errors:
        print(f"LỖI: {line}", file=sys.stderr)
    for line in notes:
        print(f"GHI CHÚ (không có kết quả): {line}", file=sys.stderr)
    digest = write_jsonl(args.out, records)
    manifest = build_manifest(
        spec=spec,
        spec_path=args.spec,
        records=records,
        dataset_path=args.out,
        dataset_sha256=digest,
        errors=errors,
        notes=notes,
        store=store,
    )
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = manifest["counts"]
    print(f"Đã ghi {args.out} ({len(records)} cặp, sha256={digest})")
    print(
        f"  listed={counts['label_listed']} not_listed={counts['label_not_listed']} "
        f"no_section={counts['no_section']} no_label={counts['no_label']}"
    )
    print(f"  mạng: {store.fetched} yêu cầu mới, {store.served_from_cache} dùng bản thô")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
