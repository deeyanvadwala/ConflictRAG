"""Compare judge verdicts with hand labels, and score the system from the hand labels.

    python eval/judge_agreement.py eval/results/baseline_dev.json eval/hand_labels_dev.jsonl
"""
import json, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
NO_ANSWER = {"unanswerable", "model-knows"}
FIELDS = ["correctness", "abstained", "claims_disagreement", "only_older_value"]

res = json.load(open(sys.argv[1], encoding="utf-8"))
labels = {l["id"]: l for l in map(json.loads, open(sys.argv[2], encoding="utf-8")) if l}
rows = [r for r in res["rows"] if r["id"] in labels]

print(f"Judge vs hand labels ({len(rows)} questions)\n")
print("| Field | Agreement |\n|---|---|")
for f in FIELDS:
    agree = sum(r["verdict"].get(f) == labels[r["id"]][f] for r in rows)
    print(f"| {f} | {agree}/{len(rows)} ({agree / len(rows):.0%}) |")


def pct(xs):
    xs = list(xs)
    return f"{sum(xs)}/{len(xs)} ({sum(xs) / len(xs):.0%})" if xs else "-"


H = lambda r: labels[r["id"]]
ans = [r for r in rows if r["tag"] not in NO_ANSWER]
noans = [r for r in rows if r["tag"] in NO_ANSWER]
conf = [r for r in rows if r["tag"] == "conflicting"]
trap = [r for r in rows if r["tag"] == "false-conflict"]
print("\nScores from hand labels\n")
print("| Metric | Value |\n|---|---|")
print(f"| correct (answerable) | {pct(H(r)['correctness'] == 'correct' for r in ans)} |")
print(f"| correct or partial (answerable) | {pct(H(r)['correctness'] in ('correct', 'partial') for r in ans)} |")
print(f"| abstention accuracy (no-answer qs) | {pct(H(r)['abstained'] for r in noans)} |")
print(f"| false abstention (answerable) | {pct(H(r)['abstained'] for r in ans)} |")
print(f"| conflict detection | {pct(H(r)['claims_disagreement'] for r in conf)} |")
print(f"| false-conflict rate (traps) | {pct(H(r)['claims_disagreement'] for r in trap)} |")
print(f"| stale answer (conflicting) | {pct(H(r)['only_older_value'] for r in conf)} |")
