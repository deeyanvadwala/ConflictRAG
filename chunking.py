import csv, re, bisect, pathlib
import yaml

CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))
CLEAN = pathlib.Path("data/clean")


def split_pages(text):
    """Split a cleaned file into (page_number, page_text) pairs."""
    parts = re.split(r"\[\[PAGE (\d+)\]\]\r?\n", text)
    return [(int(parts[i]), parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def windows(text, size, overlap):
    """Yield (start, end) character windows, preferring to cut at a line break."""
    i, n = 0, len(text)
    while i < n:
        end = min(i + size, n)
        if end < n:
            nl = text.rfind("\n", i + size // 2, end)
            if nl != -1:
                end = nl
        yield i, end
        if end >= n:
            break
        i = max(end - overlap, i + 1)


def load_chunks():
    with open("data/metadata.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    chunks = []
    for row in rows:
        path = CLEAN / f"{row['doc_id']}.txt"
        pages = split_pages(path.read_text(encoding="utf-8"))

        # Join pages into one string, remembering where each page starts
        text, starts = "", []
        for page_no, ptxt in pages:
            starts.append((len(text), page_no))
            text += ptxt + "\n"
        offsets = [s[0] for s in starts]

        def page_at(pos):
            return starts[bisect.bisect_right(offsets, pos) - 1][1]

        k = 0
        for a, b in windows(text, CFG["chunk_chars"], CFG["chunk_overlap"]):
            body = text[a:b].strip()
            if len(body) < CFG["min_chunk_chars"]:
                continue
            chunks.append({
                "chunk_id": f"{row['doc_id']}_{k:04d}",
                "text": body,
                "meta": {
                    "doc_id": row["doc_id"],
                    "title": row["title"],
                    "year": int(row["year"]),
                    "study": row["study"],
                    "doc_type": row["doc_type"],
                    "source_url": row["source_url"],
                    "page_start": page_at(a),
                    "page_end": page_at(max(a, b - 1)),
                },
            })
            k += 1
    return chunks
