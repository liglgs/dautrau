"""BM25 over evidence units; no labels or claim-ID shortcuts in ranking."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from eval.corpus import Corpus, Unit

TOKENIZER_VERSION = "nfkc-casefold-unicode-word-v1"


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold())


@dataclass(frozen=True)
class Hit:
    unit: Unit
    score: float


class BM25:
    def __init__(self, corpus: Corpus, *, k1: float = 1.2, b: float = 0.75):
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("Invalid BM25 configuration")
        self.corpus, self.k1, self.b = corpus, k1, b

    def search(self, query: str, *, k: int = 20, cutoff: str | None = None, source: str | None = None) -> list[Hit]:
        if k < 1:
            raise ValueError("k must be positive")
        # Statistics only use documents visible at cutoff; future content cannot affect IDF.
        units = self.corpus.visible(cutoff)
        terms = [Counter(tokenize(unit.title + " " + unit.text)) for unit in units]
        average = sum(sum(item.values()) for item in terms) / len(terms) if terms else 0
        frequencies = Counter(term for item in terms for term in item)
        query_terms = set(tokenize(query))
        hits = []
        for unit, counts in zip(units, terms, strict=True):
            if source and unit.source != source:
                continue
            score = 0.0
            length = sum(counts.values())
            for term in query_terms:
                tf = counts[term]
                if not tf:
                    continue
                df = frequencies[term]
                idf = math.log(1 + (len(units) - df + 0.5) / (df + 0.5))
                score += idf * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / (average or 1)))
            if score > 0:
                hits.append(Hit(unit, score))
        return sorted(hits, key=lambda hit: (-hit.score, hit.unit.unit_id))[:k]
