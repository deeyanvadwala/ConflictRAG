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
