"""Tầng Parse: bản thô -> bản ghi chuẩn (canonical) dùng lại đúng bộ phân tích của ứng dụng.

Dùng lại ``src.services.sources.parser.document`` nên văn bản, mã tài liệu và băm
trùng khớp với những gì ứng dụng tạo ra khi chạy nguồn trực tiếp. Nhờ đó gói 50 mẫu
có thể tái lập từ bản thô và đối chiếu băm với tệp JSON đã phát hành.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import httpx

from src.models.schemas import SourceDocument
from src.services.sources.parser import document, safe_xml, text_of
from src.services.sources.pubmed_local import _records as pubmed_tagged_records

DAILYM_MED_NS = {"s": "urn:hl7-org:v3"}


@dataclass
class ParsedDocument:
    doc_id: str
    source: str
    source_id: str
    version: int
    title: str
    text: str
    text_sha256: str
    source_url: str
    content_level: str
    metadata: dict = field(default_factory=dict)
    sections: list[dict] = field(default_factory=list)
    pair_id: str | None = None
    raw_sha256: str = ""
    raw_path: str = ""
    structured: dict = field(default_factory=dict)

    @property
    def warnings(self) -> list[str]:
        return list(self.metadata.get("warnings", []))


def _wrap(source_document, *, pair_id: str | None, raw_path: str, structured: dict | None = None) -> ParsedDocument:
    metadata = dict(source_document.metadata or {})
    return ParsedDocument(
        doc_id=source_document.doc_id,
        source=source_document.source,
        source_id=source_document.source_id,
        version=int(source_document.version),
        title=source_document.title,
        text=source_document.text,
        text_sha256=source_document.hash,
        source_url=source_document.source_url,
        content_level=str(metadata.get("content_level", "")),
        metadata=metadata,
        sections=list(metadata.get("sections", [])),
        pair_id=pair_id,
        raw_sha256=str(metadata.get("raw_hash", "")),
        raw_path=raw_path,
        structured=structured or {},
    )


# ------------------------------------------------------------------ PubMed
def parse_pubmed_xml(raw: bytes, *, pair_id: str | None, raw_path: str) -> list[ParsedDocument]:
    root = safe_xml(raw)
    parsed: list[ParsedDocument] = []
    for article in root.findall("PubmedArticle"):
        pmid = article.find("./MedlineCitation/PMID")
        if pmid is None or not (pmid.text or "").strip():
            continue
        title = text_of(article.find("./MedlineCitation/Article/ArticleTitle"))
        sections = [
            (item.get("Label", "Abstract"), text_of(item))
            for item in article.findall("./MedlineCitation/Article/Abstract/AbstractText")
        ]
        doi = [
            item.text for item in article.findall("./PubmedData/ArticleIdList/ArticleId")
            if item.get("IdType") == "doi"
        ]
        metadata = {
            "content_level": "abstract_only" if sections else "metadata_only",
            "doi": [d for d in doi if d],
            "publication_types": [text_of(n) for n in article.findall(".//PublicationType")],
            "publication_date": text_of(article.find(".//PubDate")),
            "journal": text_of(article.find("./MedlineCitation/Article/Journal/Title")),
            "authors": [
                text_of(author.find("./LastName")) + " " + text_of(author.find("./Initials"))
                for author in article.findall("./MedlineCitation/Article/AuthorList/Author")
                if text_of(author.find("./LastName"))
            ],
            "source_record_version": None,
            "version_semantics": "PubMed revision not verified at fetch time",
            "warnings": [] if sections else ["missing_abstract"],
        }
        source_document = document(
            "pubmed", (pmid.text or "").strip(), int(pmid.get("Version", "1")),
            title, f"https://pubmed.ncbi.nlm.nih.gov/{(pmid.text or '').strip()}/",
            raw, sections, metadata,
        )
        structured = {
            "pmid": source_document.source_id,
            "journal": metadata["journal"],
            "publication_date": metadata["publication_date"],
            "doi": metadata["doi"],
            "authors": metadata["authors"],
            "publication_types": metadata["publication_types"],
            "has_abstract": bool(sections),
            "abstract_labels": [label for label, body in sections if body],
        }
        parsed.append(_wrap(source_document, pair_id=pair_id, raw_path=raw_path, structured=structured))
    return parsed


def parse_pubmed_tagged(raw: bytes, *, pair_id: str | None, raw_path: str, query: str = "") -> list[ParsedDocument]:
    records = pubmed_tagged_records(raw)
    parsed: list[ParsedDocument] = []
    for record in records:
        pmid = record["PMID"][0]
        abstract = " ".join(record.get("AB", []))
        metadata = {
            "content_level": "abstract_only" if abstract else "metadata_only",
            "doi": [v.removesuffix(" [doi]") for v in record.get("AID", []) if v.endswith(" [doi]")],
            "publication_date": record.get("DP", []),
            "publication_types": record.get("PT", []),
            "authors": record.get("AU", []),
            "journal": record.get("JT", []),
            "search_query": query,
            "source_record_version": None,
            "version_semantics": "local_collection_version_not_verified_PubMed_revision",
            "warnings": ["source_revision_unknown", *(["missing_abstract"] if not abstract else [])],
        }
        source_document = document(
            "pubmed", pmid, 1, " ".join(record["TI"]),
            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", raw,
            [("Abstract", abstract)] if abstract else [], metadata,
        )
        structured = {
            "pmid": pmid,
            "journal": (metadata["journal"] or [""])[0],
            "publication_date": (metadata["publication_date"] or [""])[0],
            "doi": metadata["doi"],
            "authors": metadata["authors"],
            "publication_types": metadata["publication_types"],
            "has_abstract": bool(abstract),
        }
        parsed.append(_wrap(source_document, pair_id=pair_id, raw_path=raw_path, structured=structured))
    return parsed


# ------------------------------------------------------------------ DailyMed
def parse_dailymed_xml(
    raw: bytes,
    *,
    pair_id: str | None,
    raw_path: str,
    expected_setid: str | None = None,
    published_date: str | None = None,
) -> ParsedDocument:
    root = safe_xml(raw)
    identity = root.find("s:setId", DAILYM_MED_NS)
    version = root.find("s:versionNumber", DAILYM_MED_NS)
    setid = identity.get("root") if identity is not None else expected_setid
    if expected_setid and setid != expected_setid:
        raise ValueError(f"SETID không khớp: {setid} != {expected_setid}")
    if version is None:
        raise ValueError("Nhãn thiếu versionNumber")
    sections = [
        (text_of(section.find("s:title", DAILYM_MED_NS)) or "Section", text_of(section.find("s:text", DAILYM_MED_NS)))
        for section in root.findall(".//s:section", DAILYM_MED_NS)
    ]
    effective_time = root.find("s:effectiveTime", DAILYM_MED_NS)
    ingredient_names: list[str] = []
    for code in ("ACTIB", "ACTIM", "ACTIR"):
        ingredient_names.extend(
            text_of(n)
            for n in root.findall(f".//s:ingredient[@classCode='{code}']/s:ingredientSubstance/s:name", DAILYM_MED_NS)
            if text_of(n)
        )
    ingredients = list(dict.fromkeys(ingredient_names))
    routes = list(dict.fromkeys(
        (n.get("displayName") or n.get("code")) for n in root.findall(".//s:routeCode", DAILYM_MED_NS)
    ))
    metadata = {
        "content_level": "label_sections",
        "routes": routes,
        "ingredients": ingredients,
        "effective_time": effective_time.get("value") if effective_time is not None else None,
        "published_date": published_date,
        "warnings": ["current_label_only", "candidate_label_not_verified_product_match"],
    }
    if not any(body for _, body in sections):
        metadata["warnings"].append("missing_sections")
    title = text_of(root.find("s:title", DAILYM_MED_NS)) or (setid or "")
    source_document = document(
        "dailymed", str(setid), int(version.get("value")),
        title, f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={quote(str(setid), safe='')}",
        raw, sections, metadata,
    )
    structured = {
        "setid": str(setid),
        "version": int(version.get("value")),
        "effective_time": metadata["effective_time"],
        "published_date": published_date,
        "routes": routes,
        "ingredients": ingredients,
        "n_sections": len(sections),
        "single_ingredient": len([i for i in ingredients if i]) == 1,
    }
    return _wrap(source_document, pair_id=pair_id, raw_path=raw_path, structured=structured)


def dailymed_index_entries(raw: bytes) -> list[dict]:
    payload = json.loads(raw.decode("utf-8"))
    entries = payload.get("data") or []
    return [
        {
            "setid": item.get("setid"),
            "title": item.get("title"),
            "published_date": item.get("published_date"),
            "spl_version": item.get("spl_version"),
        }
        for item in entries
    ]


# ------------------------------------------------------------------ FAERS
def _faers_report_document(report: dict, raw: bytes, *, pair_id: str | None, raw_path: str,
                           drug: str = "", total_hits: int | None = None) -> ParsedDocument:
    report_id = str(report["safetyreportid"])
    version = int(report.get("safetyreportversion", "1"))
    patient = report.get("patient") or {}
    matches = []
    for item in patient.get("drug") or []:
        names = [item.get("medicinalproduct"), *((item.get("openfda") or {}).get("generic_name") or [])]
        if not drug or any(
            isinstance(name, str) and drug.casefold() in name.casefold() for name in names
        ):
            matches.append({
                "medicinalproduct": item.get("medicinalproduct"),
                "drugadministrationroute": item.get("drugadministrationroute"),
                "drugdosagetext": item.get("drugdosagetext"),
                "drugcharacterization": item.get("drugcharacterization"),
            })
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(text.encode()).hexdigest()
    reactions = patient.get("reaction") or []
    metadata = {
        "content_level": "spontaneous_report",
        "matched_drugs": matches,
        "age": patient.get("patientonsetage"),
        "age_unit": patient.get("patientonsetageunit"),
        "sex": patient.get("patientsex"),
        "reactions": [r.get("reactionmeddrapt") for r in reactions],
        "total_hits": total_hits,
        "warnings": ["report_level_not_causal_pair", "counts_not_incidence", "latest_observed_report_version"],
    }
    source_document = SourceDocument(
        doc_id=f"faers:{report_id}:{version}",
        source="faers",
        source_id=report_id,
        version=version,
        title=f"FAERS report {report_id}",
        source_url=str(httpx.URL("https://api.fda.gov/drug/event.json",
                                 params={"search": f'safetyreportid:"{report_id}"'})),
        text=text,
        hash=digest,
        metadata={
            **metadata,
            "parser_version": "mvp-sources-1",
            "raw_hash": hashlib.sha256(raw).hexdigest(),
            "parsed_hash": digest,
            "warnings": list(dict.fromkeys(metadata["warnings"])),
        },
    )
    drugs = []
    for item in patient.get("drug") or []:
        openfda = item.get("openfda") or {}
        drugs.append({
            "medicinalproduct": item.get("medicinalproduct"),
            "generic_name": (openfda.get("generic_name") or [None])[0],
            "brand_name": (openfda.get("brand_name") or [None])[0],
            "substance_name": (openfda.get("substance_name") or [None])[0],
            "route": item.get("drugadministrationroute"),
            "dose_text": item.get("drugdosagetext"),
            "characterization": item.get("drugcharacterization"),
            "indication": item.get("drugindication"),
            "start_date": item.get("drugstartdate"),
            "end_date": item.get("drugenddate"),
            "treatment_duration": item.get("drugtreatmentduration"),
        })
    structured = {
        "safetyreportid": report_id,
        "report_version": version,
        "receivedate": report.get("receivedate"),
        "occurcountry": report.get("occurcountry"),
        "serious": report.get("serious"),
        "patient_sex": patient.get("patientsex"),
        "patient_age": patient.get("patientonsetage"),
        "patient_age_unit": patient.get("patientonsetageunit"),
        "reporter_country": (report.get("primarysource") or {}).get("reportercountry"),
        "n_drugs": len(patient.get("drug") or []),
        "n_reactions": len(reactions),
        "total_hits": total_hits,
        "matched_drugs": matches,
        "reactions": [
            {"term": r.get("reactionmeddrapt"), "outcome": r.get("reactionoutcome")} for r in reactions
        ],
        "drugs": drugs,
    }
    return _wrap(source_document, pair_id=pair_id, raw_path=raw_path, structured=structured)


def parse_faers_json(raw: bytes, *, pair_id: str | None, raw_path: str, drug: str = "") -> list[ParsedDocument]:
    payload = json.loads(raw.decode("utf-8"))
    if "error" in payload and not payload.get("results"):
        raise ValueError(f"openFDA trả về lỗi: {str(payload.get('error'))[:200]}")
    total_hits = (payload.get("meta", {}).get("results", {}) or {}).get("total")
    parsed = []
    for report in payload.get("results") or []:
        parsed.append(_faers_report_document(report, raw, pair_id=pair_id, raw_path=raw_path,
                                             drug=drug, total_hits=total_hits))
    return parsed


def load_raw(path: Path) -> bytes:
    return Path(path).read_bytes()


# ------------------------------------------------------------------ Tài liệu tham chiếu (không thuộc 3 nguồn chính)
def _text_from_html(raw: bytes) -> tuple[str, str]:
    """Trả về (tiêu đề, văn bản) sau khi bỏ thẻ HTML. Không thực thi script/style."""
    from html.parser import HTMLParser

    class Extractor(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []
            self.title: list[str] = []
            self._skip = 0
            self._in_title = False

        def handle_starttag(self, tag, attrs):
            if tag in {"script", "style"}:
                self._skip += 1
            elif tag == "title":
                self._in_title = True
            elif tag in {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "td", "th"}:
                self.parts.append("\n")

        def handle_endtag(self, tag):
            if tag in {"script", "style"} and self._skip:
                self._skip -= 1
            elif tag == "title":
                self._in_title = False
            elif tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4"}:
                self.parts.append("\n")

        def handle_data(self, data):
            if self._skip:
                return
            if self._in_title:
                self.title.append(data)
            else:
                self.parts.append(data)

    parser = Extractor()
    parser.feed(raw.decode("utf-8", errors="replace"))
    text = "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())
    title = " ".join("".join(parser.title).split())
    return title, text


def _text_from_pdf(raw: bytes) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - phụ thuộc tùy chọn
        raise RuntimeError("pypdf_not_installed") from exc
    import io

    reader = PdfReader(io.BytesIO(raw))
    title = ""
    if reader.metadata and reader.metadata.title:
        title = str(reader.metadata.title)
    pages = [page.extract_text() or "" for page in reader.pages]
    return title, "\n".join(pages).strip()


def reference_document(
    raw: bytes,
    *,
    source_id: str,
    title: str,
    text: str,
    url: str,
    raw_path: str,
    kind: str,
    metadata: dict | None = None,
) -> ParsedDocument:
    """Tạo bản ghi tham chiếu (khuyến cáo, hướng dẫn, bài học quy trình) cho kho và RAG."""
    body = (text or "").strip()
    clipped = body[:200_000]
    digest = hashlib.sha256(clipped.encode("utf-8")).hexdigest()
    info = {
        "content_level": kind,
        "parser_version": "elt-reference-v1",
        "raw_hash": hashlib.sha256(raw).hexdigest(),
        "parsed_hash": digest,
        "sections": [],
        "warnings": ["reference_material_not_primary_evidence"],
        **(metadata or {}),
    }
    return ParsedDocument(
        doc_id=f"reference:{source_id}:1",
        source="reference",
        source_id=source_id,
        version=1,
        title=title[:500],
        text=clipped or source_id,
        text_sha256=digest,
        source_url=url,
        content_level=kind,
        metadata=info,
        sections=[],
        pair_id=None,
        raw_sha256=info["raw_hash"],
        raw_path=raw_path,
        structured={"kind": kind, **{k: v for k, v in (metadata or {}).items() if k != "sections"}},
    )


def parse_reference_file(path: Path, *, url: str = "", kind: str | None = None) -> ParsedDocument:
    """Phân tích một tệp tham chiếu: XML/HTML/TXT/PDF -> văn bản sạch."""
    raw = Path(path).read_bytes()
    suffix = Path(path).suffix.lower()
    if suffix in {".html", ".htm"}:
        title, text = _text_from_html(raw)
        return reference_document(raw, source_id=Path(path).stem, title=title or Path(path).stem,
                                  text=text, url=url, raw_path=str(path), kind=kind or "web_page")
    if suffix == ".pdf":
        title, text = _text_from_pdf(raw)
        return reference_document(raw, source_id=Path(path).stem, title=title or Path(path).stem,
                                  text=text, url=url, raw_path=str(path), kind=kind or "pdf_document")
    text = raw.decode("utf-8", errors="replace")
    return reference_document(raw, source_id=Path(path).stem, title=Path(path).stem,
                              text=text, url=url, raw_path=str(path), kind=kind or "text_document")
