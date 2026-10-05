"""Deterministic parsers; section offsets refer to exactly the stored text."""

import hashlib
import unicodedata
import xml.etree.ElementTree as ET

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException

from src.models.schemas import SourceDocument
from src.services.sources.transport import SourceError

PARSER_VERSION = "mvp-sources-1"


def safe_xml(raw):
    try:
        return SafeET.fromstring(raw)
    except (ET.ParseError, DefusedXmlException) as exc:
        raise SourceError("parse_error: malformed XML") from exc


def text_of(node):
    if node is None:
        return ""
    blocks = {"paragraph", "p", "br", "item", "li", "list", "table", "tr", "td", "th"}
    parts = []

    def collect(element):
        name = element.tag.rsplit("}", 1)[-1].lower()
        if name in {"script", "style"}:
            return
        if name in blocks:
            parts.append(" ")
        parts.append(element.text or "")
        for child in element:
            collect(child)
            parts.append(child.tail or "")
        if name in blocks:
            parts.append(" ")

    collect(node)
    return unicodedata.normalize("NFC", " ".join("".join(parts).split()))


def document(source, source_id, version, title, url, raw, sections, metadata):
    title = title[:500]
    text = title
    locators = []
    warnings = list(metadata.get("warnings", []))
    for label, body in sections:
        if not body:
            continue
        label = label[:200]
        start = len(text) + 2
        segment = f"{label}\n{body}"
        remaining = 200_000 - start
        if remaining <= 0:
            warnings.append("truncated_document")
            break
        kept = segment[:remaining]
        text += "\n\n" + kept
        locators.append({"title": label, "start": start, "end": len(text)})
        if len(kept) != len(segment):
            warnings.append("truncated_document")
    text = text or source_id
    digest = hashlib.sha256(text.encode()).hexdigest()
    metadata = {
        **metadata,
        "parser_version": PARSER_VERSION,
        "raw_hash": hashlib.sha256(raw).hexdigest(),
        "parsed_hash": digest,
        "sections": locators,
        "warnings": list(dict.fromkeys(warnings)),
    }
    return SourceDocument(
        doc_id=f"{source}:{source_id}:{version}",
        source=source,
        source_id=source_id,
        version=version,
        title=title,
        source_url=url,
        text=text,
        hash=digest,
        metadata=metadata,
    )
