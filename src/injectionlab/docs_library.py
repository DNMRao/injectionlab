"""The company document library: chunk -> embed -> store in Qdrant -> search.

`DocsLibrary` is the librarian. `build()` puts the documents on the shelves once
(chunks + vectors in Qdrant); `search()` finds the chunks closest in meaning to a
question; `read_doc()` returns a whole document.

Pure Python, no MCP here (same idea as workspace.py). The MCP server
(mcp_servers/docs_server.py) is a thin layer on top.
"""

from pathlib import Path

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

DOCS_DIR = Path(__file__).resolve().parents[2] / "data" / "docs"


# ------------------------------------------------------------ 1) load + chunk
def load_docs(docs_dir: str | Path = DOCS_DIR) -> dict[str, str]:
    """All markdown files in a folder: {file name: text}."""
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(Path(docs_dir).glob("*.md"))}


def chunk_markdown(name: str, text: str) -> list[dict]:
    """Split one document at its '## ' headings: one chunk per section.

    A document without '## ' headings becomes a single chunk.
    """
    title = name
    sections: list[tuple[str, list[str]]] = []  # (heading, lines of that section)
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append(line)

    if not sections:  # no headings: the whole text is one chunk
        body = "\n".join(x for x in text.splitlines() if not x.startswith("# ")).strip()
        sections = [("(whole document)", body.splitlines())]

    chunks = []
    for heading, lines in sections:
        body = "\n".join(lines).strip()
        if body:
            chunks.append(
                {"doc": name, "title": title, "section": heading, "pos": len(chunks), "text": body}
            )
    return chunks


# ------------------------------------------------------------ 2) the librarian
class DocsLibrary:
    def __init__(self, client: QdrantClient, collection: str, model_name: str):
        self.client = client
        self.collection = collection
        self.model = TextEmbedding(model_name)

    @staticmethod
    def _embed_text(chunk: dict) -> str:
        """What the model sees: title and heading give the short section its context."""
        return f"{chunk['title']} - {chunk['section']}\n{chunk['text']}"

    def build(self, docs: dict[str, str]) -> int:
        """(Re)create the collection from the documents. Returns the number of chunks."""
        chunks = [c for name, text in docs.items() for c in chunk_markdown(name, text)]
        vectors = list(self.model.embed([self._embed_text(c) for c in chunks]))

        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            self.collection,
            vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE),
        )
        self.client.upsert(
            self.collection,
            points=[
                models.PointStruct(id=i, vector=v.tolist(), payload=c)
                for i, (c, v) in enumerate(zip(chunks, vectors))
            ],
        )
        return len(chunks)

    def search(self, query: str, k: int = 3) -> list[dict]:
        """The k chunks closest in meaning to the query, best first."""
        q_vec = next(iter(self.model.query_embed(query)))
        hits = self.client.query_points(
            self.collection, query=q_vec.tolist(), limit=k, with_payload=True
        ).points
        return [
            {"score": round(h.score, 3), "doc": h.payload["doc"], "title": h.payload["title"],
             "section": h.payload["section"], "text": h.payload["text"]}
            for h in hits
        ]

    def _all_chunks(self) -> list[dict]:
        points, _ = self.client.scroll(self.collection, limit=10_000, with_payload=True)
        return [p.payload for p in points]

    def list_docs(self) -> list[dict]:
        """One entry per document: file name and title."""
        seen = {c["doc"]: c["title"] for c in self._all_chunks()}
        return [{"doc": d, "title": t} for d, t in sorted(seen.items())]

    def read_doc(self, name: str) -> str:
        """A whole document, rebuilt from its chunks in the original order."""
        chunks = sorted((c for c in self._all_chunks() if c["doc"] == name), key=lambda c: c["pos"])
        if not chunks:
            return f"Error: no document named '{name}'."
        parts = [f"# {chunks[0]['title']}"]
        parts += [f"## {c['section']}\n{c['text']}" for c in chunks]
        return "\n\n".join(parts)
