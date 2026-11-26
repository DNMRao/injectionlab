"""Tests for the docs MCP server (in-process client, Qdrant in memory, no AI)."""

import asyncio
import json

import pytest
from mcp import Client
from qdrant_client import QdrantClient

from injectionlab.docs_library import DocsLibrary, load_docs
from injectionlab.mcp_servers.docs_server import build_server


@pytest.fixture(scope="module")
def server():
    lib = DocsLibrary(QdrantClient(":memory:"), "docs_test", "BAAI/bge-small-en-v1.5")
    lib.build(load_docs())
    return build_server(lib)


def call(server, tool, args):
    async def go():
        async with Client(server) as client:
            return (await client.call_tool(tool, args)).content[0].text

    return asyncio.run(go())


def test_server_has_three_read_only_tools(server):
    async def go():
        async with Client(server) as client:
            return (await client.list_tools()).tools

    tools = asyncio.run(go())
    assert {t.name for t in tools} == {"search_docs", "list_docs", "read_doc"}
    for t in tools:
        assert t.description, f"{t.name} needs a description for the model"
        assert t.annotations.read_only_hint is True  # the library can never act


def test_search_docs_returns_json_hits(server):
    hits = json.loads(call(server, "search_docs", {"query": "hotel price limit", "k": 2}))
    assert len(hits) == 2
    assert hits[0]["doc"] == "travel_policy.md"


def test_search_docs_clamps_k(server):
    """The model chooses k; a huge k must not flood the context."""
    hits = json.loads(call(server, "search_docs", {"query": "policy", "k": 500}))
    assert len(hits) == 10


def test_read_doc_through_mcp(server):
    assert call(server, "read_doc", {"name": "supplier_payments.md"}).startswith(
        "# Supplier payments"
    )
