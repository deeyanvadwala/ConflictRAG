"""Web UI for ConflictRAG (Gradio). Runs the same pipeline the eval measures (generate.answer).

usage:
    python app.py            # then open http://127.0.0.1:7860

Caps (config.yaml, section app): question length, answer length, requests per session per
minute, and a daily total. They keep a public demo cheap and hard to abuse.
"""
import datetime
import sys
import threading
import time

import gradio as gr

from chunking import CFG
from generate import answer
from llm import LLMError

APP = CFG["app"]
CFG["max_output_tokens"] = APP["max_answer_tokens"]   # app answers only; the eval keeps its own setting

_lock = threading.Lock()
_day = {"date": None, "count": 0}

EXAMPLES = [
    "How many crew members does DRA 5.0 plan for?",
    "What surface power system does DRA 5.0 use, and how many kilowatts?",
    "How long do astronauts stay on the Martian surface in NASA's Version 1.0 Mars Reference Mission?",
]

ABOUT = """### ConflictRAG: NASA human Mars mission studies, 1997-2015
Answers come only from 12 NASA documents (Reference Mission 1.0/3.0, DRA 5.0, Evolvable Mars Campaign).
Each source shows its **publication year**. Studies changed over time, so check the year before trusting a number.
**Known limits:** a local 8B model writes the answers; it can mix values from different studies, and it does
not yet flag when sources disagree (see the project README). Do not paste personal or sensitive text."""


def _daily_ok():
    today = datetime.datetime.now(datetime.timezone.utc).date()
    with _lock:
        if _day["date"] != today:
            _day.update(date=today, count=0)
        if _day["count"] >= APP["daily_cap"]:
            return False
        _day["count"] += 1
        return True


def ask(question, history):
    history = [t for t in (history or []) if time.time() - t < 60]
    question = (question or "").strip()
    if not question:
        return "Please type a question.", [], history
    if len(question) > APP["max_question_chars"]:
        return f"Please keep questions under {APP['max_question_chars']} characters.", [], history
    if len(history) >= APP["per_user_per_minute"]:
        return "Too many questions in the last minute. Please wait a moment.", [], history
    if not _daily_ok():
        return "The demo has reached today's question limit. Please try again tomorrow (UTC).", [], history
    history.append(time.time())
    try:
        r = answer(question)
    except LLMError as e:
        print(f"LLM error: {e}", file=sys.stderr)   # details stay in the server log
        return "The language model is not available right now. Please try again later.", [], history
    rows = []
    for n, h in enumerate(r["hits"], start=1):
        m = h["meta"]
        rows.append([f"[{n}]", "yes" if n in r["cited"] else "", m["year"], m["study"],
                     m["doc_id"], f"{m['page_start']}-{m['page_end']}", m["source_url"]])
    text = r["answer"].strip()
    if r["invalid_citations"]:
        text += f"\n\n*Warning: the answer cites sources that do not exist: {r['invalid_citations']}*"
    if not r["cited"]:
        text += "\n\n*Warning: the answer cites no sources.*"
    if r.get("dropped_untrusted"):
        text += (f"\n\n*Removed {len(r['dropped_untrusted'])} passage(s) from documents outside the "
                 f"verified corpus: {r['dropped_untrusted']}*")
    return text, rows, history


with gr.Blocks(title="ConflictRAG") as demo:
    gr.Markdown(ABOUT)
    q = gr.Textbox(label="Question", max_length=APP["max_question_chars"], lines=2)
    go = gr.Button("Ask", variant="primary")
    out = gr.Markdown()
    src = gr.Dataframe(headers=["#", "cited", "year", "document label", "NTRS id", "PDF pages", "link"],
                       label="Retrieved sources (label = publisher's study; the passage may describe another)",
                       interactive=False, wrap=True)
    state = gr.State([])
    gr.Examples(EXAMPLES, inputs=q)
    go.click(ask, [q, state], [out, src, state], concurrency_limit=1)
    q.submit(ask, [q, state], [out, src, state], concurrency_limit=1)


if __name__ == "__main__":
    demo.queue(max_size=20).launch()
