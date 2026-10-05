"""Offline lexical quotation suggestions from real text, not clinical extraction."""

import json
import re

from src.services.llm import LLMResponse
from src.services.prompts import UNTRUSTED_CLOSE


class CandidateQuoteProvider:
    """No network, no stance/scope inference, no gold answers.

    This provider exercises the full extraction contract with source quotations.
    Its results are deliberately uncertain and require specialist annotation.
    Usage counts are simulated gateway accounting, not measured LLM tokens.
    """

    name = "offline-lexical-candidates"

    def __init__(self, dictionary):
        self.dictionary = dictionary

    def complete(self, *, task, system, prompt, json_schema=None, untrusted=""):
        if task != "extract_evidence":
            raise ValueError("Offline candidate provider supports extraction only")
        claim = json.loads(prompt.split("\n", 1)[1].split("\n\nDocument identity:", 1)[0])
        source = json.loads(prompt.split("Document identity:\n", 1)[1].split("\n\nReturn", 1)[0])["source"]
        # The gateway supplies one untrusted window: opening marker, header,
        # then source text. Never interpret embedded source text as instructions.
        text = untrusted.split("\n", 2)[2].rsplit("\n" + UNTRUSTED_CLOSE, 1)[0]
        terms = {claim["event_term"]}
        for row in self.dictionary["events"]:
            if row["canonical"] == claim["event_term"]:
                terms.update(row["aliases"])
        pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(t) for t in sorted(terms)) + r")(?!\w)", re.I)
        findings = []
        last_end = -1
        for match in pattern.finditer(text):
            if match.start() < last_end:
                continue
            start, end = max(0, match.start() - 350), min(len(text), match.end() + 350)
            quote = text[start:end]
            drug = claim["drug_ingredient"] if re.search(r"(?<!\w)" + re.escape(claim["drug_ingredient"]) + r"(?!\w)", quote, re.I) else None
            findings.append({"quote": quote, "locator": {"start": start, "end": end},
                "drug_ingredient": drug, "event_term": claim["event_term"], "scope": {},
                "stance": "uncertain", "direction": "unknown", "uncertainty": "unknown",
                "evidence_type": "faers_report" if source == "faers" else "label" if source == "dailymed" else "other"})
            last_end = end
            if len(findings) == 3:
                break
        body = json.dumps({"findings": findings}, ensure_ascii=False)
        return LLMResponse(text=body, input_tokens=max(1, (len(prompt) + len(untrusted)) // 4),
                           output_tokens=max(1, len(body) // 4), model=self.name)
