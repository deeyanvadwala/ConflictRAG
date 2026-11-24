"""CI smoke test: 8 dev questions through the final system, scores checked against thresholds.

    CONFLICTRAG_OFFLINE=1 python eval/smoke.py     # replay LLM outputs from eval/cache (CI)
    python eval/smoke.py                           # with Ollama running: calls it on cache misses

Retrieval runs for real (needs the index). With CONFLICTRAG_OFFLINE=1 a cache miss fails the run:
it means a prompt changed or retrieval returned different chunks than when the cache was made.
Thresholds sit just under the recorded dev results for these questions (d1_guarded_dev).
"""
import pathlib, sys, json

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from run_eval import CFG, ROOT, run_one, summarize, table   # noqa: E402

SMOKE = ["cf01", "dra02", "dra07", "emc03", "fc01", "mk01", "rm05", "un01"]
THRESHOLDS = {                      # metric: (minimum or maximum, value)
    "hit@5": ("min", 0.80),
    "correct or partial (answerable)": ("min", 0.80),
    "abstention accuracy (no-answer qs)": ("min", 1.0),
    "false-conflict rate (traps)": ("max", 0.0),
    "invalid citations (answers with any)": ("max", 0.0),
}

if __name__ == "__main__":
    qs = [json.loads(l) for l in open(ROOT / "questions.jsonl", encoding="utf-8") if l.strip()]
    qs = [q for q in qs if q["id"] in SMOKE]
    rows = [run_one(q, CFG["top_k"], retrieval=CFG["retrieval"], style=CFG["prompt"]) for q in qs]
    m = summarize(rows)
    print(table(m, f"smoke ({len(rows)} dev questions, retrieval {CFG['retrieval']}, prompt {CFG['prompt']})"))
    failed = []
    for k, (kind, limit) in THRESHOLDS.items():
        val = m[k][0]
        ok = val is not None and (val >= limit if kind == "min" else val <= limit)
        print(f"{'PASS' if ok else 'FAIL'}  {k} = {val} ({kind} {limit})")
        failed += [] if ok else [k]
    sys.exit(1 if failed else 0)
