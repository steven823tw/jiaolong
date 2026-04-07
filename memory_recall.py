# -*- coding: utf-8 -*-
"""
jiaolong记忆召回增强 - Memory Recall Enhancement
> 版本: v1.0 | 2026-04-02
> 对应: Claude Code extractMemories 召回机制
> 用途: 每次对话自动召回相关记忆，注入上下文
"""
from __future__ import annotations
import json, re
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace"))
MEMORY_DIR = WORKSPACE / "memory"
HOT_FILE = MEMORY_DIR / "memory_hot.json"
WARM_DIR = MEMORY_DIR / "memory_warm"


# ─────────────────────────────────────────────────────────────────────────────
# 记忆检索器
# ─────────────────────────────────────────────────────────────────────────────

class MemoryRetriever:
    """
    记忆检索器 - 根据当前对话上下文召回相关记忆
    """

    # 记忆类别优先级
    CATEGORY_PRIORITY = {
        "decision": 1.5,
        "preference": 1.3,
        "project": 1.2,
        "goal": 1.2,
        "context": 1.0,
        "knowledge": 0.9,
        "behavior": 0.8,
        "feedback": 0.8,
        "investment": 0.7,
    }

    def __init__(self, top_k: int = 10):
        self.top_k = top_k

    def retrieve(self, query: str, session_history: List[dict] = None,
                 category_filter: str = None,
                 hours_back: int = 168) -> List[dict]:
        """
        召回与当前上下文相关的记忆

        Args:
            query: 当前对话主题
            session_history: 最近会话历史（可选）
            category_filter: 只召回特定category
            hours_back: 只召回最近N小时的记忆（默认7天=168h）

        Returns:
            List[dict] - 召回的记忆列表，按相关性排序
        """
        facts = self._load_facts(hours_back=hours_back)
        if not facts:
            return []

        # 1. 查询关键词匹配
        scored = []
        query_lower = query.lower()
        query_words = set(re.findall(r"[\u4e00-\u9fa5]{2,}|\w+", query_lower))

        for fact in facts:
            score = 0.0
            content = fact.get("content", "").lower()
            cat = fact.get("category", "context")

            # 类别权重
            cat_weight = self.CATEGORY_PRIORITY.get(cat, 1.0)

            # 关键词精确匹配
            content_words = set(re.findall(r"[\u4e00-\u9fa5]{2,}|\w+", content))
            exact_matches = query_words & content_words
            score += len(exact_matches) * 2.0 * cat_weight

            # 模糊匹配（包含）
            for qw in query_words:
                if qw in content:
                    score += 0.5 * cat_weight

            # 完整短语匹配
            if query_lower in content:
                score += 3.0 * cat_weight

            # 类别奖励
            if category_filter and cat == category_filter:
                score += 1.0

            # 置信度奖励
            score += fact.get("confidence", 0.5) * 0.5

            # 时效性衰减（越新越好）
            age_hours = self._get_age_hours(fact)
            age_factor = max(0.3, 1.0 - (age_hours / (168 * 4)))  # 4周后衰减到0.3
            score *= age_factor

            if score > 0:
                scored.append((score, fact))

        # 排序并去重
        scored.sort(key=lambda x: -x[0])
        unique = []
        seen_content = set()
        for score, fact in scored:
            content_key = fact.get("content", "")[:30].lower()
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique.append({**fact, "_relevance_score": round(score, 3)})

        return unique[:self.top_k]

    def _load_facts(self, hours_back: int = 168) -> List[dict]:
        """加载记忆（支持OMLX三层）"""
        facts = []

        # 1. 热层
        try:
            with open(HOT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            facts.extend(data.get("facts", []) if isinstance(data, dict) else data)
        except Exception:
            pass

        # 2. 温层（最近月份）
        try:
            if WARM_DIR.exists():
                recent_months = sorted(WARM_DIR.glob("*/*"))[-2:]  # 最近2个月
                for month_dir in recent_months:
                    for fact_file in month_dir.glob("*.json"):
                        try:
                            facts.extend(json.loads(fact_file.read_text(encoding="utf-8")))
                        except Exception:
                            pass
        except Exception:
            pass

        # 过滤时间
        cutoff = datetime.now() - timedelta(hours=hours_back)
        filtered = []
        for f in facts:
            created = f.get("createdAt", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if dt.tzinfo:
                        dt = dt.replace(tzinfo=None)
                    if dt >= cutoff:
                        filtered.append(f)
                except Exception:
                    filtered.append(f)
            else:
                filtered.append(f)

        return filtered

    def _get_age_hours(self, fact: dict) -> float:
        """计算记忆年龄（小时）"""
        created = fact.get("createdAt", "")
        if not created:
            return 999
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if dt.tzinfo:
                dt = dt.replace(tzinfo=None)
            delta = datetime.now() - dt
            return delta.total_seconds() / 3600
        except Exception:
            return 999


# ─────────────────────────────────────────────────────────────────────────────
# 记忆注入器
# ─────────────────────────────────────────────────────────────────────────────

class MemoryInjector:
    """
    记忆注入器 - 将召回的记忆格式化为上下文字符串
    """

    def __init__(self, top_k: int = 10):
        self.retriever = MemoryRetriever(top_k=top_k)
        self._top_k = top_k

    def build_context_prompt(self, query: str,
                            session_history: List[dict] = None,
                            max_memories: int = 10) -> str:
        """
        构建记忆上下文提示

        Returns:
            格式化的记忆上下文字符串，可直接注入system prompt
        """
        if max_memories != self._top_k:
            self.retriever = MemoryRetriever(top_k=max_memories)
            self._top_k = max_memories
        memories = self.retriever.retrieve(query, session_history)
        if not memories:
            return ""

        lines = ["\n\n## 相关记忆（Relevant Memories）"]
        lines.append(f"（基于当前对话自动召回 {len(memories)} 条相关记忆）\n")

        for i, m in enumerate(memories, 1):
            cat = m.get("category", "?")
            conf = m.get("confidence", 0)
            content = m.get("content", "")
            score = m.get("_relevance_score", 0)
            source = m.get("source", "")
            created = m.get("createdAt", "")[:10] if m.get("createdAt") else ""

            # 类别emoji
            cat_emoji = {
                "decision": "🎯",
                "preference": "💡",
                "project": "📋",
                "goal": "🎯",
                "context": "📎",
                "knowledge": "📚",
                "behavior": "🔄",
                "feedback": "💬",
                "investment": "💰",
            }.get(cat, "📝")

            lines.append(f"{i}. {cat_emoji} [{cat}] (置信{conf:.0%} | 相关度{score:.1f})")
            lines.append(f"   {content}")
            if source:
                lines.append(f"   来源: {source}")
            if created:
                lines.append(f"   时间: {created}")

        lines.append("\n---\n提示: 上述记忆来自历史交互，如有相关请参考。")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 快速召回函数
# ─────────────────────────────────────────────────────────────────────────────

def recall_memories(query: str, top_k: int = 10, hours_back: int = 168) -> List[dict]:
    """快速召回记忆（CLI入口）"""
    retriever = MemoryRetriever(top_k=top_k)
    memories = retriever.retrieve(query, hours_back=hours_back)
    return memories


def inject_memory_context(query: str, session_history: List[dict] = None) -> str:
    """注入记忆上下文到prompt（CLI入口）"""
    injector = MemoryInjector()
    return injector.build_context_prompt(query, session_history)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    print("=== 记忆召回增强验证 ===")

    injector = MemoryInjector()
    retriever = MemoryRetriever(top_k=5)

    # 测试召回
    test_queries = [
        "jiaolong",
        "COCO",
        "量化",
        "进化",
        "记忆",
    ]

    for q in test_queries:
        memories = retriever.retrieve(q)
        print(f"\n召回 '{q}': {len(memories)} 条")
        for m in memories[:3]:
            print(f"  [{m.get('category', '?')}] {m.get('content', '')[:50]}... (score={m.get('_relevance_score', 0):.1f})")

    # 测试上下文注入
    print("\n--- 上下文注入 ---")
    inj = MemoryInjector(top_k=5)
    context = inj.build_context_prompt("COCO开发")
    if context:
        print(context[:500])
    else:
        print("(无相关记忆)")

    print("\n✅ 记忆召回验证完成")
