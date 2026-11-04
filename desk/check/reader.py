"""Read a scene (.md, .txt, .docx) into paragraphs with italic spans.

Italic marks interior thought, so it is kept: *x* or _x_ in Markdown and
plain text, italic runs (direct or by character style) in Word files.  Bold
markers are dropped.  Headings are read as narration; scene-break lines
(*, -, _ or # repeated) and <!-- notes --> are skipped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_BREAK = re.compile(r"^\s*([*\-_#~]\s*){3,}$|^\s*#\s*$")


@dataclass
class Paragraph:
    text: str
    italic: list = field(default_factory=list)   # [(start, end)]
    heading: bool = False


def _inline(s: str) -> Paragraph:
    out = []
    italic = []
    start = None
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            out.append(s[i + 1])
            i += 2
            continue
        if s.startswith("**", i) or s.startswith("__", i):
            i += 2
            continue
        if c in "*_":
            prev = s[i - 1] if i else " "
            nxt = s[i + 1] if i + 1 < n else " "
            if c == "_" and prev.isalnum() and nxt.isalnum():
                out.append(c)           # snake_case, not emphasis
                i += 1
                continue
            pos = len("".join(out))
            if start is None and not nxt.isspace():
                start = pos
            elif start is not None:
                italic.append((start, pos))
                start = None
            else:
                out.append(c)
            i += 1
            continue
        out.append(c)
        i += 1
    text = "".join(out)
    if start is not None:
        italic.append((start, len(text)))
    return Paragraph(text=text, italic=italic)


_COMMENT = re.compile(r"<!--.*?-->", re.S)


def read_markdown(src: str) -> list[Paragraph]:
    """Paragraphs are separated by blank lines; <!-- notes --> are skipped."""
    src = _COMMENT.sub("", src)
    paras: list[Paragraph] = []
    block: list[str] = []

    def flush():
        if block:
            raw = " ".join(x.strip() for x in block).strip()
            heading = False
            m = re.match(r"^#{1,6}\s+(.*)$", raw)
            if m:
                raw, heading = m.group(1), True
            raw = re.sub(r"^>\s?", "", raw)
            if raw:
                p = _inline(raw)
                p.heading = heading
                paras.append(p)
            block.clear()

    for line in src.splitlines():
        if not line.strip():
            flush()
            continue
        if _BREAK.match(line):
            flush()
            continue
        if line.lstrip().startswith("#"):
            flush()
            block.append(line)
            flush()
            continue
        block.append(line)
    flush()
    return paras


def read_docx(path: Path) -> list[Paragraph]:
    import docx  # python-docx

    d = docx.Document(str(path))
    paras = []
    for p in d.paragraphs:
        text_parts, italic = [], []
        pos = 0
        style_italic = bool(p.style is not None and p.style.font is not None and p.style.font.italic)
        for run in p.runs:
            t = run.text
            if not t:
                continue
            it = run.font.italic
            if it is None and run.style is not None and run.style.font is not None:
                it = run.style.font.italic
            if it is None:
                it = style_italic
            if it:
                if italic and italic[-1][1] == pos:
                    italic[-1] = (italic[-1][0], pos + len(t))
                else:
                    italic.append((pos, pos + len(t)))
            text_parts.append(t)
            pos += len(t)
        text = "".join(text_parts)
        if not text.strip() or _BREAK.match(text):
            continue
        heading = bool(p.style is not None and p.style.name.lower().startswith(("heading", "title")))
        paras.append(Paragraph(text=text, italic=italic, heading=heading))
    return paras


def read(path: Path) -> list[Paragraph]:
    path = Path(path)
    suf = path.suffix.lower()
    if suf == ".docx":
        return read_docx(path)
    if suf in (".md", ".markdown", ".txt", ".text"):
        src = path.read_text(encoding="utf-8")
        lines = src.splitlines()
        nonblank = sum(1 for x in lines if x.strip())
        blank = len(lines) - nonblank
        if suf in (".txt", ".text") and nonblank > 3 and blank < 0.1 * nonblank:
            # one paragraph per line (a word-processor export without blank lines)
            src = "\n\n".join(lines)
        return read_markdown(src)
    raise ValueError(f"unsupported file type {suf}: use .md, .txt or .docx")
