"""Split a paragraph into dialogue, interior thought and narration.

* quoted text is dialogue (italic inside a quotation is emphasis, so it
  stays dialogue);
* italic text outside quotation marks is interior thought;
* everything else is narration.

The quotation style is detected once per document.  With double quotes
(“…” or "…") single quotes are nested quotations.  With British single
quotes (‘…’) a closing ’ is told from an apostrophe by what precedes it:
dialogue normally closes after punctuation (‘Go now,’ she said), and an
unclosed quotation closes at the end of its paragraph.
"""
from __future__ import annotations

import re

NARRATION, DIALOGUE, INTERIOR = "narration", "dialogue", "interior"
STREAMS = (NARRATION, DIALOGUE, INTERIOR)

_SPEECH_TAG = re.compile(
    r"\s+(said|says|asked|asks|replied|cried|called|whispered|shouted|muttered|"
    r"answered|went on|added|he|she|they|i|we|you|it)\b", re.I)
_CLOSE_PUNCT = set(",.!?;:…—–-")
_OPEN_CTX = set(" \t\n([{—–-“\"")


def detect_style(texts: list[str]) -> str:
    joined = "\n".join(texts)
    doubles = joined.count("“") + joined.count('"') // 2
    singles = len(re.findall(r"(?:^|[\s(—–-])‘", joined, re.M))
    singles += len(re.findall(r"(?:^|[\s(—–-])'(?=[A-Za-z])(?!(?:tis|twas|twere|twill|em|gainst|tween|twixt|neath|til)\b)",
                              joined, re.M | re.I))
    return "single" if singles > doubles else "double"


def dialogue_spans(text: str, style: str) -> list[tuple[int, int]]:
    spans = []
    i, n = 0, len(text)
    start = None
    while i < n:
        c = text[i]
        prev = text[i - 1] if i else " "
        nxt = text[i + 1] if i + 1 < n else " "
        if style == "double":
            if c == "“" and start is None:
                start = i
            elif c == "”" and start is not None:
                spans.append((start, i + 1))
                start = None
            elif c == '"':
                if start is None and (prev in _OPEN_CTX or i == 0):
                    start = i
                elif start is not None:
                    spans.append((start, i + 1))
                    start = None
        else:
            if start is None:
                if c == "‘" or (c == "'" and (prev in _OPEN_CTX or i == 0) and nxt.isalpha()
                                     and not re.match(r"'(tis|twas|twere|twill|em|gainst|tween|twixt|neath|til)\b",
                                                      text[i:], re.I)):
                    start = i
                elif c == "“":
                    start = i
            else:
                if c in "’'" and not nxt.isalpha():
                    rest = text[i + 1:]
                    if prev in _CLOSE_PUNCT or not rest.strip() or _SPEECH_TAG.match(rest):
                        spans.append((start, i + 1))
                        start = None
                elif c == "”":
                    pass
        i += 1
    if start is not None:
        spans.append((start, n))
    return spans


def label(text: str, italic: list[tuple[int, int]], style: str) -> list[str]:
    """Per-character stream labels."""
    lab = [NARRATION] * len(text)
    for a, b in italic:
        for k in range(a, min(b, len(text))):
            lab[k] = INTERIOR
    for a, b in dialogue_spans(text, style):
        for k in range(a, min(b, len(text))):
            lab[k] = DIALOGUE
    return lab
