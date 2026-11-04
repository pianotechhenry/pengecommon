"""Index keys shared by the build and the checker.

Both sides must reduce a word to exactly the same key, or a modern spelling in
Henry's text will miss its period attestation.  Keys are built from EarlyPrint's
regularised spelling (``@reg``, else the token text), so the corpus side has
already done the hard part: ``vnto`` -> ``unto``, ``loue`` -> ``love``.  What
is left here is mechanical: Unicode form, apostrophes, long s, case.
"""
from __future__ import annotations

import re
import unicodedata

import xxhash

APOSTROPHES = "’‘ʼʻ´`′"
_APOS_RE = re.compile("[" + APOSTROPHES + "]")
_EDGE_PUNCT = re.compile(r"^[^\w']+|[^\w']+$", re.UNICODE)


def form_key(s: str) -> str:
    """Lower-cased, NFC, straight apostrophes, long s folded."""
    s = unicodedata.normalize("NFC", s)
    s = _APOS_RE.sub("'", s)
    s = s.replace("ſ", "s").replace("­", "")
    s = _EDGE_PUNCT.sub("", s)
    return s.lower()


def fold_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


# ---------------------------------------------------------------------------
# n-gram hashing.  Each word key is hashed with xxh64; bigrams and trigrams
# are combined arithmetically mod 2**64 so that numpy (corpus side) and plain
# Python ints (query side) give identical results.
M64 = (1 << 64) - 1
P1 = 0x9E3779B97F4A7C15
P2 = 0xC2B2AE3D27D4EB4F
P3 = 0x165667B19E3779F9
P4 = 0xD6E8FEB86659FD93


def word_hash(key: str) -> int:
    return xxhash.xxh64_intdigest(key.encode("utf-8"))


def _mix(x: int) -> int:
    x ^= x >> 31
    x = (x * P3) & M64
    x ^= x >> 29
    return x


def bigram_hash(k1: str, k2: str) -> int:
    h = (word_hash(k1) * P1 + word_hash(k2) * P2 + 1) & M64
    return _mix(h)


def trigram_hash(k1: str, k2: str, k3: str) -> int:
    h = (word_hash(k1) * P1 + word_hash(k2) * P2 + word_hash(k3) * P4 + 2) & M64
    return _mix(h)


def to_signed(u: int) -> int:
    """SQLite integers are signed 64-bit."""
    return u - (1 << 64) if u >= (1 << 63) else u


def ngram_hash(words: list[str]) -> int:
    if len(words) == 2:
        return bigram_hash(*words)
    if len(words) == 3:
        return trigram_hash(*words)
    raise ValueError("only bigrams and trigrams are indexed")
