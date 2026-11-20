## baseline_j2 / dev (30 questions; ollama llama3.1:8b, judge v2, k=5, 1500/200 chunks)

| Metric | Value | n |
|---|---|---|
| hit@3 | 38% | 24 |
| hit@5 | 46% | 24 |
| hit@10 | 67% | 24 |
| MRR@10 | 0.305 | 24 |
| conflict coverage@5 | 0% | 7 |
| correct (answerable) | 25% | 24 |
| correct or partial (answerable) | 62% | 24 |
| faithful (answered) | 95% | 19 |
| citation hits gold | 25% | 24 |
| invalid citations (answers with any) | 0% | 30 |
| abstention accuracy (no-answer qs) | 100% | 6 |
| false abstention (answerable) | 21% | 24 |
| conflict detection | 0% | 5 |
| false-conflict rate (traps) | 0% | 2 |
| stale answer (conflicting) | 40% | 5 |
| median LLM latency s | 6.0 | 30 |
