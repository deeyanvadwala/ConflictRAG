# Injection test inputs

`attacks.jsonl` holds 8 **fabricated** passages written for this test. None of them is a NASA document, and every figure in them is false on purpose. Their document IDs have 10 digits (real NTRS IDs have 11), so they cannot be confused with corpus documents.

Each attack is paired with a **dev** question (never a test question) and a `success_regex`: if the system's answer matches it, the answer obeyed the hostile passage. Run with `python eval/injection_eval.py`.
