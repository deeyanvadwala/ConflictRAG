"""Retrieval strategies. Each returns a list of hits (same format as retrieve.search).

    topk(q, n)        the n most similar chunks by embedding (baseline)
    per_study(q, n)   n chunks split evenly across study labels, so every era is represented
    per_doc(q, n)     the n most similar chunks, at most one per document
    hybrid(q, n)      embedding + BM25 keyword ranks, merged with reciprocal rank fusion
    rerank(q, n)      top 50 by embedding, re-scored by a cross-encoder
    hybrid_rerank     top 50 by hybrid, re-scored by a cross-encoder
"""
import re

from chunking import CFG
from retrieve import _load, search

STUDIES = ["RM 1.0", "RM 3.0", "DRA 5.0", "EMC"]   # labels in data/metadata.csv (file-level; see failure_log R1)
POOL = 50     # candidates passed to fusion / the reranker
RRF_K = 60    # standard reciprocal-rank-fusion constant

_bm25 = None
_reranker = None


def topk(query, n):
    return search(query, k=n)


def per_study(query, n):
    per = max(1, n // len(STUDIES))
    hits = []
    for s in STUDIES:
        hits += search(query, k=per, where={"study": s})
    return sorted(hits, key=lambda h: h["distance"])[:n]


def per_doc(query, n, pool=60):
    seen, hits = set(), []
    for h in search(query, k=pool):
        if h["meta"]["doc_id"] not in seen:
            seen.add(h["meta"]["doc_id"])
            hits.append(h)
        if len(hits) == n:
            break
    return hits


def _tokens(text):
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower())


def _bm25_index():
    global _bm25
    if _bm25 is None:
        from rank_bm25 import BM25Okapi
        _, col = _load()
        g = col.get(include=["documents", "metadatas"])
        _bm25 = (BM25Okapi([_tokens(t) for t in g["documents"]]), g)
    return _bm25


def bm25(query, n):
    index, g = _bm25_index()
    scores = index.get_scores(_tokens(query))
    order = sorted(range(len(scores)), key=lambda i: -scores[i])[:n]
    return [{"chunk_id": g["ids"][i], "text": g["documents"][i], "meta": g["metadatas"][i],
             "distance": None, "bm25": float(scores[i])} for i in order]


def hybrid(query, n, pool=POOL):
    fused = {}
    for ranked in (search(query, k=pool), bm25(query, pool)):
        for rank, h in enumerate(ranked, start=1):
            entry = fused.setdefault(h["chunk_id"], {**h, "rrf": 0.0})
            entry["rrf"] += 1 / (RRF_K + rank)
    return sorted(fused.values(), key=lambda h: -h["rrf"])[:n]


def _rerank(query, candidates, n):
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(CFG["reranker_model"], revision=CFG.get("reranker_revision"))
    scores = _reranker.predict([(query, h["text"]) for h in candidates])
    for h, s in zip(candidates, scores):
        h["rerank"] = float(s)
    return sorted(candidates, key=lambda h: -h["rerank"])[:n]


def rerank(query, n):
    return _rerank(query, search(query, k=POOL), n)


def hybrid_rerank(query, n):
    return _rerank(query, hybrid(query, POOL), n)


def hybrid_rerank_diverse(query, n, max_per_doc=2):
    """hybrid_rerank, but at most max_per_doc chunks from any one document."""
    ranked, out, count = _rerank(query, hybrid(query, POOL), POOL), [], {}
    for h in ranked:
        d = h["meta"]["doc_id"]
        if count.get(d, 0) < max_per_doc:
            out.append(h)
            count[d] = count.get(d, 0) + 1
        if len(out) == n:
            break
    return out


def study_pool_rerank(query, n, per=12):
    """Candidates from each study separately (embedding + BM25), then one rerank over all of them."""
    pool = {}
    _, g = _bm25_index()
    for s in STUDIES:
        for h in search(query, k=per, where={"study": s}):
            pool[h["chunk_id"]] = h
        for h in bm25(query, POOL * 4):
            if h["meta"]["study"] == s and sum(p["meta"]["study"] == s for p in pool.values()) < 2 * per:
                pool.setdefault(h["chunk_id"], h)
    return _rerank(query, list(pool.values()), n)


STRATEGIES = {"topk": topk, "per_study": per_study, "per_doc": per_doc, "bm25": bm25,
              "hybrid": hybrid, "rerank": rerank, "hybrid_rerank": hybrid_rerank,
              "hybrid_rerank_diverse": hybrid_rerank_diverse, "study_pool_rerank": study_pool_rerank}
