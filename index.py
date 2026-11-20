import collections, json
import chromadb
import sentence_transformers
from sentence_transformers import SentenceTransformer
from chunking import load_chunks, CFG

chunks = load_chunks()
print(f"{len(chunks)} chunks")

# Balance report: how many chunks come from each study and document
by_study, by_doc = collections.Counter(), collections.Counter()
for c in chunks:
    by_study[c["meta"]["study"]] += 1
    by_doc[c["meta"]["doc_id"]] += 1

print("\nChunks per study:")
for s, n in by_study.most_common():
    print(f"  {s:<10}{n:>6}  ({n / len(chunks):.0%})")

print("\nChunks per document:")
for d, n in sorted(by_doc.items()):
    print(f"  {d}  {n:>5}")

print("\nLoading embedding model (first run downloads about 130 MB)...")
model = SentenceTransformer(CFG["embedding_model"], revision=CFG["embedding_revision"])
emb = model.encode(
    [c["text"] for c in chunks],
    batch_size=32,
    normalize_embeddings=True,
    show_progress_bar=True,
)

client = chromadb.PersistentClient(path=CFG["chroma_path"])
try:
    client.delete_collection(CFG["collection"])
except Exception:
    pass
col = client.create_collection(CFG["collection"], metadata={"hnsw:space": "cosine"})

BATCH = 500
for i in range(0, len(chunks), BATCH):
    part = chunks[i:i + BATCH]
    col.add(
        ids=[c["chunk_id"] for c in part],
        documents=[c["text"] for c in part],
        metadatas=[c["meta"] for c in part],
        embeddings=emb[i:i + BATCH].tolist(),
    )

# Record settings and library versions for the README
info = {
    "embedding_model": CFG["embedding_model"],
    "embedding_revision": CFG["embedding_revision"],
    "chunk_chars": CFG["chunk_chars"],
    "chunk_overlap": CFG["chunk_overlap"],
    "n_chunks": len(chunks),
    "chromadb": chromadb.__version__,
    "sentence_transformers": sentence_transformers.__version__,
}
json.dump(info, open("index_info.json", "w"), indent=2)
print("\nIndexed.", info)
