# Change log

One change per entry. Record what changed, why, and the same checks before and after.
Until the dev set exists, the checks are check_gold.py, diagnose.py (F1) and test_queries.py.
These are 3-10 hand-picked queries, so they show direction only, not a score.

## C1: keep mid-page numbers in ingest.py (2026-11-20)

- **Change:** ingest.py drops bare-number lines only at page edges, and the repeated-header filter ignores lines without letters. Re-ran ingest.py and index.py.
- **Why:** a data-correctness fix (failure_log F2), not tuned on any query. The old filters deleted table values such as the crew-size row of 20160006315 Table 1.
- **Settings unchanged:** bge-small-en-v1.5, 1500/200 chunks, k as listed.

| Check | Before | After |
|---|---|---|
| Total chunks | 816 | 818 |
| F1 gold 20090040343_0027 (DRA 5.0 crew) | rank 41, distance 0.381 | rank 39 of 818, distance 0.381 |
| EMC crew gold 20140016934 p.1 / p.2 (k=20) | rank 1 / 4 | rank 1 / 4 |
| IMLEO gold 20090040343 p.15 (k=20) | rank 16 | rank 14 |
| IMLEO gold 20090010571 p.36 (k=20) | rank 4 | rank 2 |
| Perseverance (off-topic) top-1 distance | 0.363 | 0.357 |

- **Notes:** the F1 chunk's text is unchanged (same distance); its rank moved because other chunks changed. Chunk IDs after any changed region shift, so gold must not be stored as chunk IDs. The off-topic question now sits slightly closer to the corpus, which matters for abstention.

## C2: a retrieval hit must contain the verified quote (2026-11-20)

- **Change:** check_gold.py gold is now (doc_id, PDF page, quote). A hit is a retrieved chunk from that document whose text contains the quote, ignoring case and line breaks. The old page-range rule is printed alongside for comparison. Added the secondary DRA 5.0 crew passage (failure_log F1 correction). No pipeline change, index untouched.
- **Why:** the page rule counted any chunk whose page range covered the gold page, even if it lacked the answer.
- **Checked:** every gold quote appears whole in at least one chunk, so a miss is a retrieval miss, not a chunk-boundary artifact.

| Gold passage (k=20) | Page rule | Quote rule |
|---|---|---|
| 20090040343 p.7 "envisions sending six crewmembers to Mars" | not in top 20 | not in top 20 |
| 20160006315 p.5 "a crew of six transfers to Mars" | rank 1 | rank 1 |
| 20140016934 p.1 "at least 4 crew for up to 500 sols" | rank 1 | rank 1 |
| 20090040343 p.15 "has an IMLEO of 356.4 t" | **rank 14** | **not in top 20** (true rank 155, failure_log F3) |
| 20090010571 p.36 "IMLEO ~336.5 t" | rank 2 | rank 2 |

- **Result:** the page rule overstated one of five passages. The eval script will use the quote rule.

## C3: pin the embedding model revision (2026-11-20)

- **Change:** config.yaml `embedding_revision: 5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` (the commit already in the local Hugging Face cache); index.py and retrieve.py load that revision, and index.py records it in index_info.json.
- **Why:** without a revision, a model update on Hugging Face could silently change every distance.
- **Check:** F1 gold chunk still rank 39 of 818, distance 0.381 (identical). Index not rebuilt; index_info.json gains the field at the next rebuild.

## C4: add DRA 5.0 Addendum #2, chapters 1-2; freeze the corpus (2026-11-20)

- **Change:** added 20160003093 (NASA/SP-2009-566-ADD2, cover dated "March 2014", so year 2014), PDF pages 25-90 only: chapter 1 "Summary of Assessments Conducted since DRA 5" and chapter 2 "Earth-Mars Trajectories" (chapter 3 starts on PDF page 91). New optional `pages` column in data/metadata.csv; ingest.py extracts only that range and keeps original PDF page numbers in the `[[PAGE n]]` markers. download.py no longer lists the dropped duplicate 20100028285.
- **Why only chapters 1-2:** the full document is 598 pages (about 3.5x the 1997 book) and would have been about 60% of all chunks. Chapters 1-2 are the parts that update DRA 5.0. This is a corpus selection decision and must be stated in the README.
- **Check:** the 11 existing cleaned files are byte-identical to before. The new file's page markers run 25 to 90.
- **Searched for, not added:** DRA 5.0 Addendum #1 (not found by NTRS search); Moon to Mars Architecture Definition Document revisions and other EMC papers (not chosen).

| Check | Before (C3) | After |
|---|---|---|
| Total chunks | 818 | 972 (154 from 20160003093, 16%) |
| F1 gold 20090040343_0027 | rank 39, distance 0.381 | rank 48 of 972, distance 0.381 |
| check_gold.py, quote rule | as C2 | unchanged for all five passages |

- **Freeze:** data/corpus_manifest.csv records the SHA-256 of all 12 PDFs; `python manifest.py` verifies them. From here on the corpus does not change; any change needs a new entry here and a rerun of every score.

## C5: eval set drafted; eval tooling; generation output limit (2026-11-20)

- **Eval set (draft, not yet split or frozen):** eval/questions.jsonl, 44 questions: 15 easy, 9 multi-step, 7 conflicting, 3 false-conflict, 5 unanswerable, 5 model-knows. Easy and multi-step questions were drafted per document group, then each was read by hand against its quote. `python eval/verify_gold.py` checks every gold quote is on its PDF page and in data/clean, and every absent term for unanswerable and model-knows questions is missing from the corpus.
- **Dropped or changed during review:** rm07 dropped (Version 3.0 launch count is ambiguous: "two additional flights" vs "two launches ... eliminated"); dra10 dropped (its margin depends on which stay figure is used, ~500 or 540 days); rm02 retagged as conflicting (1997 book "600 days nominal" vs 1998 addendum "500-day surface mission" for Version 1.0); dra04, dra06 reworded; emc07 gold changed to the Table 1 cell; a Curiosity landing-date question was dropped because PDF page 56 of 20160003093 says MSL is "scheduled to land in August of this year".
- **fc01 rewritten:** the first wording ("Do DRA 5.0 and the EMC disagree about how long the crew stays on the surface?") was ambiguous: in a two-question smoke test the baseline answered "yes" citing 20160006315 Table 1 (450-550 vs 320-550 days at Mars), which the corpus does support. The question now asks only about the 500 days vs 500 sols unit difference. This was before any split existed.
- **Limitation:** absent-term checks show the terms are missing, not that the answer is missing. One candidate (Curiosity) passed the term check but was partly answerable.
- **Tooling:** eval/run_eval.py (one score table, cached LLM calls in eval/cache/), eval/make_split.py (stratified, seed 42, refuses to reshuffle), eval/verify_gold.py.
- **Generation setting changed:** `max_output_tokens` 1024 -> 4096. Gemini 3.5 counts hidden "thinking" tokens against this limit, and the smoke-test judge verdict was cut off mid-JSON. llm.py now reports why the model stopped (`complete_meta`), and run_eval.py refuses to cache any output that did not end normally. No baseline scores existed yet, so no comparison is affected.

## C6: eval set approved, split and frozen (2026-11-20)

- 44 questions approved. `python eval/make_split.py` (stratified by tag, seed 42, 30% test): **30 dev, 14 test**.
  - dev: easy 11, multi-step 6, conflicting 5, false-conflict 2, unanswerable 3, model-knows 3.
  - test: easy 4, multi-step 3, conflicting 2, false-conflict 1, unanswerable 2, model-knows 2.
- Frozen file: eval/questions.jsonl, SHA-256 `628e5b49afdb9ec551b71355aec273d302886c938a1da9f1acc620808f7de137`.
- **Rules from here:** no question is edited, added or removed. All experiments run on `--split dev` only. The test split is run once, at the end, and every wrong answer is categorized.

## C7: judge fixes; switch the eval LLM to local Ollama (2026-11-20)

No scores had been produced yet, so nothing is being compared across these changes.

- **Judge JSON:** a verdict came back as invalid JSON (`"reason": The provided ...`, missing quote). The judge now uses JSON mode (Gemini `responseMimeType`, Ollama `format: json`).
- **Judge rubric bug:** for cf07 (answerable), the system wrongly said the context had no crew sizes, and the judge graded that abstention "correct", because the rubric let the judge decide which questions were unanswerable. The judge is now told whether the documents can answer the question, and abstaining on an answerable question is "incorrect". Found by reading the verdict, which is why 10-15 verdicts will be hand-checked.
- **Provider:** the Gemini free tier returned HTTP 429, "Generate content requests per day limit exceeded on Free Tier", limit 20 (the error named model `gemini-3.6-flash` although config asks for `gemini-3.5-flash`; not investigated). One dev run needs 60 calls. Switched to Ollama `llama3.1:8b` on the local GPU (RTX 4060, 8 GB): free, unlimited, offline, reproducible. Expect weaker answers and a weaker judge than Gemini.
- **Ollama context:** `num_ctx: 8192` set explicitly; the default context would silently drop the start of the ~3k-token judge prompts.
- The few Gemini outputs already cached are keyed by provider and are not reused.

## B0: baseline on dev (2026-11-20)

`python eval/run_eval.py --split dev --name baseline` (30 questions; ollama llama3.1:8b, temperature 0, k=5, 1500/200 chunks, naive prompt). Full output: eval/results/baseline_dev.json.

**Deterministic metrics (computed by code, trustworthy):**

| Metric | Value | n |
|---|---|---|
| hit@3 | 38% | 24 |
| hit@5 | 46% | 24 |
| hit@10 | 67% | 24 |
| MRR@10 | 0.305 | 24 |
| conflict coverage@5 | 0% | 7 |
| citation hits gold | 25% | 24 |
| invalid citations | 0% | 30 |
| median LLM latency (s) | 6.0 | 30 |

**Answer quality, from hand labels** (eval/hand_labels_dev.jsonl; judge figures in brackets, see failure_log J1):

| Metric | Hand labels | (judge) |
|---|---|---|
| correct (answerable) | 10/24, 42% | (33%) |
| correct or partial | 14/24, 58% | (46%) |
| abstention accuracy | 6/6, 100% | (33%) |
| false abstention | 5/24, 21% | (0%) |
| conflict detection | 0/5, 0% | (80%) |
| false-conflict rate | 0/2, 0% | (0%) |
| stale answer | 2/5, 40% | (80%) |

- Faithfulness (judge 32%) is not reported: the judge marked clear abstentions as unfaithful, and it was not hand-labelled.
- "citation hits gold" undercounts when another chunk states the same fact (e.g. dra02 is correct but cites a chunk without the gold quote).
- Small n: 24 answerable, 6 no-answer, 5 conflicting. One question moves a rate by 4-20 points.

## C8: judge v2, validated against dev hand labels, then frozen (2026-11-20)

- **Change (evaluation only; the system's answers are the cached B0 answers, unchanged):** `--judge v2` (default) asks one narrow question per call and combines the parts in code:
  - declined: label "answers" / "unavailable" from question + answer only (no context);
  - correctness: only for answerable questions the system did not decline; the judge first writes the reference's key facts and the answer's, then compares. Declining an answerable question is "incorrect" and answering a no-answer question is "incorrect", applied by code;
  - reports a conflict: label "one_value" / "sources_differ", and code also requires the answer to state values from at least two sources;
  - stale: the judge lists which known source values the answer states; code checks whether only older ones appear;
  - faithfulness: unchanged in spirit, skipped for declined answers; still not hand-labelled.
  - `--judge v1` keeps the single-prompt judge so B0 stays reproducible.
- **Iterations (limit set in advance: initial v2 plus at most two revisions, then freeze):**

| Field (agreement with 30 hand labels) | v1 | v2 initial | rev 1 | rev 2 (frozen) |
|---|---|---|---|---|
| declined | 21/30 | 14/30 | 30/30 | 30/30 |
| correctness | 23/30 | 19/30 | 24/30 | 25/30 |
| reports a conflict | 26/30 | 26/30 | 28/30 | 30/30 |
| stale | 28/30 | 28/30 | 28/30 | 30/30 |

  - v2 initial asked "does the answer say the documents do NOT contain...": the negation made llama3.1:8b say "declined" for plain answers (e.g. rm04 "each reactor can produce 160 kWe"). Rev 1 replaced yes/no questions with named labels. Rev 1 still graded dra01 (160 kWe vs reference 30 kWe) "correct"; rev 2 makes the judge write both sets of facts before comparing. Rev 2 also fixed two code bugs: stale and conflict fields were computed for declined answers.
  - Remaining correctness disagreements (dra03, emc02, fc01, rm03, rm04): the judge says "partial" where hand labels say incorrect (1) or correct (4).
- **Caveat:** the judge was revised while looking at dev labels, so dev agreement overstates it. Before the test run, the test answers will be hand-labelled first and judge agreement on test reported separately.
- **Baseline under the frozen judge** (eval/results/baseline_j2_dev.json; retrieval rows corrected in C9): correct 25% (hand 42%), correct or partial 62% (hand 58%), abstention 100%, false abstention 21%, conflict detection 0%, false-conflict 0%, stale 40%, faithful 95% (n=19, not hand-checked). Strict "correct" is the judge's least reliable number; report "correct or partial" alongside it.

## C9: metric matching fix; retrieval strategy comparison (2026-11-20)

- **Metric bug fixed:** run_eval.py and check-style gold matching lowercased and collapsed whitespace only, while verify_gold.py also maps en-dashes, curly quotes and ligatures. The fc01 EMC quote ("...one Martian day - slightly more than 24 hours long") contains an en-dash in the PDF, so it was never counted as retrieved. run_eval.py and retrieval_eval.py now import `norm` from verify_gold.py. **B0 retrieval rows corrected:** hit@5 46% -> 50%, hit@10 67% -> 71%, MRR@10 0.305 -> 0.313, citation hits gold 25% -> 29%. Hit@3 (38%), coverage (0/7) and all answer-quality numbers are unchanged.
- **Retrieval-only comparison on dev** (`python eval/retrieval_eval.py --split dev`, no LLM; 24 answerable, 7 conflict/trap questions). Every strategy tried is listed:

| Strategy | n | hit@n | MRR@n | coverage@n |
|---|---|---|---|---|
| topk (baseline) | 5 | 12/24 | 0.286 | 0/7 |
| per_study | 5 | 5/24 | 0.188 | 0/7 |
| per_doc | 5 | 8/24 | 0.236 | 0/7 |
| bm25 | 5 | 13/24 | 0.324 | 0/7 |
| hybrid (RRF) | 5 | 13/24 | 0.312 | 0/7 |
| rerank | 5 | 16/24 | 0.436 | 2/7 |
| hybrid_rerank | 5 | 17/24 | 0.449 | 1/7 |
| hybrid_rerank_diverse | 5 | 17/24 | 0.451 | 1/7 |
| study_pool_rerank | 5 | 17/24 | 0.478 | 2/7 |
| topk (baseline) | 8 | 15/24 | 0.304 | 0/7 |
| per_study | 8 | 9/24 | 0.257 | 0/7 |
| per_doc | 8 | 8/24 | 0.236 | 0/7 |
| bm25 | 8 | 15/24 | 0.337 | 0/7 |
| hybrid (RRF) | 8 | 16/24 | 0.330 | 0/7 |
| rerank | 8 | 16/24 | 0.436 | 2/7 |
| hybrid_rerank | 8 | 18/24 | 0.454 | 2/7 |
| hybrid_rerank_diverse | 8 | 18/24 | 0.456 | 1/7 |
| study_pool_rerank | 8 | 17/24 | 0.478 | 3/7 |

- **Reading:** forcing study balance without reranking hurts (per_study 5/24); the cross-encoder reranker (BAAI/bge-reranker-base, pinned revision 2cfc18c...) gives the large gain. Among reranking variants the differences are 1-2 questions, within noise for n=24 and n=7. The last two variants were added after seeing the first results; no further variants will be tried on dev.
- **Why coverage stays low:** with plain embeddings the second side of each conflict ranks 10-91 of 972 (cf01 EMC side 36, cf06 NTR side 82, cf07 EMC side 71).
- **Chosen for E1:** study_pool_rerank at the baseline's k=5, so the only change is retrieval.
- New dependency: rank-bm25==0.2.2. The reranker runs on CPU (the installed torch is a CPU build), roughly 5-10 s per query.

## E1: study_pool_rerank retrieval, everything else as B0 (2026-11-20)

`python eval/run_eval.py --split dev --name e1_studypool --retrieval study_pool_rerank` (judge v2, naive prompt, k=5). Results: eval/results/e1_studypool_dev.json.

| Metric | B0 (topk) | E1 (study_pool_rerank) |
|---|---|---|
| hit@3 | 38% | 50% |
| hit@5 | 50% | 71% |
| MRR@10 | 0.313 | 0.478 |
| conflict coverage@5 | 0/7 | 2/7 |
| correct (answerable, judge) | 25% | 42% |
| correct or partial (judge) | 62% | 79% |
| citation hits gold | 29% | 50% |
| false abstention | 21% | 12% |
| abstention accuracy | 100% | 100% |
| conflict detection | 0/5 | 0/5 |
| false-conflict rate | 0/2 | 0/2 |
| stale answer | 2/5 | 2/5 |
| faithful (judge, not hand-checked) | 95% (n=19) | 86% (n=21) |
| median LLM latency | 6.0 s | 5.5 s (plus ~5-10 s CPU reranking) |

- **Hand check:** all 6 questions whose correctness or decline verdict changed from B0 were read: dra08, dra09, emc03, fc01 now correct; cf04 partial and stale (gives only the 1997 book's mid-November 2009); emc01 still incorrect. All 6 verdicts agree with a hand reading.
- **F4 persists:** emc01 now answers with the 1997 book's MAV specific impulse (379 s) instead of the EMC's 360 s. Better retrieval alone does not stop era mixing.
- **Conflict detection stays 0/5:** even when both sides are retrieved (cf01, cf04), the naive prompt does not ask the model to compare sources.
- **Decision:** keep study_pool_rerank as the retrieval for the next experiments.

## E2: conflict-aware prompt on top of E1 (2026-11-20) - rejected

`python eval/run_eval.py --split dev --name e2_conflictprompt --retrieval study_pool_rerank --prompt conflict`. Only change from E1: the prompt (generate.py PROMPT_CONFLICT: shows study label and year, asks for "Source [n] (study, year) says X", unit/configuration check, label warning).

| Metric | E1 | E2 |
|---|---|---|
| correct (answerable, judge) | 42% | 17% |
| correct or partial (judge) | 79% | 71% |
| citation hits gold | 50% | 62% |
| invalid citations | 0% | 3% |
| conflict detection (judge / hand) | 0/5 / 0/5 | 1/5 / 1/5 (rm02) |
| false-conflict rate (judge / hand) | 0/2 / 0/2 | 2/2 / 1/2 (fc03) |
| stale answer (judge) | 2/5 | 3/5 |
| faithful (judge, not hand-checked) | 86% | 71% |

- **Hand reading of all conflict, trap and regressed answers:** llama3.1:8b applies the answer format to every question and ends with "The sources differ." even when all sources agree (cf01 lists four sources saying "6") or when the second source is about something else (emc03, rm05, dra02, emc05). It also copies "study" literally ("Source [1] (study, 1997)").
- **Judge disagreement:** fc01's answer says the sources "differ in units: one study uses days, the other uses sols", which is the desired behavior; the judge's label rule counts it as a false conflict. Hand: 1/2 false conflicts (fc03 says the two papers "have different information" about a crew of six).
- **Decision:** rejected. A single instruction-heavy prompt does not work with an 8B model: it raises conflict reporting by one question and creates false conflicts in many others. Next: compare claims in code instead of asking the model to judge disagreement (E3). The prompt will not be tuned further on dev.
