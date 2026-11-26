"""Tests for the document library (chunking + Qdrant in memory, no Docker, no AI agent)."""

import pytest
from qdrant_client import QdrantClient

from injectionlab.docs_library import DocsLibrary, chunk_markdown, load_docs

MODEL = "BAAI/bge-small-en-v1.5"


@pytest.fixture(scope="module")
def library():
    """One library for all tests in this file: the model loads once (~2 s)."""
    lib = DocsLibrary(QdrantClient(":memory:"), "docs_test", MODEL)
    lib.build(load_docs())
    return lib


# ------------------------------------------------------------ chunking (no model needed)
def test_chunk_markdown_splits_at_sections():
    text = "# Travel policy\n\n## Booking\nBook trains.\n\n## Hotels\nUp to 150 EUR.\n"
    chunks = chunk_markdown("travel.md", text)
    assert [c["section"] for c in chunks] == ["Booking", "Hotels"]
    assert [c["pos"] for c in chunks] == [0, 1]
    assert chunks[1]["title"] == "Travel policy"
    assert chunks[1]["text"] == "Up to 150 EUR."  # empty edge lines stripped


def test_chunk_markdown_skips_empty_sections():
    chunks = chunk_markdown("x.md", "# X\n## Empty\n\n## Full\nSome text.")
    assert [c["section"] for c in chunks] == ["Full"]
    assert chunks[0]["pos"] == 0  # positions have no gaps


def test_chunk_markdown_without_headings_is_one_chunk():
    chunks = chunk_markdown("note.md", "Just a short note.\nSecond line.")
    assert len(chunks) == 1
    assert chunks[0]["title"] == "note.md"  # fallback: file name
    assert chunks[0]["text"] == "Just a short note.\nSecond line."


def test_load_docs_is_sorted_and_clean():
    docs = load_docs()
    assert len(docs) == 15
    assert list(docs) == sorted(docs)  # same order every run
    text = " ".join(docs.values()).upper()
    for canary in ("XX-666", "EVIL", "ATTACKER"):
        assert canary not in text  # canaries only exist inside attacks


# ------------------------------------------------------------ search + read
@pytest.mark.parametrize(
    ("question", "doc", "section"),
    [
        ("How much can I spend on a hotel?", "travel_policy.md", "Hotels"),
        ("A supplier says their bank account changed.", "supplier_payments.md",
         "Changed bank details"),
        ("Can I work from home?", "remote_work.md", "Working from home"),
    ],
)
def test_search_finds_the_right_section_first(library, question, doc, section):
    best = library.search(question, k=3)[0]
    assert (best["doc"], best["section"]) == (doc, section)


def test_search_returns_k_results_best_first(library):
    hits = library.search("travel", k=5)
    assert len(hits) == 5
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_list_docs_has_one_entry_per_document(library):
    docs = library.list_docs()
    assert len(docs) == 15
    assert {"doc": "travel_policy.md", "title": "Travel policy"} in docs


def test_read_doc_rebuilds_sections_in_order(library):
    text = library.read_doc("travel_policy.md")
    assert text.startswith("# Travel policy")
    assert text.index("## Booking") < text.index("## Hotels") < text.index("## Local transport")


def test_read_unknown_doc_returns_error(library):
    assert library.read_doc("nope.md").startswith("Error")


def test_rebuild_leaves_no_ghost_cards(library):
    """build() starts from an empty shelf: removed documents disappear."""
    lib = DocsLibrary(QdrantClient(":memory:"), "ghosts", MODEL)
    lib.model = library.model  # reuse the loaded model
    lib.build({"a.md": "# A\n## One\nalpha", "b.md": "# B\n## One\nbeta\n## Two\ngamma"})
    lib.build({"a.md": "# A\n## One\nalpha"})
    assert [d["doc"] for d in lib.list_docs()] == ["a.md"]
    assert lib.client.count("ghosts").count == 1
