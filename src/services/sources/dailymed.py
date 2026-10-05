from urllib.parse import quote

from src.services.sources.base import SourceAdapter
from src.services.sources.parser import document, safe_xml, text_of
from src.services.sources.transport import SourceError

BASE = "https://dailymed.nlm.nih.gov/dailymed/services/v2/"
NS = {"s": "urn:hl7-org:v3"}


class DailyMedAdapter(SourceAdapter):
    name = "dailymed"

    def fetch(self, action, meter):
        if not self.drug:
            raise SourceError("invalid_query: drug required")
        raw = self.get(BASE + "spls.json", {"drug_name": self.drug, "pagesize": self.max_documents}, meter)
        candidates = self.json(raw)["data"][: self.max_documents]
        results = []
        seen = set()
        for candidate in candidates:
            setid = candidate["setid"]
            if not isinstance(setid, str) or len(setid) > 100:
                raise SourceError("parse_error: invalid SETID")
            if setid in seen:
                continue
            seen.add(setid)
            raw = self.get(BASE + f"spls/{quote(setid, safe='')}.xml", {}, meter)
            root = safe_xml(raw)
            actual_id = root.find("s:setId", NS)
            version = root.find("s:versionNumber", NS)
            if actual_id is None or actual_id.get("root") != setid or version is None:
                raise SourceError("parse_error: label identity/version missing")
            sections = [
                (text_of(section.find("s:title", NS)) or "Section", text_of(section.find("s:text", NS)))
                for section in root.findall(".//s:section", NS)
            ]
            metadata = {
                "content_level": "label_sections",
                "routes": list(
                    dict.fromkeys(n.get("displayName") or n.get("code") for n in root.findall(".//s:routeCode", NS))
                ),
                "ingredients": [text_of(n) for n in root.findall(".//s:activeIngredientSubstance/s:name", NS)],
                "effective_time": root.find("s:effectiveTime", NS).get("value")
                if root.find("s:effectiveTime", NS) is not None
                else None,
                "warnings": ["current_label_only", "candidate_label_not_verified_product_match"],
            }
            if not any(body for _, body in sections):
                metadata["warnings"].append("missing_sections")
            results.append(
                self.snapshot(
                    document(
                        self.name,
                        setid,
                        int(version.get("value")),
                        text_of(root.find("s:title", NS)) or candidate.get("title", setid),
                        f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={quote(setid)}",
                        raw,
                        sections,
                        metadata,
                    ),
                    raw,
                )
            )
        return results
