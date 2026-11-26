"""MCP server for the company document library (RAG over Qdrant).

A thin layer: each MCP tool calls one `DocsLibrary` method. All tools are
read-only: the library can be searched and read, never changed by the agent.
The docstrings below are what the AI model reads to decide which tool to use.

The server does NOT build the index; it searches an existing Qdrant collection
(build it first with scripts/build_docs_index.py). Which collection is used comes
from the normal settings, so the runner can point the server at a poisoned copy:

  DOCS_COLLECTION   Qdrant collection to search (default: "docs")
  QDRANT_URL        where Qdrant runs (default: http://localhost:6333)

Run by hand:  uv run python -m injectionlab.mcp_servers.docs_server
"""

import json
import logging

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from qdrant_client import QdrantClient

from injectionlab.config import get_settings
from injectionlab.docs_library import DocsLibrary

READ = ToolAnnotations(readOnlyHint=True)


def _out(value) -> str:
    """Tool results go back to the model as text; JSON keeps them exact."""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=1)


def build_server(library: DocsLibrary) -> MCPServer:
    server = MCPServer(
        name="docs",
        instructions="Search and read the company's internal documents and policies.",
    )

    @server.tool(annotations=READ)
    def search_docs(query: str, k: int = 3) -> str:
        """Search the company documents (policies, guidelines, project notes) by meaning.
        Returns the k most relevant sections (1-10, default 3), best first, with their
        document name, section heading and text."""
        k = max(1, min(k, 10))  # keep the answer small
        return _out(library.search(query, k))

    @server.tool(annotations=READ)
    def list_docs() -> str:
        """List all company documents: file name and title."""
        return _out(library.list_docs())

    @server.tool(annotations=READ)
    def read_doc(name: str) -> str:
        """Read a whole company document by its file name, e.g. 'travel_policy.md'."""
        return _out(library.read_doc(name))

    return server


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)  # hide one log line per Qdrant call
    s = get_settings()
    library = DocsLibrary(QdrantClient(url=s.qdrant_url), s.docs_collection, s.embed_model)
    build_server(library).run("stdio")


if __name__ == "__main__":
    main()
