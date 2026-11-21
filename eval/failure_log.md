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

## F3: DRA 5.0 paper's crewed MTV IMLEO is not retrieved (2026-11-20)

- **Query:** "What is the IMLEO of the crewed Mars transfer vehicle?"
- **Gold passage:** 20090040343, PDF page 15: "The 'all-propulsive' crewed MTV has an IMLEO of 356.4 t". Appears in chunks 20090040343_0053 and _0054.
- **Result:** best gold chunk (_0053, p.14-15) ranks 155 of 818, distance 0.345. The old page-range rule had reported rank 14 because a different p.15 chunk without the sentence was retrieved (changes.md C2).
- **Related, not concluded:** 20090010571 p.36 gives "'0-gE' Crewed MTV: IMLEO ~336.5 t" (rank 2). The two figures carry different labels ("all-propulsive" vs "0-gE"), which points to different configurations rather than a design change, but this is not verified. Do not call it a conflict yet.
- **Hypotheses (untested):** same as F1 (dilution in a 1,476-character chunk; many documents mention MTV and IMLEO).
- **Status:** unfixed. Test with the retrieval experiments on dev.

## F4: answers mix eras: 1997 values given for later studies (baseline dev run, 2026-11-20)

- **dra01** "What surface power system does DRA 5.0 use, and how many kilowatts?" answered "160 kWe", citing 19980037039 p.40 (the 1997 book). DRA 5.0's figure is 30 kWe (20090012109 p.25).
- **emc01, emc06** (EMC Mars Ascent Vehicle engine): the answer says the value is not stated, then infers from the 1997 book's RL10 engines.
- **Why it matters:** this is the failure ConflictRAG exists to prevent: a confident answer built from the wrong study's passage. The baseline prompt shows no year or study, by design.
- **Status:** open; the conflict module and study-aware prompting are tested on dev.

## F5: both sides of a conflict are never retrieved together (baseline dev run, 2026-11-20)

- conflict coverage@5 = 0/7: for no conflicting or false-conflict question do the top 5 chunks contain the gold quotes from every source. The generator therefore cannot report a disagreement, and conflict detection is 0/5 (hand labels).
- **Status:** open. Retrieval across years (e.g. per-study retrieval) is the planned fix.

## J1: the local judge (llama3.1:8b) is not reliable enough to publish (2026-11-20)

- Hand-labelled all 30 dev answers (eval/hand_labels_dev.jsonl, labeler: claude). Spot-checked by the project owner on 2026-11-20: no labels changed (which IDs were checked is not recorded). Agreement with the judge: correctness 23/30, abstained 21/30, claims_disagreement 26/30, only_older_value 28/30.
- All 7 correctness disagreements are the judge being too harsh, e.g. it graded "There is no information in the provided context about the first powered helicopter flight" (mk05) as not abstaining and incorrect.
- Biggest distortions: abstention accuracy judge 33% vs hand 100%; conflict detection judge 80% vs hand 0%.
- **Rule until fixed:** report judge-based metrics only with the hand-label figures beside them, and use eval/judge_agreement.py to validate any judge change.

## G1: frozen reference for cf06 is incomplete (2026-11-20)

- cf06 "How many days does the DRA 5.0 crew spend at Mars?" The baseline answered "450-550 days", which 20160006315 states for DRA 5.0 (Table 1, PDF page 11). The frozen reference lists only ~500 and 540 days. The question file is frozen, so it is not edited; hand label for cf06 is "partial" and the gap is recorded here.

## R1: document-level study label misattributes passages (risk, 2026-11-20)

Not yet a wrong answer; logged because the conflict module will depend on it.

- **Evidence:** in the baseline run for "How many crew members does DRA 5.0 plan for?", the cited chunk is labelled `EMC, 2015` (from data/metadata.csv), but the passage describes DRA 5.0: "a crew of six transfers to Mars" (20160006315, PDF page 5). EMC's own steady state is four crew (20140016934, PDF pages 1-2).
- **Risk:** a conflict module that trusts the `study` field would report "EMC (2015) says six crew", which is false. The same applies to 19980218778, which holds both Version 1.0 and Version 3.0 text under one label (`RM 3.0`), and to 19980037039, labelled `RM 1.0` although the book never uses that phrase.
- **Implication:** the study a claim belongs to must be read from the passage text; the file-level label only says who published the document and when.
- **Status:** open. Address when building the conflict module.

## F6: conflict prompt makes the 8B model report disagreement everywhere (E2, 2026-11-20)

- With the conflict-aware prompt, answers end with "The sources differ." regardless of content: cf01 lists four sources that all say 6 crew and still concludes they differ; emc03 adds a "1 Sol Mars orbit" as a conflicting answer to an aggregation-orbit question; rm05 contrasts launch-vehicle capability with TMI stack mass.
- Strict correctness fell from 42% (E1) to 17%.
- **Implication:** whether two values conflict should be decided by code over extracted claims, not by asking the generator in one prompt.
