import sys
from retrieve import _load, search

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# usage: python diagnose.py "<query>" "<phrase that appears in the answer>"
query, phrase = sys.argv[1], sys.argv[2]

model, col = _load()
total = col.count()
everything = col.get(include=["documents", "metadatas"], limit=total)

# Rank every chunk in the index for this query
ranked = search(query, k=total)
rank = {h["chunk_id"]: (i + 1, h["distance"]) for i, h in enumerate(ranked)}

found = 0
for cid, doc, meta in zip(everything["ids"], everything["documents"], everything["metadatas"]):
    flat = " ".join(doc.split())  # ignore line breaks when matching the phrase
    pos = flat.lower().find(phrase.lower())
    if pos == -1:
        continue
    found += 1
    r, d = rank[cid]
    print(f"\n{cid} | {meta['doc_id']} p.{meta['page_start']}-{meta['page_end']} | "
          f"rank {r} of {total} | distance {d:.3f} | {len(doc)} chars")
    print("   ..." + flat[max(0, pos - 200): pos + 250] + "...")

if found == 0:
    print(f"\nNo chunk contains '{phrase}'. Try a shorter phrase.")
