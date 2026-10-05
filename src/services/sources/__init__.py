"""PubMed, DailyMed and FAERS adapters for the synchronous MVP runtime."""

from src.services.sources.dailymed import DailyMedAdapter
from src.services.sources.faers import FAERSAdapter
from src.services.sources.pubmed import PubMedAdapter
from src.services.sources.pubmed_local import LocalPubMedAdapter
from src.services.sources.transport import SourceTransport


def build_adapters(
    *,
    transport=None,
    snapshot_root="data/snapshots",
    drug="",
    event="",
    max_documents=5,
    pubmed_mode="api",
    pubmed_corpus_root="data/pubmed-local",
):
    transport = transport or SourceTransport()
    options = dict(
        transport=transport, snapshot_root=snapshot_root, drug=drug, event=event, max_documents=max_documents
    )
    if pubmed_mode not in {"api", "local"}:
        raise ValueError("Unsupported PubMed mode")
    pubmed = (
        LocalPubMedAdapter(corpus_root=pubmed_corpus_root, **options)
        if pubmed_mode == "local"
        else PubMedAdapter(**options)
    )
    return {"pubmed": pubmed, "dailymed": DailyMedAdapter(**options), "faers": FAERSAdapter(**options)}
