## final / test (14 questions; ollama llama3.1:8b, judge v2, retrieval study_pool_rerank, prompt guarded, conflict check off, k=5, 1500/200 chunks)

| Metric | Value | n |
|---|---|---|
| hit@3 | 40% | 10 |
| hit@5 | 60% | 10 |
| hit@10 | 70% | 10 |
| MRR@10 | 0.348 | 10 |
| conflict coverage@5 | 0% | 3 |
| correct (answerable) | 30% | 10 |
| correct or partial (answerable) | 50% | 10 |
| faithful (answered) | 100% | 9 |
| citation hits gold | 40% | 10 |
| invalid citations (answers with any) | 0% | 14 |
| abstention accuracy (no-answer qs) | 100% | 4 |
| false abstention (answerable) | 10% | 10 |
| conflict detection | 0% | 2 |
| false-conflict rate (traps) | 0% | 1 |
| stale answer (conflicting) | 0% | 2 |
| median LLM latency s | 5.2 | 14 |
