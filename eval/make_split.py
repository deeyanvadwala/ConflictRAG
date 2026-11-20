"""Assign dev/test splits once, stratified by tag, with a fixed seed.

    python eval/make_split.py

Refuses to run if any question already has a split: the test split must never be reshuffled
after it has been created (that would let test questions leak into dev tuning).
"""
import collections, json, pathlib, random, sys

PATH = pathlib.Path(__file__).resolve().parent / "questions.jsonl"
TEST_FRACTION = 0.3
SEED = 42

qs = [json.loads(l) for l in open(PATH, encoding="utf-8") if l.strip()]
if any("split" in q for q in qs):
    sys.exit("splits already assigned; refusing to reshuffle")

rng = random.Random(SEED)
by_tag = collections.defaultdict(list)
for q in qs:
    by_tag[q["tag"]].append(q)
for tag in sorted(by_tag):
    group = sorted(by_tag[tag], key=lambda q: q["id"])
    rng.shuffle(group)
    n_test = max(1, round(len(group) * TEST_FRACTION))
    for i, q in enumerate(group):
        q["split"] = "test" if i < n_test else "dev"

with open(PATH, "w", encoding="utf-8") as f:
    for q in qs:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")
counts = collections.Counter((q["tag"], q["split"]) for q in qs)
for tag in sorted(by_tag):
    print(f"{tag:<16} dev {counts[(tag, 'dev')]:>2}  test {counts[(tag, 'test')]:>2}")
