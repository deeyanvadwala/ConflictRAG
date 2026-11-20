import sys
from retrieve import search

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (query, [(doc_id, pdf_page, quote), ...]). Every quote was verified in the PDF with find.py.
# Quote rule (the one we use): a hit is a retrieved chunk from that document whose text contains
# the quote (case and line breaks ignored). Page rule (old, shown for comparison): any chunk from
# that document whose page range covers the page.
CASES = [
    ("How many crew members does DRA 5.0 plan for?", [
        ("20090040343", 7, "envisions sending six crewmembers to Mars"),   # primary
        ("20160006315", 5, "a crew of six transfers to Mars"),             # secondary (2015 comparison)
    ]),
    ("How many crew in the Evolvable Mars Campaign surface mission?", [
        ("20140016934", 1, "at least 4 crew for up to 500 sols"),
    ]),
    ("What is the IMLEO of the crewed Mars transfer vehicle?", [
        ("20090040343", 15, "has an IMLEO of 356.4 t"),
        ("20090010571", 36, "IMLEO ~336.5 t"),
    ]),
]

K = 20


def norm(s):
    return " ".join(s.lower().split())


def contains(chunk_text, quote):
    return norm(quote) in norm(chunk_text)


def ranks(hits, doc_id, page, quote):
    by_page = by_quote = None
    for i, h in enumerate(hits, start=1):
        m = h["meta"]
        if m["doc_id"] != doc_id:
            continue
        if by_page is None and m["page_start"] <= page <= m["page_end"]:
            by_page = i
        if by_quote is None and contains(h["text"], quote):
            by_quote = i
    return by_page, by_quote


if __name__ == "__main__":
    fmt = lambda r: f"rank {r}" if r else f"not in top {K}"
    for query, gold in CASES:
        hits = search(query, k=K)
        print(f"\nQ: {query}")
        for doc_id, page, quote in gold:
            by_page, by_quote = ranks(hits, doc_id, page, quote)
            print(f"   {doc_id} p.{page} \"{quote}\"")
            print(f"      quote rule: {fmt(by_quote):<16} page rule: {fmt(by_page)}")
