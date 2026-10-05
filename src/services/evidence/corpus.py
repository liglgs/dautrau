"""Read Person 1's frozen candidate bundle without changing source snapshots."""

import json
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path, PurePosixPath

from src.models.schemas import SourceDocument, SourceSearchResult
from src.services.evidence.citations import text_hash


@dataclass
class CandidateCorpus:
    bundle_hash: str
    collection: dict
    documents: list[SourceDocument]
    reviews: list[dict]
    families: dict[str, list[str]]
    file_count: int
    ingredient_relations: dict[str, list[dict]] = field(default_factory=dict)

    def documents_for(self, family):
        if family not in self.families:
            raise ValueError(f"Unknown family: {family}")
        ids = set(self.families[family])
        return [d.model_copy(deep=True) for d in self.documents if d.doc_id in ids]

    def audit(self):
        return {"bundle_sha256": self.bundle_hash, "status": "candidate_not_gold",
                "documents": len(self.documents), "checksummed_files": self.file_count,
                "counts": {s: sum(d.source == s for d in self.documents) for s in ("pubmed", "dailymed", "faers")},
                "families": self.families, "pending_reviews": sum(r["review_decision"] == "pending" for r in self.reviews),
                "gold_labels": sum(r.get("gold_label") is not None for r in self.reviews),
                "validation": "schema, bundle files, parsed/raw hashes, unique IDs, review IDs and section bounds passed",
                "external_source_authenticity_checked": False}


def load_candidate_corpus(path: str | Path) -> CandidateCorpus:
    path = Path(path)
    bundle_hash = sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entries")
        if sum(i.file_size for i in z.infolist()) > 50_000_000:
            raise ValueError("Candidate bundle exceeds 50 MB uncompressed")
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name:
                raise ValueError(f"Unsafe bundle path: {name}")
        hashes = json.loads(z.read("files.sha256.json"))
        if set(hashes) != set(names) - {"files.sha256.json"}:
            raise ValueError("Checksum manifest must cover every data file")
        for name, expected in hashes.items():
            if sha256(z.read(name)).hexdigest() != expected:
                raise ValueError(f"File hash mismatch: {name}")
        collection = json.loads(z.read("collection.json"))
        reviews = [json.loads(line) for line in z.read("review.jsonl").decode("utf-8").splitlines() if line.strip()]
        documents, families, identities, ingredient_relations = {}, {}, {}, {}
        for pair in collection["pairs"]:
            family = pair["drug"]
            if family in families:
                raise ValueError(f"Repeated family: {family}")
            families[family] = []
            for source in ("pubmed", "dailymed", "faers"):
                entry = pair["sources"][source]
                data = json.loads(z.read(entry["file"]))
                if source == "faers":
                    # Collection metadata is not a field in Person 2's public
                    # search contract. Accept this one documented extension only.
                    search = dict(data)
                    used = search.pop("requests_used", 0)
                    if not isinstance(used, int) or used < 0:
                        raise ValueError("Invalid collection requests_used")
                    result = SourceSearchResult.model_validate(search)
                    if result.source != source or str(result.status) != "ok":
                        raise ValueError(f"Unsuccessful collected source: {family}/{source}")
                    batch = result.documents
                else:
                    batch = [SourceDocument.model_validate(d) for d in data]
                if len(batch) != entry["count"]:
                    raise ValueError(f"Count mismatch: {family}/{source}")
                for d in batch:
                    if d.source != source or d.hash != text_hash(d.text) or d.metadata.get("parsed_hash") != d.hash:
                        raise ValueError(f"Source/parsed hash mismatch: {d.doc_id}")
                    if sha256(z.read(d.metadata["raw_ref"])).hexdigest() != d.metadata["raw_hash"]:
                        raise ValueError(f"Raw hash mismatch: {d.doc_id}")
                    if source == "dailymed":
                        ingredient_relations[d.doc_id] = spl_ingredient_relations(z.read(d.metadata["raw_ref"]))
                    for section in d.metadata.get("sections", []):
                        if not 0 <= section["start"] < section["end"] <= len(d.text):
                            raise ValueError(f"Invalid section offsets: {d.doc_id}")
                    identity = (d.source, d.source_id, d.version)
                    if identity in identities and identities[identity] != (d.doc_id, d.hash):
                        raise ValueError(f"Conflicting source/version: {d.doc_id}")
                    identities[identity] = (d.doc_id, d.hash)
                    if d.doc_id in documents and documents[d.doc_id].model_dump() != d.model_dump():
                        raise ValueError(f"Conflicting document ID: {d.doc_id}")
                    documents[d.doc_id] = d
                    families[family].append(d.doc_id)
        if len(documents) != collection["total_unique_documents"]:
            raise ValueError("Unique document count mismatch")
        if len(reviews) != len({r["doc_id"] for r in reviews}) or set(documents) != {r["doc_id"] for r in reviews}:
            raise ValueError("Review rows must map to unique corpus documents")
    return CandidateCorpus(bundle_hash, collection, list(documents.values()), reviews, families, len(hashes), ingredient_relations)


def spl_ingredient_relations(raw):
    """Only explicit active ingredient/active moiety relationships from SPL XML.

    Not all source fixtures are XML. No abbreviation, brand or formulation
    inference is permitted. Combination products are not used for aliases.
    """
    ns = {"h": "urn:hl7-org:v3"}
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    rows = []
    for ingredient in root.findall(".//h:ingredient", ns):
        if ingredient.get("classCode") not in {"ACTIB", "ACTIM", "ACTIR"}:
            continue
        substance = ingredient.find("h:ingredientSubstance", ns)
        if substance is None:
            continue
        name = substance.findtext("h:name", namespaces=ns)
        moiety = substance.findtext("h:activeMoiety/h:activeMoiety/h:name", namespaces=ns)
        if not name or not moiety:
            return []  # do not infer missing active moieties
        rows.append({"ingredient": name.strip(), "active_moiety": moiety.strip()})
    if len({r["active_moiety"].casefold() for r in rows}) != 1:
        return []
    return list({(r["ingredient"], r["active_moiety"]): r for r in rows}.values())


def corpus_dictionary(corpus):
    """Literal names and SPL-attested active moieties; no brand guessing."""
    result = {"version": "mvp-candidates-2026-10-02.1", "mode": "verified",
              "description": "Literal term mapping attested in frozen corpus, not clinical gold or ontology mapping.",
              "corpus_sha256": corpus.bundle_hash, "drugs": [], "events": []}
    for pair in corpus.collection["pairs"]:
        docs = corpus.documents_for(pair["drug"])
        for section, term in (("drugs", pair["drug"]), ("events", pair["event"].casefold())):
            pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.I)
            d = next((d for d in docs if pattern.search(d.text)), None)
            if d is None:
                raise ValueError(f"No source attestation for {term}")
            start, end = pattern.search(d.text).span()
            # Only the spelling diarrhea/diarrhoea is equated, with both attested.
            aliases = []
            relationships = []
            if section == "drugs":
                for doc in docs:
                    for relation in corpus.ingredient_relations.get(doc.doc_id, []):
                        alias = relation["ingredient"].casefold()
                        if relation["active_moiety"].casefold() == term and alias != term:
                            aliases.append(alias)
                            relationships.append({**relation, "doc_id": doc.doc_id, "source_ref": doc.source_url,
                                "raw_ref": doc.metadata["raw_ref"], "raw_hash": doc.metadata["raw_hash"],
                                "verification": "SPL active ingredientSubstance/activeMoiety relationship"})
            if term == "diarrhoea" and any("diarrhea" in doc.text.casefold() for doc in docs):
                aliases = ["diarrhea"]
            aliases = sorted(set(aliases))
            alias_attestations = []
            for alias in aliases:
                pattern_alias = re.compile(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", re.I)
                source = next((doc for doc in docs if pattern_alias.search(doc.text)), None)
                if source is None:
                    continue  # relationship provenance remains in SPL metadata
                a, b = pattern_alias.search(source.text).span()
                alias_attestations.append({"alias": alias, "doc_id": source.doc_id, "source_ref": source.source_url,
                    "source_hash": source.hash, "quote": source.text[a:b], "start": a, "end": b})
            result[section].append({"canonical": term, "aliases": aliases, "source_ref": d.source_url,
                "license": "Team-authored short term mapping; source text remains in the locally supplied bundle.",
                "source_doc_id": d.doc_id, "source_hash": d.hash,
                "attestation": {"quote": d.text[start:end], "start": start, "end": end},
                "alias_attestations": alias_attestations, "ingredient_relationships": relationships})
    return result
