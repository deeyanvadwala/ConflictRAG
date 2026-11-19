import sys
import chromadb
from sentence_transformers import SentenceTransformer
from chunking import CFG

_model = None
_col = None


def _load():
    global _model, _col
    if _model is None:
        _model = SentenceTransformer(CFG["embedding_model"])
        client = chromadb.PersistentClient(path=CFG["chroma_path"])
        _col = client.get_collection(CFG["collection"])
    return _model, _col


def search(query, k=None):
    """Return the top-k chunks for a query. Lower distance = closer match."""
    k = k or CFG["top_k"]
    model, col = _load()
    q = model.encode([CFG["query_prefix"] + query], normalize_embeddings=True).tolist()
    r = col.query(query_embeddings=q, n_results=k)
    return [
        {
            "chunk_id": r["ids"][0][i],
            "text": r["documents"][0][i],
            "meta": r["metadatas"][0][i],
            "distance": r["distances"][0][i],
        }
        for i in range(len(r["ids"][0]))
    ]


if __name__ == "__main__":
    # Avoid Windows console encoding errors on special characters
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    question = " ".join(sys.argv[1:])
    print(f"Query: {question}\n")
    for h in search(question):
        m = h["meta"]
        print(f"[{h['distance']:.3f}] {m['study']} {m['year']} | {m['doc_id']} p.{m['page_start']}-{m['page_end']}")
        print("    ", h["text"][:300].replace("\n", " "), "\n")
