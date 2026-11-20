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


def page_range(spec, n_pages):
    """'25-90' -> PDF page numbers 25..90; blank -> every page."""
    if not spec:
        return list(range(1, n_pages + 1))
    a, b = (int(x) for x in spec.split("-"))
    return list(range(a, min(b, n_pages) + 1))


def extract(doc_id, spec=""):
    doc = pymupdf.open(RAW / f"{doc_id}.pdf")
    numbers = page_range(spec, len(doc))          # original PDF page numbers, kept for citations
    pages = [page_lines(doc[n - 1]) for n in numbers]

    repeated = set()
    if len(pages) >= 8:
        counts = collections.Counter()
        for lines in pages:
            # Only lines with a letter: norm() turns every bare number into "#",
            # which would otherwise mark all table numbers as a repeated header.
            counts.update({norm(l) for l in lines if len(l) < 80 and re.search(r"[A-Za-z]", l)})
        repeated = {k for k, c in counts.items() if c >= 0.4 * len(pages)}

    out, empty = [], 0
    for n, lines in zip(numbers, pages):
        edge = {0, 1, len(lines) - 2, len(lines) - 1}  # first/last 2 lines: where page numbers sit
        kept = [
            l for i, l in enumerate(lines)
            # bare page numbers, only at the page edges: mid-page bare numbers are
            # table values (e.g. the crew-size row of 20160006315 Table 1, PDF page 11)
            if not (i in edge and re.fullmatch(r"[\d\-\sivxIVX]{1,8}", l))
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
    text, n_pages, empty = extract(doc_id, row.get("pages", ""))
    (CLEAN / f"{doc_id}.txt").write_text(text, encoding="utf-8")
    note = []
    if row["year"] == "TODO":
        note.append("year is TODO")
    if empty > 0.3 * n_pages:
        note.append("many empty pages: scanned or slide-heavy?")
    print(f"{doc_id:<13}{n_pages:>6}{len(text):>9}{empty:>12}  {'; '.join(note)}")