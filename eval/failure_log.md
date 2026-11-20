# Failure log

Record each failure when it happens, with the evidence. Do not fix an entry until it can be tested on the dev set.

## F1: DRA 5.0 crew size is not retrieved (2026-11-19)

- **Query:** "How many crew members does DRA 5.0 plan for?"
- **Gold passage:** 20090040343, PDF page 7: "...envisions sending six crewmembers to Mars..."
- **Result:** the gold chunk (20090040343_0027) ranks 41 of 816, distance 0.381. It is not in the top 20.
- **Top results instead:** chunks from the 2015 comparison paper (20160006315) and the Phobos-Deimos paper (20110005558), which mention DRA 5.0 but do not state the crew size in this passage.
  - *Correction (2026-11-20):* the rank-1 chunk (20160006315, p.5-6, distance 0.243) **does** state it: "a crew of six transfers to Mars" (verified with find.py, PDF page 5). The answer is retrievable, but only from a 2015 secondary source that describes DRA 5.0; the primary source is still rank 41. The baseline generate.py run (gemini-3.5-flash, k=5) answered "six" and cited this chunk.
  - *Implication for eval:* gold for this question should list both passages, tagged primary and secondary, so hit rate is not understated and the citation source type can be checked separately.
- **Observations:**
  - The gold chunk is 1,472 characters and the answer sentence sits in the middle, after unrelated text about science outcrops.
  - The question says "crew members"; the document says "crewmembers".
  - Many documents in the corpus mention "DRA 5.0".
- **Hypotheses (untested):** (1) the chunk's embedding is diluted by mixed content; (2) the wording mismatch hurts dense retrieval; (3) "DRA 5.0" in the query pulls in documents that only mention it.
- **Implication for abstention:** the correct chunk (0.381) is farther from the question than the best chunk for an off-topic question (Perseverance landing, 0.363), so a top-1 distance cutoff cannot be the abstention rule.
- **Status:** unfixed. To be tested as single-change experiments on the dev set: smaller chunks, keyword search alongside vector search, reranking.

## F2: ingest.py deleted table numbers (2026-11-20, fixed)

- **Evidence:** 20160006315 PDF page 11, Table 1 "Comparison of Mars Studies", Crew Size row reads 6 (DRA 5.0), 4 (EMC Split), 4 (EMC Hybrid), "4 (2 to surface for short stay)" (JPL), 2 (Inspiration Mars), "4 every 2 years" (Mars One). The cleaned text kept only `Crew Size / 4 (2 to surface for short stay) / 4 every 2 years`, so the first number after "Crew Size" was 4, which reads as if DRA 5.0 planned four crew.
- **Cause:** two filters. (1) The bare-page-number regex dropped every digits-only line anywhere on the page: 1,761 lines in the corpus, 1,277 of them mid-page. (2) The repeated-header filter replaces digits with `#`, so every bare number became `#`, which appears on most pages and was removed as a "header".
- **Fix:** (1) the page-number regex now applies only to the first 2 and last 2 lines of a page; (2) the header filter only counts lines that contain a letter. After the fix the row reads `Crew Size / 6 / 4 / 4 / 4 (2 to surface for short stay) / 2 / 4 every 2 years`, and the page number "11" is still removed. 36 bare-number lines remain at page edges (not inspected).
- **Remaining limitation:** tables are extracted one cell per line, so a value is not explicitly tied to its column. "6" follows "Crew Size" but the link to "Mars DRA 5.0" is only positional.
- **Before/after:** see eval/changes.md, C1.

## R1: document-level study label misattributes passages (risk, 2026-11-20)

Not yet a wrong answer; logged because the conflict module will depend on it.

- **Evidence:** in the baseline run for "How many crew members does DRA 5.0 plan for?", the cited chunk is labelled `EMC, 2015` (from data/metadata.csv), but the passage describes DRA 5.0: "a crew of six transfers to Mars" (20160006315, PDF page 5). EMC's own steady state is four crew (20140016934, PDF pages 1-2).
- **Risk:** a conflict module that trusts the `study` field would report "EMC (2015) says six crew", which is false. The same applies to 19980218778, which holds both Version 1.0 and Version 3.0 text under one label (`RM 3.0`), and to 19980037039, labelled `RM 1.0` although the book never uses that phrase.
- **Implication:** the study a claim belongs to must be read from the passage text; the file-level label only says who published the document and when.
- **Status:** open. Address when building the conflict module.
