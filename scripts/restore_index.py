"""Restore a prebuilt index instead of building one (saves 3-6 hours).

The built index travels as zstd-compressed pieces under 100 MB, with SHA-256
checksums.  Put the pieces in one folder (for example by cloning just the
index branch), then:

    git clone --depth 1 --single-branch -b index-data \\
        https://github.com/pianotechhenry/pengecommon index-data
    python scripts/restore_index.py index-data

This writes data/index.sqlite and data/etymology.sqlite (or the folder in
DESK_DATA), checking every piece and the result.  `desk check` and `desk
lookup` then work at once.  The token streams are not included, so after
adding a multi-word phrase to the watch list it is looked up in the phrase
index (phrases printed in 5 or more texts) rather than exhaustively; a full
`desk build` restores the exhaustive scan.
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

import zstandard as zstd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from desk import paths  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Joined:
    """The pieces read in order as one file."""

    def __init__(self, parts: list[Path]):
        self.parts = parts
        self.i = 0
        self.f = open(parts[0], "rb")

    def read(self, n: int = -1) -> bytes:
        out = b""
        if self.i >= len(self.parts):
            return out
        while n < 0 or len(out) < n:
            chunk = self.f.read(-1 if n < 0 else n - len(out))
            if chunk:
                out += chunk
                continue
            self.f.close()
            self.i += 1
            if self.i >= len(self.parts):
                break
            self.f = open(self.parts[self.i], "rb")
        return out


def main(src: Path) -> int:
    sums = {}
    for line in (src / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(None, 1)
        sums[name.strip().lstrip("*")] = digest
    for name, digest in sums.items():
        got = sha256(src / name)
        if got != digest:
            print(f"{name}: checksum mismatch - download it again")
            return 1
    print(f"{len(sums)} pieces verified")
    out_dir = paths.data_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    dctx = zstd.ZstdDecompressor()
    parts = sorted(src.glob("index.sqlite.zst.part*"))
    targets = [(Joined(parts), out_dir / "index.sqlite"),
               (open(src / "etymology.sqlite.zst", "rb"), out_dir / "etymology.sqlite")]
    for stream, dest in targets:
        tmp = dest.with_suffix(".sqlite.tmp")
        with open(tmp, "wb") as fo:
            dctx.copy_stream(stream, fo)
        con = sqlite3.connect(tmp)
        ok = con.execute("PRAGMA quick_check").fetchone()[0]
        con.close()
        if ok != "ok":
            print(f"{dest.name}: database check failed ({ok})")
            return 1
        tmp.replace(dest)
        print(f"wrote {dest} ({dest.stat().st_size / 1e9:.2f} GB)")
    print("done - try: desk info")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "index-data")))
