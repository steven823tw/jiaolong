# -*- coding: utf-8 -*-
"""Tests for memory_recall module."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_recall import MemoryRetriever


# ─────────────────────────────────────────────────────────────────────────────
# MemoryRetriever
# ─────────────────────────────────────────────────────────────────────────────


class TestMemoryRetriever:
    def test_create_retriever(self):
        retriever = MemoryRetriever(top_k=5)
        assert retriever.top_k == 5

    def test_default_top_k(self):
        retriever = MemoryRetriever()
        assert retriever.top_k == 10

    def test_category_priority_weights(self):
        retriever = MemoryRetriever()
        assert "decision" in retriever.CATEGORY_PRIORITY
        assert retriever.CATEGORY_PRIORITY["decision"] == 1.5
        assert retriever.CATEGORY_PRIORITY["preference"] == 1.3

    def test_retrieve_empty_when_no_facts(self):
        retriever = MemoryRetriever()
        # When no memory file exists, should return empty list
        results = retriever.retrieve("test query")
        assert isinstance(results, list)

    def test_retrieve_returns_list(self):
        retriever = MemoryRetriever()
        results = retriever.retrieve("jiaolong", hours_back=1)
        assert isinstance(results, list)
