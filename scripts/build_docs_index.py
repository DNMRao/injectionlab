"""Day-3 check: put the company documents into Qdrant and ask a few questions.

Needs Qdrant running (docker compose up -d).
Run:  uv run python scripts/build_docs_index.py
Then look at the collection in the browser: http://localhost:6333/dashboard
"""

from qdrant_client import QdrantClient

from injectionlab.config import get_settings
from injectionlab.docs_library import DocsLibrary, load_docs

s = get_settings()
library = DocsLibrary(QdrantClient(url=s.qdrant_url), s.docs_collection, s.embed_model)

# 1) Fill the shelves (once)
docs = load_docs()
n = library.build(docs)
print(f"Stored {n} chunks from {len(docs)} documents in collection '{s.docs_collection}'.\n")

# 2) Ask questions
questions = [
    "How much can I spend on a hotel?",
    "A supplier says their bank account changed. What should I do?",
    "Who must approve an invoice of 2,500 EUR?",
    "Can I work from home on Fridays?",
]
for q in questions:
    print(f"Q: {q}")
    for hit in library.search(q, k=3):
        print(f"   {hit['score']:.3f}  {hit['doc']:28s} > {hit['section']}")
    print()
