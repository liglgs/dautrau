"""Verify quote provenance on exact text; semantic support remains a review gate."""

from hashlib import sha256
from urllib.parse import urlparse

from src.services.evidence.drafts import CitationCheckDraft, CitationDraft, DocumentDraft


def text_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def validate_citation(document: DocumentDraft, citation: CitationDraft) -> CitationCheckDraft:
    """Offsets are Unicode code points, start inclusive and end exclusive.

    This function does not fetch URLs, approve a dossier, or verify entailment.
    """
    errors = []
    for field in ("document_id", "source_id", "source_version", "source_url"):
        doc_value = getattr(document, field)
        if not doc_value or doc_value != getattr(citation, field):
            errors.append(f"{field}_mismatch")
    if document.content_hash != text_hash(document.text):
        errors.append("document_hash_mismatch")
    if citation.content_hash != document.content_hash:
        errors.append("citation_hash_mismatch")
    parsed_url = urlparse(citation.source_url)
    if (parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname
            or any(character.isspace() for character in citation.source_url)):
        errors.append("invalid_source_url")
    valid_locator = (
        isinstance(citation.start, int) and not isinstance(citation.start, bool)
        and isinstance(citation.end, int) and not isinstance(citation.end, bool)
        and 0 <= citation.start < citation.end <= len(document.text)
    )
    if not valid_locator:
        errors.append("invalid_locator")
    elif not citation.quoted_span.strip() or document.text[citation.start:citation.end] != citation.quoted_span:
        errors.append("quote_mismatch")
    return CitationCheckDraft(not errors, tuple(errors))


def validate_evidence_citation(document, evidence) -> CitationCheckDraft:
    """Strict public-schema citation check, with the saved extraction provenance."""
    from src.services.evidence.contracts import read_annotation

    annotation = read_annotation(evidence.notes)
    errors = []
    if evidence.source != document.source:
        errors.append("source_mismatch")
    if annotation is None:
        errors.append("missing_extraction_provenance")
    elif annotation.document_version != document.version or annotation.document_hash != document.hash:
        errors.append("source_version_or_hash_mismatch")
    draft = DocumentDraft(
        document.doc_id, document.source_id, str(document.version), document.source_url,
        document.text, document.hash,
    )
    citation = CitationDraft(
        evidence.doc_id, document.source_id, str(document.version), document.source_url,
        annotation.document_hash if annotation else document.hash,
        evidence.quote, evidence.locator.start, evidence.locator.end,
    )
    checked = validate_citation(draft, citation)
    errors.extend(checked.errors)
    return CitationCheckDraft(not errors, tuple(dict.fromkeys(errors)))
