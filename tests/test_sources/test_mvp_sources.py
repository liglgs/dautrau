"""Exercise real source adapters with synthetic HTTP responses, never provider calls."""

import hashlib
import json

import httpx
import pytest

from src.models.schemas import BudgetState, PlannerActionKind, PlannerDecision, SourceStatus


def action(source, query="ibuprofen bleeding"):
    return PlannerDecision(action=PlannerActionKind.SEARCH_SOURCE, source=source, query=query, reason="test")


def adapters(tmp_path, handler):
    from src.services.sources import build_adapters
    from src.services.sources.transport import SourceTransport

    transport = SourceTransport(client=httpx.Client(transport=httpx.MockTransport(handler)), interval=0)
    return build_adapters(transport=transport, snapshot_root=tmp_path, drug="ibuprofen", event="bleeding")


def test_pubmed_batch_preserves_sections_and_missing_abstract(tmp_path):
    def handler(request):
        if request.url.path.endswith("esearch.fcgi"):
            assert request.url.params["term"] == "ibuprofen bleeding"
            return httpx.Response(200, json={"esearchresult": {"idlist": ["123", "124"]}})
        assert request.url.params["id"] == "123,124"
        return httpx.Response(
            200,
            headers={"content-type": "application/xml"},
            content=b"""<PubmedArticleSet>
        <PubmedArticle><MedlineCitation><PMID Version="1">123</PMID><Article><ArticleTitle>Trial</ArticleTitle>
        <Abstract><AbstractText Label="RESULTS">Bleeding observed.</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle>
        <PubmedArticle><MedlineCitation><PMID>124</PMID><Article><ArticleTitle>No abstract</ArticleTitle></Article></MedlineCitation></PubmedArticle>
        </PubmedArticleSet>""",
        )

    result = adapters(tmp_path, handler)["pubmed"].search(action("pubmed"), BudgetState())
    assert result.status == SourceStatus.OK
    assert result.documents[0].text == "Trial\n\nRESULTS\nBleeding observed."
    assert result.documents[1].metadata["content_level"] == "metadata_only"
    assert "missing_abstract" in result.documents[1].metadata["warnings"]
    assert result.documents[0].metadata["sections"][0]["start"] == 7
    assert result.documents[0].hash == hashlib.sha256(result.documents[0].text.encode()).hexdigest()
    assert result.requests_used == 2


def test_dailymed_keeps_products_and_actual_xml_version(tmp_path):
    def handler(request):
        if request.url.path.endswith("spls.json"):
            assert request.url.params["drug_name"] == "ibuprofen"
            return httpx.Response(
                200, json={"data": [{"setid": "a", "title": "Oral"}, {"setid": "b", "title": "Topical"}]}
            )
        route = "ORAL" if request.url.path.endswith("a.xml") else "TOPICAL"
        return httpx.Response(
            200,
            headers={"content-type": "application/xml"},
            content=f'''<document xmlns="urn:hl7-org:v3"><setId root="{request.url.path[-5]}"/><versionNumber value="3"/><title>Label</title><routeCode displayName="{route}"/><component><section><title>Warnings</title><text>Bleeding warning.</text></section></component></document>'''.encode(),
        )

    result = adapters(tmp_path, handler)["dailymed"].search(action("dailymed"), BudgetState())
    assert len(result.documents) == 2
    assert [d.metadata["routes"] for d in result.documents] == [["ORAL"], ["TOPICAL"]]
    assert result.documents[0].version == 3
    assert result.documents[0].text == "Label\n\nWarnings\nBleeding warning."
    assert result.documents[0].doc_id != result.documents[1].doc_id


def test_faers_preserves_missing_fields_and_other_drugs(tmp_path):
    report = {
        "safetyreportid": "99",
        "safetyreportversion": "2",
        "patient": {
            "drug": [
                {"medicinalproduct": "IBUPROFEN"},
                {"medicinalproduct": "OTHER", "drugadministrationroute": "048"},
            ],
            "reaction": [{"reactionmeddrapt": "Bleeding"}],
        },
    }

    def handler(request):
        assert 'patient.reaction.reactionmeddrapt:"bleeding"' in request.url.params["search"]
        return httpx.Response(200, json={"meta": {"results": {"total": 4}}, "results": [report, report]})

    result = adapters(tmp_path, handler)["faers"].search(action("faers"), BudgetState())
    assert len(result.documents) == 1
    metadata = result.documents[0].metadata
    assert metadata["matched_drugs"][0]["drugadministrationroute"] is None
    assert metadata["reactions"] == ["Bleeding"]
    assert metadata["total_hits"] == 4
    assert "report_level_not_causal_pair" in metadata["warnings"]
    assert json.loads(result.documents[0].text)["patient"]["drug"][1]["medicinalproduct"] == "OTHER"


def test_source_error_is_not_cached_as_empty(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) <= 2 else 200, json={"esearchresult": {"idlist": []}})

    adapter = adapters(tmp_path, handler)["pubmed"]
    first = adapter.search(action("pubmed"), BudgetState())
    assert first.status == SourceStatus.ERROR
    second = adapter.search(action("pubmed"), BudgetState())
    assert second.status == SourceStatus.EMPTY
    assert len(calls) == 3


def test_transport_rejects_redirect_and_enforces_budget(tmp_path):
    result = adapters(tmp_path, lambda _: httpx.Response(302, headers={"location": "https://evil.test"}))[
        "pubmed"
    ].search(action("pubmed"), BudgetState())
    assert result.status == SourceStatus.ERROR
    assert "redirect" in result.error
    result = adapters(tmp_path, lambda _: httpx.Response(429))["pubmed"].search(
        action("pubmed"), BudgetState(max_source_requests=1)
    )
    assert result.requests_used == 1
    assert "budget_exhausted" in result.error


def test_parser_rejects_external_entities(tmp_path):
    xml = b'<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///etc/passwd">]><PubmedArticleSet>&secret;</PubmedArticleSet>'

    def handler(request):
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(200, json={"esearchresult": {"idlist": ["1"]}})
        return httpx.Response(200, content=xml, headers={"content-type": "application/xml"})

    result = adapters(tmp_path, handler)["pubmed"].search(action("pubmed"), BudgetState())
    assert result.status == SourceStatus.ERROR
    assert "parse_error" in result.error


def test_successful_cache_returns_same_provenance_without_http(tmp_path):
    def handler(request):
        return httpx.Response(200, json={"esearchresult": {"idlist": []}})

    adapter = adapters(tmp_path, handler)["pubmed"]
    assert adapter.search(action("pubmed"), BudgetState()).requests_used == 1
    assert adapter.search(action("pubmed"), BudgetState()).requests_used == 0


def test_transport_does_not_fetch_foreign_host():
    from src.services.sources.transport import SourceError, SourceTransport

    with pytest.raises(SourceError, match="invalid_query"):
        SourceTransport(interval=0).get("https://evil.test/x", {}, BudgetState())


def test_utf16_xml_cannot_expand_entities():
    from src.services.sources.parser import safe_xml
    from src.services.sources.transport import SourceError

    malicious = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE x [<!ENTITY content "expanded">]><x>&content;</x>'
    with pytest.raises(SourceError, match="parse_error"):
        safe_xml(malicious.encode("utf-16"))


def test_faers_404_no_matches_is_empty(tmp_path):
    result = adapters(
        tmp_path, lambda _: httpx.Response(404, json={"error": {"code": "NOT_FOUND", "message": "No matches found!"}})
    )["faers"].search(action("faers"), BudgetState())
    assert result.status == SourceStatus.EMPTY


def test_transport_caps_size_before_parser(tmp_path):
    from src.services.sources.transport import SourceError, SourceTransport

    transport = SourceTransport(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, content=b"x" * 20, headers={"content-type": "application/xml"})
            )
        ),
        interval=0,
        max_bytes=10,
    )
    with pytest.raises(SourceError, match="response too large"):
        transport.get("https://dailymed.nlm.nih.gov/large.xml", {}, BudgetState())


def test_parser_preserves_unicode_offsets_and_warns_truncation():
    from src.services.sources.parser import document

    doc = document(
        "pubmed",
        "1",
        1,
        "Title",
        "https://pubmed.ncbi.nlm.nih.gov/1/",
        b"raw",
        [("Kết quả", "Thuốc gây buồn ngủ.\n" + "x" * 210_000)],
        {},
    )
    section = doc.metadata["sections"][0]
    assert doc.text[section["start"] : section["start"] + 7] == "Kết quả"
    assert "truncated_document" in doc.metadata["warnings"]
    assert len(doc.text) == 200_000


def test_faers_null_optional_names_do_not_crash(tmp_path):
    report = {
        "safetyreportid": "100",
        "patient": {"drug": [{"medicinalproduct": None, "openfda": None}], "reaction": None},
    }
    result = adapters(tmp_path, lambda _: httpx.Response(200, json={"results": [report]}))["faers"].search(
        action("faers"), BudgetState()
    )
    assert result.status == SourceStatus.OK
    assert result.documents[0].metadata["matched_drugs"] == []
    assert result.documents[0].metadata["reactions"] == []


@pytest.mark.parametrize("error", [httpx.RemoteProtocolError("incomplete read"), httpx.DecodingError("invalid gzip")])
def test_http_response_failures_return_typed_source_error(tmp_path, error):
    def handler(request):
        raise error

    result = adapters(tmp_path, handler)["pubmed"].search(action("pubmed"), BudgetState())
    assert result.status == SourceStatus.ERROR
    assert result.requests_used in (1, 2)


def test_faers_does_not_match_another_ingredient_prefix(tmp_path):
    report = {
        "safetyreportid": "100",
        "patient": {
            "drug": [
                {"medicinalproduct": "PREDNISOLONE", "drugadministrationroute": "oral"},
                {"medicinalproduct": "METHYLPREDNISOLONE", "drugadministrationroute": "intravenous"},
            ]
        },
    }
    adapter = adapters(tmp_path, lambda _: httpx.Response(200, json={"results": [report]}))["faers"]
    adapter.drug = "prednisolone"
    result = adapter.search(action("faers", "prednisolone bleeding"), BudgetState())
    assert [d["drugadministrationroute"] for d in result.documents[0].metadata["matched_drugs"]] == ["oral"]


def test_xml_block_and_table_boundaries_remain_separated():
    from src.services.sources.parser import safe_xml, text_of

    xml = b"<text><paragraph>Take one dose</paragraph><paragraph>with food</paragraph><table><tr><td>5</td><td>10</td></tr></table></text>"
    assert text_of(safe_xml(xml)) == "Take one dose with food 5 10"
    assert text_of(safe_xml(b"<text>micro<i>organisms</i></text>")) == "microorganisms"


def test_openfda_404_response_obeys_size_limit():
    from src.services.sources.transport import SourceError, SourceTransport

    transport = SourceTransport(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    404, content=b'"No matches found!"' + b"x" * 100, headers={"content-type": "application/json"}
                )
            )
        ),
        interval=0,
        max_bytes=32,
    )
    with pytest.raises(SourceError, match="response too large"):
        transport.get("https://api.fda.gov/drug/event.json", {}, BudgetState())
