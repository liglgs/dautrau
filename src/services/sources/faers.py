import hashlib
import json
import re

import httpx

from src.models.schemas import SourceDocument
from src.services.sources.base import SourceAdapter
from src.services.sources.parser import PARSER_VERSION
from src.services.sources.transport import SourceError

BASE = "https://api.fda.gov/drug/event.json"


def query_literal(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class FAERSAdapter(SourceAdapter):
    name = "faers"

    def fetch(self, action, meter):
        if not self.drug or not self.event:
            raise SourceError("invalid_query: drug and event required")
        drug = query_literal(self.drug)
        search = (
            f"(patient.drug.openfda.generic_name:{drug} OR patient.drug.medicinalproduct:{drug}) AND "
            f"patient.reaction.reactionmeddrapt:{query_literal(self.event)}"
        )
        raw = self.get(BASE, {"search": search, "limit": self.max_documents}, meter)
        payload = self.json(raw)
        if "error" in payload:
            raise SourceError("unavailable: openFDA error")
        results = []
        seen = set()
        for report in payload["results"][: self.max_documents]:
            report_id = str(report["safetyreportid"])
            version = int(report.get("safetyreportversion", "1"))
            if (report_id, version) in seen:
                continue
            seen.add((report_id, version))
            patient = report.get("patient") or {}
            matches = []
            for item in patient.get("drug") or []:
                names = [item.get("medicinalproduct"), *((item.get("openfda") or {}).get("generic_name") or [])]
                if any(
                    isinstance(name, str)
                    and re.search(r"(?<!\w)" + re.escape(self.drug.casefold()) + r"(?!\w)", name.casefold())
                    for name in names
                ):
                    matches.append(
                        {
                            "medicinalproduct": item.get("medicinalproduct"),
                            "drugadministrationroute": item.get("drugadministrationroute"),
                            "drugdosagetext": item.get("drugdosagetext"),
                            "drugcharacterization": item.get("drugcharacterization"),
                        }
                    )
            text = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if len(text) > 200_000:
                raise SourceError("parse_error: report too large")
            digest = hashlib.sha256(text.encode()).hexdigest()
            metadata = {
                "parser_version": PARSER_VERSION,
                "content_level": "spontaneous_report",
                "raw_hash": hashlib.sha256(raw).hexdigest(),
                "parsed_hash": digest,
                "matched_drugs": matches,
                "age": patient.get("patientonsetage"),
                "reactions": [r.get("reactionmeddrapt") for r in patient.get("reaction") or []],
                "total_hits": payload.get("meta", {}).get("results", {}).get("total"),
                "warnings": ["report_level_not_causal_pair", "counts_not_incidence", "latest_observed_report_version"],
            }
            results.append(
                self.snapshot(
                    SourceDocument(
                        doc_id=f"faers:{report_id}:{version}",
                        source="faers",
                        source_id=report_id,
                        version=version,
                        title=f"FAERS report {report_id}",
                        source_url=str(
                            httpx.URL(BASE, params={"search": f"safetyreportid:{query_literal(report_id)}"})
                        ),
                        text=text,
                        hash=digest,
                        metadata=metadata,
                    ),
                    raw,
                )
            )
        return results
