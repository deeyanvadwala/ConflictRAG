"""One command, one score table.

    python eval/run_eval.py --split dev            # baseline pipeline on the dev split
    python eval/run_eval.py --split dev --name x   # save results as eval/results/x_dev.json

Every LLM call (answers and judge verdicts) is cached in eval/cache/, keyed by the exact prompt,
provider and model. Reruns with unchanged prompts cost nothing and give identical numbers, and
the cache is committed so others can reproduce the table without an API key.

Metrics
- Retrieval (answerable questions): hit@3/5/10 = a top-k chunk contains a gold quote; MRR@10.
  conflict coverage@5 = for conflict questions, chunks containing quotes from EVERY gold document
  are in the top 5 (both sides of the disagreement reached the generator).
- Correctness: LLM judge with a rubric (correct / partial / incorrect) against the reference answer.
- Faithfulness: judge says every claim in the answer is supported by the retrieved context.
- Citation accuracy: answerable questions where at least one cited chunk contains a gold quote;
  invalid citations = numbers that point to no source.
- Abstention: unanswerable + model-knows questions where the system declined; false abstention =
  answerable questions it declined.
- Conflicts: detection = conflicting questions where the answer reports the disagreement;
  false-conflict rate = false-conflict traps where the answer claims a contradiction;
  stale = conflicting questions answered with only an older source's value.
- Latency: median seconds, measured when the answer was first generated (cache keeps it).
"""
import argparse, hashlib, json, os, pathlib, re, statistics, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from chunking import CFG          # noqa: E402
from generate import build_prompt, cited_numbers   # noqa: E402
from llm import LLMError, complete_meta   # noqa: E402
from strategies import STRATEGIES  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / "cache"
RESULTS = ROOT / "results"
NO_ANSWER_TAGS = {"unanswerable", "model-knows"}

JUDGE = """You are grading an answer from a question-answering system over NASA Mars mission documents.

Question: {question}
Question type: {tag}
Can the documents answer this question? {answerable}
Reference answer (written by a human from the documents): {reference}
{claims}
Retrieved context the system was given:
{context}

System answer:
{answer}

Grade it. Return ONLY a JSON object with these fields:
- "abstained": true if the system declined to answer or said the documents do not contain the answer.
- "correctness": "correct" if it matches the reference answer's key facts, "partial" if some key facts are right but some are missing or wrong, "incorrect" otherwise. If the documents CAN answer the question, abstaining is "incorrect" even when the retrieved context lacks the answer. If the documents CANNOT answer it, "correct" means the system abstained and did not present an outside answer as coming from the documents.
- "faithful": true if every factual claim in the system answer is supported by the retrieved context (outside knowledge counts as unsupported).
- "claims_disagreement": true if the answer says the sources disagree or give different values.
- "only_older_value": true if the answer gives only the value from an older source and omits the newer source's different value (false if not applicable).
- "reason": one short sentence."""

# Judge v2: one narrow question per call; code combines the parts (see changes.md C8).
J_DECLINED = """Here is a question and an answer written by an assistant that was given some documents.

Question: {question}

Answer:
{answer}

Which label fits the answer best?
- "answers": the answer gives the requested information, for example a number, name or choice, as found in the documents.
- "unavailable": the answer says the documents or context do not contain or state the requested information (even if it then guesses or speculates).
Return JSON: {{"label": "answers" or "unavailable"}}"""

J_CORRECT = """Compare an answer with a reference answer.

Question: {question}
Reference answer: {reference}

Answer to grade:
{answer}

First write the key fact(s) of the reference answer (numbers with units, names, choices).
Then write the key fact(s) the answer states for the same thing.
Then compare them: a different number or name is wrong, even if the answer sounds confident.
- "correct": all key facts match and none is contradicted (extra detail is fine).
- "partial": some key facts match, but some are missing or different.
- "incorrect": the key facts are missing or different.
Return JSON: {{"reference_facts": "...", "answer_facts": "...", "correctness": "correct" or "partial" or "incorrect"}}"""

J_DISAGREE = """Read this answer.

{answer}

Which label fits the answer best?
- "one_value": the answer gives one value or one account, or describes several plans without saying their values differ.
- "sources_differ": the answer explicitly says that different sources, documents, studies or versions give different values.
Return JSON: {{"label": "one_value" or "sources_differ"}}"""

J_VALUES = """Read this answer.

{answer}

Here are values that sources give for the question "{question}":
{values}

Which of these values does the answer state (in any wording or units)?
Return JSON: {{"stated": [list of the numbers of the values it states]}}"""

J_FAITHFUL = """Context given to an assistant:
{context}

The assistant's answer:
{answer}

Is every factual claim in the answer supported by the context? Statements that the context
lacks information count as supported. Outside knowledge counts as unsupported.
Return JSON: {{"faithful": true or false}}"""


from verify_gold import norm   # noqa: E402  same text matching as the gold verifier (dashes, quotes, ligatures)


USED = set()   # cache files used by this run (for --prune)


def cached_complete(prompt, json_mode=False):
    provider = CFG["llm_provider"]
    model = CFG["llm_models"][provider]
    settings = [provider, model, CFG["temperature"], CFG["max_output_tokens"], prompt]
    if json_mode:
        settings.append("json")
    key = hashlib.sha256(json.dumps(settings).encode()).hexdigest()[:24]
    path = CACHE / f"{key}.json"
    USED.add(path.name)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if os.environ.get("CONFLICTRAG_OFFLINE") == "1":   # CI replay: never call a model
        raise LLMError(f"cache miss {path.name} in offline mode: a prompt changed, or retrieval "
                       f"returned different chunks than when the cache was made")
    t = time.perf_counter()
    out, finish = complete_meta(prompt, json_mode=json_mode)
    if finish != "stop":   # never cache a cut-off or blocked output: it would be reused forever
        raise LLMError(f"model output ended with finish={finish}; not cached. "
                       f"Raise max_output_tokens in config.yaml if it was cut off.")
    rec = {"provider": provider, "model": model, "temperature": CFG["temperature"],
           "max_output_tokens": CFG["max_output_tokens"],
           "latency_s": round(time.perf_counter() - t, 2), "output": out,
           "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    CACHE.mkdir(exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    return rec


def parse_json(text):
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError(f"judge returned no JSON: {text[:200]!r}")
    return json.loads(m.group(0))


def gold_rank(hits, gold):
    """1-based rank of the first chunk containing any gold quote, else None."""
    for i, h in enumerate(hits, start=1):
        for g in gold:
            if h["meta"]["doc_id"] == g["doc_id"] and norm(g["quote"]) in norm(h["text"]):
                return i
    return None


def covers_all_docs(hits, gold):
    need = {g["doc_id"] for g in gold}
    got = {g["doc_id"] for h in hits for g in gold
           if h["meta"]["doc_id"] == g["doc_id"] and norm(g["quote"]) in norm(h["text"])}
    return need <= got


def ask(prompt):
    return parse_json(cached_complete(prompt, json_mode=True)["output"])


def judge_v1(q, answer, context):
    claims = ""
    if q.get("claims"):
        claims = "Known source claims (year order matters):\n" + "\n".join(
            f"- {c['doc_id']} ({c['year']}): {c['value']}" for c in q["claims"])
    answerable = "no" if q["tag"] in NO_ANSWER_TAGS else "yes"
    return ask(JUDGE.format(question=q["question"], tag=q["tag"], answerable=answerable,
                            reference=q["answer"], claims=claims, context=context, answer=answer))


def judge_v2(q, answer, context):
    declined = ask(J_DECLINED.format(question=q["question"], answer=answer)).get("label") == "unavailable"
    v = {"abstained": declined, "claims_disagreement": False, "only_older_value": False}
    if q["tag"] in NO_ANSWER_TAGS:
        v["correctness"] = "correct" if declined else "incorrect"   # rule applied by code
    elif declined:
        v["correctness"] = "incorrect"   # the documents can answer it; declining is a miss
    else:
        v["correctness"] = ask(J_CORRECT.format(question=q["question"], reference=q["answer"],
                                                answer=answer)).get("correctness", "incorrect")
    if q["tag"] in {"conflicting", "false-conflict"} and not declined:
        v["claims_disagreement"] = ask(J_DISAGREE.format(answer=answer)).get("label") == "sources_differ"
    if q["tag"] == "conflicting" and q.get("claims") and not declined:
        claims = sorted(q["claims"], key=lambda c: c["year"])
        values = "\n".join(f"{i}. {c['value']}" for i, c in enumerate(claims, start=1))
        stated = ask(J_VALUES.format(answer=answer, question=q["question"], values=values)).get("stated") or []
        stated = {int(s) for s in stated if str(s).isdigit()}
        newest = max(c["year"] for c in claims)
        idx_newest = {i for i, c in enumerate(claims, start=1) if c["year"] == newest}
        v["stated_values"] = sorted(stated)
        v["only_older_value"] = bool(stated) and not (stated & idx_newest)   # rule applied by code
        # Detecting a conflict = saying the sources differ AND stating values from at least two of them.
        v["claims_disagreement"] = v["claims_disagreement"] and len(stated) >= 2
    v["faithful"] = None if declined else bool(ask(J_FAITHFUL.format(context=context, answer=answer)).get("faithful"))
    return v


def run_one(q, k_gen, judge="v2", retrieval="topk", style="naive", conflict_check=False):
    hits = STRATEGIES[retrieval](q["question"], 10)   # top 10 for hit@k; the first k_gen go to the LLM
    gen_hits = hits[:k_gen]
    prompt = build_prompt(q["question"], gen_hits, style)
    gen = cached_complete(prompt)
    answer = gen["output"]
    check = None
    if conflict_check:   # E3: code compares extracted claims and appends a note
        from conflicts import check as run_check
        check = run_check(q["question"], gen_hits, ask)
        if check["note"]:
            answer = answer.rstrip() + "\n\n" + check["note"]
    # Citations are counted on the generator's own text, not on the appended note.
    cited = [n for n in cited_numbers(gen["output"]) if 1 <= n <= len(gen_hits)]
    invalid = [n for n in cited_numbers(gen["output"]) if not 1 <= n <= len(gen_hits)]

    context = "\n\n".join(f"[{n}] {h['text']}" for n, h in enumerate(gen_hits, start=1))
    if judge == "none":   # answers only: lets a human label them before seeing any judge verdict
        verdict = {}
    else:
        verdict = (judge_v1 if judge == "v1" else judge_v2)(q, answer, context)

    gold = q.get("gold", [])
    return {
        "id": q["id"], "tag": q["tag"], "question": q["question"], "answer": answer,
        "retrieved": [h["chunk_id"] for h in hits],
        "gold_rank": gold_rank(hits, gold) if gold else None,
        "conflict_covered@5": covers_all_docs(hits[:5], gold) if q["tag"] in {"conflicting", "false-conflict"} else None,
        "cited": cited, "invalid_citations": invalid,
        "cited_gold": any(gold_rank([gen_hits[n - 1]], gold) for n in cited) if gold else None,
        "verdict": verdict, "latency_s": gen["latency_s"],
        "conflict_check": check,
    }


def rate(xs):
    xs = [bool(x) for x in xs]
    return (sum(xs) / len(xs), len(xs)) if xs else (None, 0)


def summarize(rows):
    ans = [r for r in rows if r["tag"] not in NO_ANSWER_TAGS]
    noans = [r for r in rows if r["tag"] in NO_ANSWER_TAGS]
    conf = [r for r in rows if r["tag"] == "conflicting"]
    trap = [r for r in rows if r["tag"] == "false-conflict"]
    v = lambda r, f: r["verdict"].get(f)
    m = {}
    for k in (3, 5, 10):
        m[f"hit@{k}"] = rate([r["gold_rank"] and r["gold_rank"] <= k for r in ans])
    rr = [1 / r["gold_rank"] if r["gold_rank"] else 0 for r in ans]
    m["MRR@10"] = (sum(rr) / len(rr), len(rr)) if rr else (None, 0)
    m["conflict coverage@5"] = rate([r["conflict_covered@5"] for r in conf + trap])
    m["correct (answerable)"] = rate([v(r, "correctness") == "correct" for r in ans])
    m["correct or partial (answerable)"] = rate([v(r, "correctness") in ("correct", "partial") for r in ans])
    m["faithful (answered)"] = rate([v(r, "faithful") for r in rows if not v(r, "abstained") and v(r, "faithful") is not None])
    m["citation hits gold"] = rate([r["cited_gold"] for r in ans])
    m["invalid citations (answers with any)"] = rate([r["invalid_citations"] for r in rows])
    m["abstention accuracy (no-answer qs)"] = rate([v(r, "abstained") for r in noans])
    m["false abstention (answerable)"] = rate([v(r, "abstained") for r in ans])
    m["conflict detection"] = rate([v(r, "claims_disagreement") for r in conf])
    m["false-conflict rate (traps)"] = rate([v(r, "claims_disagreement") for r in trap])
    m["stale answer (conflicting)"] = rate([v(r, "only_older_value") for r in conf])
    if any(r.get("conflict_check") for r in rows):   # measured by code, no judge
        flag = lambda r: r["conflict_check"]["decision"] == "conflict"
        other = [r for r in ans if r["tag"] not in {"conflicting", "false-conflict"}]
        m["module flags conflict (conflicting)"] = rate([flag(r) for r in conf])
        m["module flags conflict (traps)"] = rate([flag(r) for r in trap])
        m["module flags conflict (other answerable)"] = rate([flag(r) for r in other])
    lat = [r["latency_s"] for r in rows]
    m["median LLM latency s"] = (statistics.median(lat), len(lat)) if lat else (None, 0)
    return m


def table(m, title):
    lines = [f"## {title}", "", "| Metric | Value | n |", "|---|---|---|"]
    for k, (val, n) in m.items():
        if val is None:
            s = "-"
        elif "latency" in k:
            s = f"{val:.1f}"
        elif k.startswith("MRR"):
            s = f"{val:.3f}"
        else:
            s = f"{val:.0%}"
        lines.append(f"| {k} | {s} | {n} |")
    return "\n".join(lines)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    p.add_argument("--name", default="baseline")
    p.add_argument("--questions", default=str(ROOT / "questions.jsonl"))
    p.add_argument("--only", nargs="*", help="run only these question ids (smoke test)")
    p.add_argument("--retrieval", choices=sorted(STRATEGIES), default=CFG["retrieval"])
    p.add_argument("--prompt", choices=["naive", "conflict", "guarded"], default=CFG["prompt"])
    p.add_argument("--conflict-check", action="store_true",
                   help="E3: append a code-decided source comparison to each answer (conflicts.py)")
    p.add_argument("--judge", choices=["v1", "v2", "none"], default="v2",
                   help="v1 = single-prompt judge used for B0; v2 = narrow questions combined by code")
    p.add_argument("--prune", action="store_true",
                   help="after the run, delete cache files this run did not use (run with --split all)")
    a = p.parse_args()

    qs = [json.loads(l) for l in open(a.questions, encoding="utf-8") if l.strip()]
    if a.split != "all":
        qs = [q for q in qs if q.get("split") == a.split]
    if a.only:
        qs = [q for q in qs if q["id"] in a.only]
    if not qs:
        sys.exit("no questions selected")

    rows = []
    for i, q in enumerate(qs, start=1):
        print(f"[{i}/{len(qs)}] {q['id']} {q['tag']}", file=sys.stderr)
        rows.append(run_one(q, CFG["top_k"], judge=a.judge, retrieval=a.retrieval, style=a.prompt,
                            conflict_check=a.conflict_check))
    m = summarize(rows)
    provider = CFG["llm_provider"]
    title = (f"{a.name} / {a.split} ({len(rows)} questions; {provider} {CFG['llm_models'][provider]}, judge {a.judge}, retrieval {a.retrieval}, prompt {a.prompt}, "
             f"conflict check {'on' if a.conflict_check else 'off'}, "
             f"k={CFG['top_k']}, {CFG['chunk_chars']}/{CFG['chunk_overlap']} chunks)")
    out = table(m, title)
    print(out)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{a.name}_{a.split}.json").write_text(
        json.dumps({"title": title, "metrics": m, "rows": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    (RESULTS / f"{a.name}_{a.split}.md").write_text(out + "\n", encoding="utf-8")
    if a.prune:
        stale = [f for f in CACHE.glob("*.json") if f.name not in USED]
        for f in stale:
            f.unlink()
        print(f"pruned {len(stale)} unused cache files", file=sys.stderr)
