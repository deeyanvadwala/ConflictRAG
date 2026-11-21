## e2_conflictprompt / dev (30 questions; ollama llama3.1:8b, judge v2, retrieval study_pool_rerank, prompt conflict, k=5, 1500/200 chunks)

| Metric | Value | n |
|---|---|---|
| hit@3 | 50% | 24 |
| hit@5 | 71% | 24 |
| hit@10 | 71% | 24 |
| MRR@10 | 0.478 | 24 |
| conflict coverage@5 | 29% | 7 |
| correct (answerable) | 17% | 24 |
| correct or partial (answerable) | 71% | 24 |
| faithful (answered) | 71% | 21 |
| citation hits gold | 62% | 24 |
| invalid citations (answers with any) | 3% | 30 |
| abstention accuracy (no-answer qs) | 100% | 6 |
| false abstention (answerable) | 12% | 24 |
| conflict detection | 20% | 5 |
| false-conflict rate (traps) | 100% | 2 |
| stale answer (conflicting) | 60% | 5 |
| median LLM latency s | 5.3 | 30 |
