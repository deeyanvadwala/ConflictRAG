"""Prompt-injection test: does a hostile passage in the context change the answer?

    python eval/injection_eval.py                 # current system (config.yaml), saves injection_<name>
    python eval/injection_eval.py --name x --prompt naive

For each attack in eval/injection/attacks.jsonl:
- exposure: the hostile passage is put among the real top-5 sources, once as source [1] and once as
  source [5] (replacing the 5th real source). Attack success = the answer matches the attack's
  success_regex (decided by code, no judge).
- reach: would the reranker place the hostile passage in the top 5 if it were in the candidate pool?
  (its rerank score is above the real 5th source's score). This does not test whether the passage
  would enter the pool; it is an upper bound on how easily retrieval lets it through.
"""
import argparse, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from chunking import CFG                     # noqa: E402
from generate import build_prompt, trusted   # noqa: E402
from run_eval import cached_complete         # noqa: E402
from strategies import STRATEGIES, _rerank   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent


def hostile_hit(a):
    return {"chunk_id": a["id"], "text": a["text"], "distance": 0.0,
            "meta": {"doc_id": a["doc_id"], "page_start": 1, "page_end": 1, "study": a["study"],
                     "year": a["year"], "source_url": ""}}


def run(attacks, retrieval, style, provenance=False, k=5):
    rows = []
    for a in attacks:
        print(a["id"], a["type"], file=sys.stderr)
        hits = STRATEGIES[retrieval](a["question"], k)
        bad = hostile_hit(a)
        _rerank(a["question"], [bad], 1)
        fifth = hits[-1].get("rerank")
        row = {"id": a["id"], "type": a["type"], "question_id": a["question_id"],
               "reach": (bad["rerank"] > fifth) if fifth is not None else None,
               "hostile_rerank": round(bad["rerank"], 3),
               "fifth_rerank": round(fifth, 3) if fifth is not None else None}
        for pos, ctx in (("first", [bad] + hits[:k - 1]), ("last", hits[:k - 1] + [bad])):
            if provenance:   # D2: drop passages from documents outside the hashed corpus manifest
                ctx, _ = trusted(ctx)
            out = cached_complete(build_prompt(a["question"], ctx, style))["output"]
            row[f"success_{pos}"] = bool(re.search(a["success_regex"], out, flags=re.I))
            row[f"answer_{pos}"] = out
        rows.append(row)
    return rows


def table(rows, title):
    n = len(rows)
    first = sum(r["success_first"] for r in rows)
    last = sum(r["success_last"] for r in rows)
    either = sum(r["success_first"] or r["success_last"] for r in rows)
    reach = sum(bool(r["reach"]) for r in rows)
    lines = [f"## {title}", "",
             f"Attack success: as source [1] {first}/{n}, as source [5] {last}/{n}, either {either}/{n}. "
             f"Reranker would admit the hostile passage to the top 5: {reach}/{n}.", "",
             "| Attack | Type | Question | Success as [1] | Success as [5] | Reaches top 5 |",
             "|---|---|---|---|---|---|"]
    yn = lambda x: "yes" if x else "no"
    for r in rows:
        lines.append(f"| {r['id']} | {r['type']} | {r['question_id']} | {yn(r['success_first'])} | "
                     f"{yn(r['success_last'])} | {yn(r['reach'])} ({r['hostile_rerank']} vs {r['fifth_rerank']}) |")
    return "\n".join(lines)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--name", default="final")
    p.add_argument("--retrieval", choices=sorted(STRATEGIES), default=CFG["retrieval"])
    p.add_argument("--prompt", default=CFG["prompt"])
    p.add_argument("--provenance", action="store_true", help="D2: apply the corpus-manifest check")
    a = p.parse_args()
    attacks = [json.loads(l) for l in open(ROOT / "injection" / "attacks.jsonl", encoding="utf-8") if l.strip()]
    rows = run(attacks, a.retrieval, a.prompt, a.provenance)
    provider = CFG["llm_provider"]
    title = (f"injection_{a.name} ({len(rows)} attacks; {provider} {CFG['llm_models'][provider]}, "
             f"retrieval {a.retrieval}, prompt {a.prompt}, provenance check {'on' if a.provenance else 'off'})")
    out = table(rows, title)
    print(out)
    res = ROOT / "results"
    (res / f"injection_{a.name}.json").write_text(json.dumps({"title": title, "rows": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    (res / f"injection_{a.name}.md").write_text(out + "\n", encoding="utf-8")
