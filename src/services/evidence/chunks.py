"""Bounded document windows with offsets into the immutable source text."""

import re
from dataclasses import dataclass

WINDOW_CHARS = 10000
OVERLAP_CHARS = 2000  # preserve quotes of up to 2000 characters at boundaries


@dataclass(frozen=True)
class DocumentWindow:
    start: int
    end: int
    text: str


def document_windows(document, claim, dictionary=None, *, max_windows=3):
    """Select lexical relevance windows, never claim that selection is exhaustive.

    Matching terms select context only; they do not establish stance or scope.
    Short documents use their full text. Long documents retain an opening window
    plus the most relevant windows; callers record any unexamined coverage.
    """
    if max_windows < 1:
        raise ValueError("max_windows must be positive")
    text = document.text
    windows = []
    for start in range(0, len(text), WINDOW_CHARS - OVERLAP_CHARS):
        end = min(start + WINDOW_CHARS, len(text))
        windows.append(DocumentWindow(start, end, text[start:end]))
        if end == len(text):
            break
    if len(windows) <= max_windows:
        return windows
    terms = {claim.event_term}
    for record in (dictionary or {}).get("events", []):
        if record["canonical"] == claim.event_term:
            terms.update(record["aliases"])
    patterns = [re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.I) for term in terms if term]
    ranked = sorted(windows[1:], key=lambda w: (-sum(len(p.findall(w.text)) for p in patterns), w.start))
    return sorted([windows[0], *ranked[:max_windows - 1]], key=lambda w: w.start)


def coverage_summary(windows, text_length):
    end = covered = 0
    for w in sorted(windows, key=lambda w: w.start):
        covered += max(0, w.end - max(end, w.start))
        end = max(end, w.end)
    return {"ranges": [[w.start, w.end] for w in windows], "examined_chars": covered,
            "total_chars": text_length, "complete": covered == text_length}
