import csv, re, pathlib, collections
import pymupdf

RAW = pathlib.Path("data/raw")
CLEAN = pathlib.Path("data/clean")
CLEAN.mkdir(parents=True, exist_ok=True)


def norm(line):
    return re.sub(r"\d+", "#", line.lower()).strip()


def page_lines(page):
    lines = []
    for l in page.get_text("text").splitlines():  # no sort=True: keeps column order
        l = re.sub(r"[ \t\u00a0]+", " ", l).strip()
        if l:
            lines.append(l)
    return lines


def extract(doc_id):
    doc = pymupdf.open(RAW / f"{doc_id}.pdf")
    pages = [page_lines(p) for p in doc]

    repeated = set()
    if len(pages) >= 8:
        counts = collections.Counter()
        for lines in pages:
            counts.update({norm(l) for l in lines if len(l) < 80})
        repeated = {k for k, c in counts.items() if c >= 0.4 * len(pages)}

    out, empty = [], 0
    for n, lines in enumerate(pages, start=1):
        kept = [
            l for l in lines
            if not re.fullmatch(r"[\d\-\sivxIVX]{1,8}", l)   # bare page numbers
            and not re.fullmatch(r"[•·\-–—]", l)             # lone bullets
            and norm(l) not in repeated
        ]
        text = "\n".join(kept)
        if len(text) < 50:
            empty += 1
        out.append(f"[[PAGE {n}]]\n{text}\n")
    return "\n".join(out), len(pages), empty


with open("data/metadata.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print(f"{'doc_id':<13}{'pages':>6}{'chars':>9}{'near-empty':>12}  note")
for row in rows:
    doc_id = row["doc_id"]
    if not (RAW / f"{doc_id}.pdf").exists():
        print(f"{doc_id:<13} MISSING PDF")
        continue
    text, n_pages, empty = extract(doc_id)
    (CLEAN / f"{doc_id}.txt").write_text(text, encoding="utf-8")
    note = []
    if row["year"] == "TODO":
        note.append("year is TODO")
    if empty > 0.3 * n_pages:
        note.append("many empty pages: scanned or slide-heavy?")
    print(f"{doc_id:<13}{n_pages:>6}{len(text):>9}{empty:>12}  {'; '.join(note)}")