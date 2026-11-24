## d1_guarded / dev (30 questions; ollama llama3.1:8b, judge v2, retrieval study_pool_rerank, prompt guarded, conflict check off, k=5, 1500/200 chunks)

| Metric | Value | n |
|---|---|---|
| hit@3 | 50% | 24 |
| hit@5 | 71% | 24 |
| hit@10 | 71% | 24 |
| MRR@10 | 0.478 | 24 |
| conflict coverage@5 | 29% | 7 |
| correct (answerable) | 38% | 24 |
| correct or partial (answerable) | 75% | 24 |
| faithful (answered) | 95% | 20 |
| citation hits gold | 46% | 24 |
| invalid citations (answers with any) | 0% | 30 |
| abstention accuracy (no-answer qs) | 100% | 6 |
| false abstention (answerable) | 17% | 24 |
| conflict detection | 0% | 5 |
| false-conflict rate (traps) | 0% | 2 |
| stale answer (conflicting) | 20% | 5 |
| median LLM latency s | 4.9 | 30 |
