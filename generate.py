"""Baseline RAG: retrieve top-k chunks, ask the LLM to answer with [n] citations.

The prompt is naive ON PURPOSE (no abstention rule, no year or conflict handling,
no injection defenses) so later improvements can be measured against it.

usage:
    python generate.py "How many crew members does DRA 5.0 plan for?"
    python generate.py "..." --k 8 --provider ollama
    python generate.py "..." --dry-run      # print the prompt, do not call the LLM
"""
import argparse
import re
import sys
import time

from chunking import CFG
from retrieve import search

PROMPT = """Answer the question using the context below. Cite the sources you use with their numbers in square brackets, like [1].

Context:
{context}

Question: {question}

Answer:"""


def build_prompt(question, hits):
    blocks = []
    for n, h in enumerate(hits, start=1):
        m = h["meta"]
        blocks.append(f"[{n}] (document {m['doc_id']}, pages {m['page_start']}-{m['page_end']})\n{h['text']}")
    return PROMPT.format(context="\n\n".join(blocks), question=question)


def cited_numbers(answer):
    """All source numbers the answer cites, e.g. '[1]', '[2, 3]' or '[1][4]'."""
    nums = set()
    for group in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", answer):
        nums.update(int(x) for x in group.split(","))
    return sorted(nums)


def answer(question, k=None, provider=None, dry_run=False):
    """Returns a dict with the answer, the retrieved hits, citations and timings."""
    from llm import complete  # imported here so --dry-run works without LLM settings

    k = k or CFG["top_k"]
    t0 = time.perf_counter()
    hits = search(question, k=k)
    t1 = time.perf_counter()
    prompt = build_prompt(question, hits)
    if dry_run:
        return {"question": question, "prompt": prompt, "hits": hits, "retrieval_s": t1 - t0}
    text = complete(prompt, provider=provider)
    t2 = time.perf_counter()
    cited = cited_numbers(text)
    return {
        "question": question,
        "answer": text,
        "hits": hits,
        "cited": [n for n in cited if 1 <= n <= len(hits)],
        "invalid_citations": [n for n in cited if not 1 <= n <= len(hits)],
        "retrieval_s": t1 - t0,
        "llm_s": t2 - t1,
    }


def show(r):
    print(f"Q: {r['question']}\n")
    if "prompt" in r:
        print(r["prompt"])
        return
    print(r["answer"].strip(), "\n")
    print("Sources:")
    for n, h in enumerate(r["hits"], start=1):
        m = h["meta"]
        mark = "cited " if n in r["cited"] else "unused"
        print(f"  [{n}] {mark} {m['doc_id']} ({m['study']}, {m['year']}) "
              f"p.{m['page_start']}-{m['page_end']}  dist {h['distance']:.3f}  {m['source_url']}")
    if r["invalid_citations"]:
        print(f"  WARNING: cites sources that do not exist: {r['invalid_citations']}")
    if not r["cited"]:
        print("  WARNING: the answer cites no sources")
    print(f"\nTime: retrieval {r['retrieval_s']:.2f}s, LLM {r['llm_s']:.2f}s")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--k", type=int, default=None)
    p.add_argument("--provider", choices=["gemini", "ollama", "anthropic"], default=None)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    show(answer(a.question, k=a.k, provider=a.provider, dry_run=a.dry_run))
