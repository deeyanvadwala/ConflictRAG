import pymupdf, sys, re

# usage: python find.py <doc_id> <search term>
doc_id, term = sys.argv[1], sys.argv[2]
doc = pymupdf.open(f"data/raw/{doc_id}.pdf")

for n, page in enumerate(doc, start=1):
    text = page.get_text().replace("\n", " ")
    for m in re.finditer(term, text, flags=re.IGNORECASE):
        start = max(0, m.start() - 100)
        print(f"[pdf page {n}] ...{text[start:m.end()+100]}...")