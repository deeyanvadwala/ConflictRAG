"""Conflict check (experiment E3): extract one claim per retrieved passage, compare them in code.

The generator's answer is left unchanged. This module adds a "Source check" note to it when the
passages give different values. Whether two values conflict is decided here, by code, not by the
model (see failure F6: the 8B model called almost everything a disagreement).

Steps
1. Extract: for each passage, the LLM answers one narrow JSON question: does this passage state
   a value for the question, and if so, which value, unit and study it belongs to, and the exact
   sentence.
2. Verify: the sentence must appear in the passage and contain the number; otherwise the claim is dropped.
   A second narrow call asks whether the sentence answers the question itself or states a value
   for something else (another quantity, phase or option); "something else" is dropped.
3. Filter: if the question names one study (e.g. DRA 5.0), claims that the passage attributes to a
   different study are dropped. The study comes from the passage text, not the file label (R1).
4. Compare: units are converted (months/sols/years -> days, kg -> t). Values more than TOLERANCE
   apart, from at least two documents, are a conflict. Values that only differ in raw units are a
   unit difference, not a conflict.

usage:
    python conflicts.py "How long do astronauts stay on the Martian surface in Version 1.0?"
"""
import json
import re
import sys

from chunking import CFG

TOLERANCE = 0.05   # fixed before the E3 run; not tuned on dev

EXTRACT = """You are reading one passage from a NASA Mars mission document.

Question: {question}

Passage:
{text}

Does this passage itself state a value that answers the question?
The value must be for exactly the quantity the question asks about. A value for a different quantity
(for example a transit time when the question asks about a stay time, or one vehicle's mass when it
asks about a total) does not count.
If yes, return JSON:
{{"answers": true,
 "value": "the value as written, e.g. '600 days' or 'six crewmembers'",
 "number": the main number as a numeral (the middle of a range), or null,
 "unit": "the unit of the number, e.g. days, sols, months, t, kWe, crew",
 "describes": "the mission study, version or option the value belongs to, as the passage names it",
 "quote": "the exact sentence from the passage that states the value"}}
If the passage does not state such a value, return {{"answers": false}}."""

RELEVANT = """Question: {question}

A sentence from a NASA document:
"{quote}"

Value taken from it: {value}

Is this value an answer to the question itself, or a value for something else (a different
quantity, mission phase or option)?
Return JSON: {{"label": "answers_question" or "something_else"}}"""

# Study names that a question or passage may use. Version 3.0 is checked before 1.0.
STUDY_ALIASES = {
    "RM 3.0": ["version 3.0", "reference mission 3.0", "rm 3.0"],
    "RM 1.0": ["version 1.0", "reference mission 1.0", "rm 1.0", "sp-6107"],
    "DRA 5.0": ["dra 5.0", "design reference architecture 5.0", "dra5", "dra-5"],
    "EMC": ["evolvable mars campaign", "emc"],
}

# unit -> (canonical unit, factor). Unknown units are compared only with the same raw unit.
UNITS = {
    "day": ("day", 1), "days": ("day", 1), "d": ("day", 1),
    "sol": ("day", 1.0275), "sols": ("day", 1.0275),
    "month": ("day", 30.44), "months": ("day", 30.44),
    "year": ("day", 365.25), "years": ("day", 365.25),
    "t": ("t", 1), "mt": ("t", 1), "tonnes": ("t", 1), "tonne": ("t", 1),
    "metric tons": ("t", 1), "metric ton": ("t", 1), "kg": ("t", 0.001),
    "kw": ("kw", 1), "kwe": ("kw", 1),
    "crew": ("crew", 1), "crewmembers": ("crew", 1), "crew members": ("crew", 1),
    "astronauts": ("crew", 1), "people": ("crew", 1), "persons": ("crew", 1),
}

NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}


def studies_named(text):
    """Set of study keys named in a text (empty if none)."""
    t = " " + (text or "").lower() + " "
    found = set()
    for key, aliases in STUDY_ALIASES.items():
        for a in aliases:
            if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", t):
                found.add(key)
                break
    return found


def _norm(s):
    from eval.verify_gold import norm
    return re.sub(r"\s+", " ", norm(s)).strip()


def _number(x):
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip().lower().replace(",", "")
        if s in NUMBER_WORDS:
            return float(NUMBER_WORDS[s])
        try:
            return float(s)
        except ValueError:
            return None
    return None


def verified(claim, text):
    """'quote' if the quote is in the passage and contains the number, else None."""
    q = _norm(claim.get("quote") or "")
    if len(q) <= 10 or q not in _norm(text):
        return None
    n = claim["number"]
    forms = {f"{n:g}"} | {w for w, v in NUMBER_WORDS.items() if v == n}
    value_nums = re.findall(r"\d+(?:\.\d+)?", claim.get("value") or "")
    forms |= set(value_nums)   # a range "450-550" has middle 500, which is not written
    ql = q.lower()
    if any(re.search(r"(?<![\d.])" + re.escape(f) + r"(?![\d])", ql) for f in forms):
        return "quote"
    return None


def extract(question, hits, ask):
    """One claim (or None) per hit. ask(prompt) -> parsed JSON dict."""
    claims = []
    for n, h in enumerate(hits, start=1):
        try:
            out = ask(EXTRACT.format(question=question, text=h["text"]))
        except (ValueError, json.JSONDecodeError):
            out = {}
        if not out.get("answers"):
            continue
        c = {"source": n, "doc_id": h["meta"]["doc_id"], "year": h["meta"]["year"],
             "value": str(out.get("value") or "").strip(), "number": _number(out.get("number")),
             "unit": str(out.get("unit") or "").strip().lower(),
             "describes": str(out.get("describes") or "").strip(),
             "quote": str(out.get("quote") or "").strip()}
        if c["number"] is None:
            continue
        c["verified"] = verified(c, h["text"])
        if not c["verified"]:
            continue
        try:   # second, narrower call: is this the asked-for quantity? (E3 v3)
            rel = ask(RELEVANT.format(question=question, quote=c["quote"], value=c["value"]))
        except (ValueError, json.JSONDecodeError):
            rel = {}
        c["relevant"] = rel.get("label") == "answers_question"
        if c["relevant"]:
            claims.append(c)
    return claims


def compare(question, claims):
    """Decide: 'none' (fewer than 2 usable claims), 'agree', 'unit_difference' or 'conflict'."""
    target = studies_named(question)
    kept = []
    for c in claims:
        named = studies_named(c["describes"])
        if len(target) == 1 and named and not (named & target):
            continue   # the passage says this value belongs to a different study
        unit, factor = UNITS.get(c["unit"], (c["unit"], 1))
        kept.append({**c, "base_unit": unit, "base": c["number"] * factor})
    if len({c["doc_id"] for c in kept}) < 2:
        return {"decision": "none", "claims": kept}

    # Only compare claims that share a canonical unit with the most common one.
    units = [c["base_unit"] for c in kept]
    main = max(set(units), key=units.count)
    same = sorted((c for c in kept if c["base_unit"] == main), key=lambda c: c["base"])
    groups = []
    for c in same:
        if groups and abs(c["base"] - groups[-1][0]["base"]) <= TOLERANCE * max(abs(groups[-1][0]["base"]), 1e-9):
            groups[-1].append(c)
        else:
            groups.append([c])
    docs_per_group = [{c["doc_id"] for c in g} for g in groups]
    if len(groups) >= 2 and len(set().union(*docs_per_group)) >= 2:
        decision = "conflict"
    elif len({c["unit"] for c in same}) > 1 and {UNITS.get(c["unit"], (None, 1))[1] for c in same} != {1}:
        decision = "unit_difference"
    else:
        decision = "agree"
    return {"decision": decision, "claims": kept, "groups": [[c["source"] for c in g] for g in groups]}


def _label(c):
    d = f"; describes {c['describes']}" if c["describes"] else ""
    return f"[{c['source']}] (document {c['doc_id']}, {c['year']}{d}): \"{c['value']}\""


def note(result):
    """Text appended to the answer, or '' when there is nothing to report."""
    d = result["decision"]
    cs = sorted(result["claims"], key=lambda c: c["year"])
    if d == "conflict":
        newest = cs[-1]
        lines = ["Source check: the sources give different values."]
        lines += [f"- {_label(c)}" for c in cs]
        lines.append(f"The newest source is [{newest['source']}] ({newest['year']}).")
        return "\n".join(lines)
    if d == "unit_difference":
        lines = ["Source check: the values use different units but agree after conversion "
                 f"(within {TOLERANCE:.0%}); this is a unit difference, not a disagreement."]
        lines += [f"- {_label(c)}" for c in cs]
        return "\n".join(lines)
    return ""


def check(question, hits, ask):
    claims = extract(question, hits, ask)
    result = compare(question, claims)
    result["note"] = note(result)
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from llm import complete_meta
    from strategies import STRATEGIES

    def ask(prompt):
        text, _ = complete_meta(prompt, json_mode=True)
        m = re.search(r"\{.*\}", text, flags=re.S)
        return json.loads(m.group(0)) if m else {}

    q = sys.argv[1]
    hits = STRATEGIES["study_pool_rerank"](q, CFG["top_k"])
    r = check(q, hits, ask)
    print(json.dumps({k: v for k, v in r.items() if k != "note"}, indent=1, ensure_ascii=False))
    print("\n" + (r["note"] or "(no note)"))
