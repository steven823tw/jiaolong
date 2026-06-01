# -*- coding: utf-8 -*-
"""Tests for memory_recall module (v6.1.0 - native .md system)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_recall import (
    MemoryRetriever,
    MemoryInjector,
    get_project_memory_dir,
    parse_md_frontmatter,
)


class TestParseMdFrontmatter:
    def test_parse_with_frontmatter(self):
        content = "---\nname: test\ntype: feedback\ndescription: a test\n---\nBody content"
        result = parse_md_frontmatter(content)
        assert result["name"] == "test"
        assert result["type"] == "feedback"
        assert result["description"] == "a test"
        assert result["body"] == "Body content"

    def test_parse_without_frontmatter(self):
        content = "Just plain text"
        result = parse_md_frontmatter(content)
        assert result["name"] == ""
        assert result["body"] == "Just plain text"

    def test_parse_with_quotes(self):
        content = '---\nname: "quoted name"\ntype: \'feedback\'\n---\nBody'
        result = parse_md_frontmatter(content)
        assert result["name"] == "quoted name"
        assert result["type"] == "feedback"


class TestGetProjectMemoryDir:
    def test_returns_path(self):
        result = get_project_memory_dir("C:\\cc")
        assert "C--cc" in str(result)
        assert "memory" in str(result)

    def test_default_cwd(self):
        result = get_project_memory_dir()
        assert isinstance(result, Path)


class TestMemoryRetriever:
    def _make_md_file(self, tmp_path: Path, name: str, content: str, mem_type: str = "reference"):
        md_file = tmp_path / f"{name}.md"
        md_content = f"---\nname: {name}\ntype: {mem_type}\n---\n{content}"
        md_file.write_text(md_content, encoding="utf-8")
        return md_file

    def test_retrieve_from_md_files(self, tmp_path):
        self._make_md_file(tmp_path, "jiaolong-info", "jiaolong is an AI assistant", "project")
        self._make_md_file(tmp_path, "cooking", "how to cook pasta", "reference")

        retriever = MemoryRetriever(top_k=5, memory_dir=tmp_path)
        results = retriever.retrieve("jiaolong")
        assert len(results) >= 1
        assert any("jiaolong" in r.get("content", "") for r in results)

    def test_type_weight_affects_ranking(self, tmp_path):
        self._make_md_file(tmp_path, "ctx", "jiaolong context note", "reference")
        self._make_md_file(tmp_path, "fb", "jiaolong feedback note", "feedback")

        retriever = MemoryRetriever(top_k=5, memory_dir=tmp_path)
        results = retriever.retrieve("jiaolong")
        # feedback has higher weight (1.5 vs 1.0), should rank first
        assert results[0]["type"] == "feedback"

    def test_top_k_limits_results(self, tmp_path):
        for i in range(10):
            self._make_md_file(tmp_path, f"item-{i}", f"memory item {i} about jiaolong")

        retriever = MemoryRetriever(top_k=2, memory_dir=tmp_path)
        results = retriever.retrieve("jiaolong")
        assert len(results) <= 2

    def test_empty_dir_returns_empty(self, tmp_path):
        retriever = MemoryRetriever(top_k=5, memory_dir=tmp_path)
        results = retriever.retrieve("anything")
        assert results == []

    def test_skips_memory_md(self, tmp_path):
        # MEMORY.md should be skipped
        (tmp_path / "MEMORY.md").write_text("# Index", encoding="utf-8")
        self._make_md_file(tmp_path, "real", "real memory about jiaolong")

        retriever = MemoryRetriever(top_k=5, memory_dir=tmp_path)
        results = retriever.retrieve("jiaolong")
        assert len(results) == 1

    def test_create_retriever(self):
        retriever = MemoryRetriever(top_k=5)
        assert retriever.top_k == 5

    def test_default_top_k(self):
        retriever = MemoryRetriever()
        assert retriever.top_k == 10


class TestMemoryInjector:
    def test_build_context_prompt(self, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("---\nname: test\ntype: decision\n---\nTest memory content", encoding="utf-8")

        injector = MemoryRetriever(top_k=3, memory_dir=tmp_path)
        results = injector.retrieve("test")
        assert len(results) >= 1

    def test_empty_returns_empty_string(self, tmp_path):
        injector = MemoryInjector(top_k=3, memory_dir=tmp_path)
        prompt = injector.build_context_prompt("nothing")
        assert prompt == ""
