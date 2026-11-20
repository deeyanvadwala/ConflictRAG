"""Corpus freeze: record or verify the SHA-256 of every PDF listed in data/metadata.csv.

    python manifest.py           # verify data/raw against data/corpus_manifest.csv
    python manifest.py --write   # (re)write the manifest; only when the corpus is deliberately changed
"""
import csv, hashlib, pathlib, sys

import pymupdf

MANIFEST = pathlib.Path("data/corpus_manifest.csv")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


rows = list(csv.DictReader(open("data/metadata.csv", newline="", encoding="utf-8")))
current = []
for r in rows:
    p = pathlib.Path(f"data/raw/{r['doc_id']}.pdf")
    if not p.exists():
        sys.exit(f"MISSING {p}: run python download.py")
    current.append({"doc_id": r["doc_id"], "sha256": sha256(p), "bytes": p.stat().st_size,
                    "pdf_pages": len(pymupdf.open(p)), "pages_used": r.get("pages") or "all"})

if sys.argv[1:] == ["--write"]:
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(current[0]))
        w.writeheader()
        w.writerows(current)
    print(f"wrote {MANIFEST} ({len(current)} documents)")
else:
    frozen = {r["doc_id"]: r for r in csv.DictReader(open(MANIFEST, encoding="utf-8"))}
    bad = [c["doc_id"] for c in current if frozen.get(c["doc_id"], {}).get("sha256") != c["sha256"]]
    extra = set(frozen) - {c["doc_id"] for c in current}
    if bad or extra:
        sys.exit(f"CORPUS MISMATCH: changed or new {bad}, missing from metadata {sorted(extra)}")
    print(f"corpus OK: {len(current)} documents match {MANIFEST}")
