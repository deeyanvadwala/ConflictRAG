import sys
from retrieve import search

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUERIES = [
    "How many crew members does DRA 5.0 plan for?",
    "How many crew in the Evolvable Mars Campaign surface mission?",
    "What is the surface stay duration?",
    "How many launches are needed for a Mars mission?",
    "What is the IMLEO of the crewed Mars transfer vehicle?",
    "nuclear thermal rocket engine thrust",
    "Mars Reference Mission Version 3.0 changes from Version 1.0",
    "radiation protection for the crew",
    "How much does a Mars mission cost?",
    "When did the Perseverance rover land on Mars?",
]

BOOK = "19980037039"

for q in QUERIES:
    hits = search(q, k=5)
    from_book = sum(1 for h in hits if h["meta"]["doc_id"] == BOOK)
    print(f"\nQ: {q}")
    print(f"   chunks from the 1997 book in top 5: {from_book}/5")
    for h in hits[:3]:
        m = h["meta"]
        print(f"   [{h['distance']:.3f}] {m['doc_id']} ({m['study']}, {m['year']}) p.{m['page_start']}-{m['page_end']}")
