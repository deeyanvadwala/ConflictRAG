## baseline / dev (30 questions; ollama llama3.1:8b, k=5, 1500/200 chunks)

| Metric | Value | n |
|---|---|---|
| hit@3 | 38% | 24 |
| hit@5 | 46% | 24 |
| hit@10 | 67% | 24 |
| MRR@10 | 0.305 | 24 |
| conflict coverage@5 | 0% | 7 |
| correct (answerable) | 33% | 24 |
| correct or partial (answerable) | 46% | 24 |
| faithful (answered) | 32% | 28 |
| citation hits gold | 25% | 24 |
| invalid citations (answers with any) | 0% | 30 |
| abstention accuracy (no-answer qs) | 33% | 6 |
| false abstention (answerable) | 0% | 24 |
| conflict detection | 80% | 5 |
| false-conflict rate (traps) | 0% | 2 |
| stale answer (conflicting) | 80% | 5 |
| median LLM latency s | 6.0 | 30 |
