"""Retrieval-only comparison (no LLM): hit rate, MRR and conflict coverage per strategy.

    python eval/retrieval_eval.py --split dev

hit@n: answerable questions where some retrieved chunk contains a gold quote.
coverage@n: conflicting + false-conflict questions where chunks containing gold quotes from
EVERY gold document are retrieved (both sides reach the generator).
"""
import argparse, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from strategies import STRATEGIES   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
NO_ANSWER = {"unanswerable", "model-knows"}


sys.path.insert(0, str(ROOT))
from verify_gold import norm   # noqa: E402  same text matching as the gold verifier


def has(h, g):
    return h["meta"]["doc_id"] == g["doc_id"] and norm(g["quote"]) in norm(h["text"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=["dev", "test"], default="dev")
    p.add_argument("--n", type=int, nargs="+", default=[4, 8])
    p.add_argument("--only", nargs="+", help="run only these strategies")
    a = p.parse_args()
    qs = [json.loads(l) for l in open(ROOT / "questions.jsonl", encoding="utf-8") if l.strip()]
    qs = [q for q in qs if q["split"] == a.split and q["tag"] not in NO_ANSWER]
    conf = [q for q in qs if q["tag"] in {"conflicting", "false-conflict"}]

    print(f"{a.split}: {len(qs)} answerable questions, {len(conf)} conflict/trap questions\n")
    print("| Strategy | n | hit@n | MRR@n | coverage@n | covered ids |\n|---|---|---|---|---|---|")
    for n in a.n:
        for name, fn in STRATEGIES.items():
            if a.only and name not in a.only:
                continue
            hit, rr, cov, ids = 0, 0.0, 0, []
            for q in qs:
                hits = fn(q["question"], n)
                rank = next((i for i, h in enumerate(hits, 1) if any(has(h, g) for g in q["gold"])), None)
                hit += rank is not None
                rr += 1 / rank if rank else 0
                if q in conf:
                    need = {g["doc_id"] for g in q["gold"]}
                    got = {g["doc_id"] for h in hits for g in q["gold"] if has(h, g)}
                    if need <= got:
                        cov += 1
                        ids.append(q["id"])
            print(f"| {name} | {n} | {hit}/{len(qs)} | {rr / len(qs):.3f} | {cov}/{len(conf)} | {' '.join(ids) or '-'} |")
