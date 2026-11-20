import sys
from retrieve import search

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (query, [(doc_id, pdf_page), ...]) -- pages come from your own find.py output.
# A hit means a retrieved chunk is from that document and its page range covers that page.
CASES = [
    ("How many crew members does DRA 5.0 plan for?",
     [("20090040343", 7)]),
    ("How many crew in the Evolvable Mars Campaign surface mission?",
     [("20140016934", 1), ("20140016934", 2)]),
    ("What is the IMLEO of the crewed Mars transfer vehicle?",
     [("20090040343", 15), ("20090010571", 36)]),
]

K = 20

for query, gold in CASES:
    hits = search(query, k=K)
    print(f"\nQ: {query}")
    for doc_id, page in gold:
        rank = None
        for i, h in enumerate(hits, start=1):
            m = h["meta"]
            if m["doc_id"] == doc_id and m["page_start"] <= page <= m["page_end"]:
                rank = i
                break
        where = f"rank {rank}" if rank else f"NOT in top {K}"
        print(f"   gold {doc_id} p.{page}: {where}")
