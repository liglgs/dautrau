"""Synthetic Person 3 inputs and opt-in runtime for the shared LangGraph/API."""

import json
from copy import deepcopy
from pathlib import Path

from src.models.schemas import SourceDocument, SourceSearchResult, SourceStatus
from src.services.evidence.citations import text_hash
from src.services.evidence.integration import configure_person3
from src.services.llm import LLMGateway, MockProvider

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = {
    "match": ("Bằng chứng phù hợp", "supported_for_scope"),
    "route_mismatch": ("Claim oral, nguồn intravenous", "scope_mismatch"),
    "missing_scope": ("Nguồn thiếu liều claim yêu cầu", "insufficient_evidence"),
    "imprecise_null": ("Kết quả null còn bất định", "insufficient_evidence"),
    "fake_quote": ("Quote không có trong nguồn", "insufficient_evidence"),
    "contradiction": ("Hai nghiên cứu cùng scope trái chiều", "requires_human_review"),
    "ambiguous_brand": ("Brand có hai hoạt chất ứng viên", "requires_human_review"),
    "faers_only": ("Chỉ có báo cáo FAERS", "insufficient_evidence"),
}


def build_inputs(name):
    if name not in SCENARIOS:
        raise ValueError(f"Unknown Person 3 demo scenario: {name}")
    fixture = json.loads((ROOT / "tests/fixtures/mvp/person3/integration_demo.json").read_text(encoding="utf-8"))
    document, response = deepcopy(fixture["document"]), deepcopy(fixture["response"])
    finding = response["findings"][0]
    if name == "ambiguous_brand":
        fixture["claim"]["drug"] = "Brand Ambiguous"
    elif name == "route_mismatch":
        finding["scope"]["route"] = "intravenous"
    elif name == "missing_scope":
        finding["scope"]["dose"] = None
    elif name == "imprecise_null":
        finding.update(stance="contradicts", direction="no_clear_effect", uncertainty="high")
        finding["quote"] = "The fictional result was imprecise and found no clear difference for Event Alpha."
    elif name == "fake_quote":
        finding["quote"] = "This invented quotation never appeared in the document."
    elif name == "faers_only":
        document["source"] = "faers"

    # Explicit source context: fixtures do not borrow absent scope from the claim.
    context = "; ".join(f"{key}: {value}" for key, value in finding["scope"].items() if value)
    original_quote = fixture["document"]["text"] if name == "fake_quote" else finding["quote"]
    document["text"] = f"Synthetic context: {context}; comparator: placebo.\n{original_quote}"
    start = len(document["text"]) - len(original_quote)
    finding["locator"] = {"start": start, "end": start + len(original_quote)}
    inputs = [(document, response)]
    if name == "contradiction":
        other, negative = deepcopy(document), deepcopy(response)
        other["doc_id"] = "SYNTHETIC-DEMO-B"
        other["source_id"] = "synthetic-other-study"
        other["source_url"] = "https://example.org/synthetic/person3-demo-b"
        quote = "Drug Alpha decreased Event Alpha in a fictional controlled comparison."
        negative["findings"][0].update(quote=quote, stance="contradicts", direction="decrease")
        other["text"] = f"Synthetic context: {context}; comparator: placebo.\n{quote}"
        offset = len(other["text"]) - len(quote)
        negative["findings"][0]["locator"] = {"start": offset, "end": offset + len(quote)}
        inputs.append((other, negative))
    return fixture["claim"], inputs


def graph_inputs(name):
    """Full-graph fixture: two fictional documents allow testing the stop policy."""
    claim, inputs = build_inputs(name)
    if name == "match":
        other, response = deepcopy(inputs[0])
        other.update(
            doc_id="SYNTHETIC-DEMO-C",
            source_id="synthetic-independent-comparison",
            source_url="https://example.org/synthetic/person3-demo-c",
        )
        other["text"] = "Another fictional document.\n" + other["text"]
        response["findings"][0]["locator"]["start"] += len("Another fictional document.\n")
        response["findings"][0]["locator"]["end"] += len("Another fictional document.\n")
        inputs.append((other, response))
    for document, _ in inputs:
        document["doc_id"] += f"-{name}"
        document["source_id"] += f"-{name}"
        document["title"] = f"SYNTHETIC — Person 3: {name}"
    return claim, inputs


class SyntheticSourceAdapter:
    """Return authored documents once, then empty; no network/source connector."""

    def __init__(self, source, documents):
        self.name = source
        self.documents = [doc for doc in documents if doc.source == source]
        self.used = False

    def search(self, action, budget):
        documents = [] if self.used else self.documents
        self.used = True
        return SourceSearchResult(
            source=self.name, query=action.query or "", fingerprint=action.fingerprint or "",
            status=SourceStatus.OK if documents else SourceStatus.EMPTY, documents=documents,
        )


def make_demo_runtime(name="match"):
    """Use real Person 3 services and graph; only sources/LLM are synthetic."""
    _, inputs = graph_inputs(name)
    responses = {document["doc_id"]: response for document, response in inputs}
    documents = [SourceDocument(**document, hash=text_hash(document["text"])) for document, _ in inputs]

    def respond(prompt, system):
        for doc_id, response in responses.items():
            if doc_id in prompt:
                return deepcopy(response)
        raise ValueError("No synthetic response for the requested document")

    gateway = LLMGateway(MockProvider({"extract_evidence": respond}))

    def execute(state, ctx):
        from src.agents.graph import run_investigation

        configure_person3(ctx, ROOT / "data/dictionaries/person3_synthetic.json", allow_synthetic=True)
        ctx.scenario = {"name": name, "synthetic": True}
        ctx.adapters = {source: SyntheticSourceAdapter(source, documents) for source in ("pubmed", "dailymed", "faers")}
        ctx.emit(state.investigation_id, "runtime", "Person 3 demo: synthetic sources and model", {
            "mode": "person3_demo", "synthetic": True, "scenario": name,
        })
        return run_investigation(state, ctx)

    return execute, gateway

