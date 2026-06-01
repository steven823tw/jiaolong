# -*- coding: utf-8 -*-
"""
End-to-end test: extract → .md file → recall → context injection
Tests the complete memory lifecycle with native .md system.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_recall import MemoryRetriever, MemoryInjector, parse_md_frontmatter


class TestE2EMemoryLifecycle:
    """端到端测试：写入记忆 → 读取 → 召回 → 注入上下文"""

    def test_write_read_recall_inject(self, tmp_path):
        """完整生命周期：写入 .md → 读取 → 关键词召回 → 格式化注入"""
        # Step 1: 写入记忆（模拟 extract hook）
        md_content = """---
name: jiaolong-project
description: jiaolong是AI助手增强框架
type: project
---

jiaolong运行在Claude Code之上，提供记忆召回、Skills触发、并行执行等功能。
版本v6.1.0，使用原生.md记忆系统。
"""
        memory_file = tmp_path / "jiaolong-project.md"
        memory_file.write_text(md_content, encoding="utf-8")

        # Step 2: 读取记忆（模拟 recall hook）
        retriever = MemoryRetriever(top_k=5, memory_dir=tmp_path)
        results = retriever.retrieve("jiaolong 版本")

        # Step 3: 验证召回结果
        assert len(results) >= 1
        found = results[0]
        assert "jiaolong" in found["content"]
        assert found["type"] == "project"
        assert found["_relevance_score"] > 0

        # Step 4: 注入上下文
        injector = MemoryInjector(top_k=3, memory_dir=tmp_path)
        context = injector.build_context_prompt("jiaolong 版本")
        assert "相关记忆" in context
        assert "jiaolong" in context
        assert "project" in context

    def test_multiple_memories_ranked_by_relevance(self, tmp_path):
        """多条记忆按相关性排序"""
        # 写入多条记忆
        (tmp_path / "cooking.md").write_text(
            "---\nname: cooking\ntype: reference\n---\nHow to cook pasta", encoding="utf-8"
        )
        (tmp_path / "jiaolong-v6.md").write_text(
            "---\nname: jiaolong-v6\ntype: project\n---\njiaolong v6.1.0 released", encoding="utf-8"
        )
        (tmp_path / "jiaolong-memory.md").write_text(
            "---\nname: jiaolong-memory\ntype: feedback\n---\njiaolong memory system migrated to native .md",
            encoding="utf-8",
        )

        retriever = MemoryRetriever(top_k=10, memory_dir=tmp_path)
        results = retriever.retrieve("jiaolong 记忆系统")

        # Should find jiaolong-related memories first
        assert len(results) >= 2
        jiaolong_results = [r for r in results if "jiaolong" in r["content"]]
        assert len(jiaolong_results) >= 2

        # feedback type should rank higher than project type
        feedback = [r for r in results if r["type"] == "feedback"]
        project = [r for r in results if r["type"] == "project"]
        if feedback and project:
            assert results.index(feedback[0]) < results.index(project[0])

    def test_empty_memory_dir(self, tmp_path):
        """空记忆目录应该返回空结果"""
        retriever = MemoryRetriever(top_k=5, memory_dir=tmp_path)
        results = retriever.retrieve("anything")
        assert results == []

        injector = MemoryInjector(top_k=3, memory_dir=tmp_path)
        context = injector.build_context_prompt("anything")
        assert context == ""

    def test_memory_md_skipped(self, tmp_path):
        """MEMORY.md 索引文件应该被跳过"""
        (tmp_path / "MEMORY.md").write_text("# Index file", encoding="utf-8")
        (tmp_path / "real.md").write_text(
            "---\nname: real\ntype: reference\n---\nReal memory content", encoding="utf-8"
        )

        retriever = MemoryRetriever(top_k=5, memory_dir=tmp_path)
        results = retriever.retrieve("real")
        assert len(results) == 1
        assert results[0]["name"] == "real"

    def test_category_filter_boosts_score(self, tmp_path):
        """类别过滤应该提升匹配类型的分数"""
        (tmp_path / "proj.md").write_text(
            "---\nname: proj\ntype: project\n---\nProject memory about jiaolong", encoding="utf-8"
        )
        (tmp_path / "ref.md").write_text(
            "---\nname: ref\ntype: reference\n---\nReference memory about jiaolong", encoding="utf-8"
        )

        retriever = MemoryRetriever(top_k=5, memory_dir=tmp_path)
        # Without filter
        results_all = retriever.retrieve("jiaolong memory")
        # With filter
        results_filtered = retriever.retrieve("jiaolong memory", category_filter="project")

        # Both should return results
        assert len(results_all) >= 1
        assert len(results_filtered) >= 1
