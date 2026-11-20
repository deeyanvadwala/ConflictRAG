"""Check every eval question against the PDFs. Run from the repo root:

    python eval/verify_gold.py [eval/questions.jsonl]

For each gold passage: the quote must appear on that PDF page (raw PDF text) AND in that page of
data/clean (what the index sees). For unanswerable questions: none of `absent_terms` may appear
anywhere in data/clean. Exits non-zero on any failure, so nothing unverified gets in.
"""
import json, pathlib, re, sys
import pymupdf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TAGS = {"easy", "multi-step", "unanswerable", "conflicting", "false-conflict", "model-knows"}
SUBS = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
        " ": " ", "ﬁ": "fi", "ﬂ": "fl"}


def norm(s):
    for a, b in SUBS.items():
        s = s.replace(a, b)
    return " ".join(s.lower().split())


_raw, _clean = {}, {}


def raw_page(doc_id, page):
    if doc_id not in _raw:
        _raw[doc_id] = pymupdf.open(f"data/raw/{doc_id}.pdf")
    doc = _raw[doc_id]
    return norm(doc[page - 1].get_text("text")) if 1 <= page <= len(doc) else ""


def clean_pages(doc_id):
    if doc_id not in _clean:
        text = pathlib.Path(f"data/clean/{doc_id}.txt").read_text(encoding="utf-8")
        parts = re.split(r"\[\[PAGE (\d+)\]\]\r?\n", text)
        _clean[doc_id] = {int(parts[i]): norm(parts[i + 1]) for i in range(1, len(parts), 2)}
    return _clean[doc_id]


def corpus_text():
    return norm(" ".join(p.read_text(encoding="utf-8") for p in pathlib.Path("data/clean").glob("*.txt")))


def check(q, corpus):
    errs = []
    if q.get("tag") not in TAGS:
        errs.append(f"bad tag {q.get('tag')!r}")
    if q["tag"] in {"unanswerable", "model-knows"}:   # the corpus must not contain the answer
        if q.get("gold"):
            errs.append(f"{q['tag']} question has gold passages")
        terms = q.get("absent_terms") or []
        if not terms:
            errs.append(f"{q['tag']} question needs absent_terms")
        for t in terms:
            if norm(t) in corpus:
                errs.append(f"absent term {t!r} IS in the corpus")
    else:
        if not q.get("gold"):
            errs.append("no gold passages")
        if not q.get("answer"):
            errs.append("no reference answer")
        for g in q.get("gold", []):
            quote = norm(g["quote"])
            if len(quote) < 15:
                errs.append(f"quote too short to be unambiguous: {g['quote']!r}")
            if quote not in raw_page(g["doc_id"], g["page"]):
                errs.append(f"quote not on PDF page {g['doc_id']} p.{g['page']}: {g['quote']!r}")
            elif quote not in clean_pages(g["doc_id"]).get(g["page"], ""):
                errs.append(f"quote on PDF page but missing from data/clean (ingest dropped it): "
                            f"{g['doc_id']} p.{g['page']}")
    if q["tag"] in {"conflicting", "false-conflict"} and len({g["doc_id"] for g in q.get("gold", [])}) < 2:
        errs.append("conflict questions need gold from at least 2 documents")
    return errs


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "eval/questions.jsonl"
    qs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    corpus = corpus_text()
    ids = [q["id"] for q in qs]
    failed = 0
    if len(ids) != len(set(ids)):
        print("DUPLICATE ids"); failed += 1
    for q in qs:
        errs = check(q, corpus)
        if errs:
            failed += 1
            print(f"FAIL {q['id']} ({q['tag']}): {q['question']}")
            for e in errs:
                print(f"     - {e}")
    counts = {}
    for q in qs:
        counts[q["tag"]] = counts.get(q["tag"], 0) + 1
    print(f"\n{len(qs) - failed}/{len(qs)} questions verified. By tag: {counts}")
    sys.exit(1 if failed else 0)
