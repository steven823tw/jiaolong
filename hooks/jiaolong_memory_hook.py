# -*- coding: utf-8 -*-
"""
jiaolong Cowork Memory Hook
> 版本: v5.0.0 | 2026-04-30
> 用途: Claude Code Stop hook - 每次对话结束时自动提取记忆

配置方式（在 ~/.claude/settings.json）：
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.claude/jiaolong/hooks/jiaolong_memory_hook.py"
          }
        ]
      }
    ]
  }
}
"""
from __future__ import annotations
import json
import sys
import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# 路径配置
# ─────────────────────────────────────────────────────────────────────────────

HOME = Path.home()
JIAOLONG_DIR = HOME / ".claude" / "jiaolong"
MEMORY_DIR = JIAOLONG_DIR / "memory"
MEMORY_HOT = MEMORY_DIR / "memory_hot.json"


def ensure_dirs():
    """确保目录存在"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def load_memories() -> dict:
    """加载热记忆"""
    if not MEMORY_HOT.exists():
        return {"facts": [], "version": "1.0"}
    try:
        with open(MEMORY_HOT, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"facts": data, "version": "1.0"}
        return data
    except Exception:
        return {"facts": [], "version": "1.0"}


def save_memories(data: dict):
    """保存热记忆"""
    ensure_dirs()
    with open(MEMORY_HOT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_keywords(message: str) -> list:
    """从消息中提取关键词"""
    import re
    # 移除标点和常见停用词
    stop_words = {
        "的", "了", "是", "在", "我", "你", "他", "她", "它",
        "这", "那", "有", "和", "与", "或", "但", "不", "也",
        "就", "都", "把", "被", "让", "给", "从", "到", "对",
        "the", "a", "an", "is", "are", "was", "were", "be",
        "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can",
        "i", "you", "he", "she", "it", "we", "they", "this",
        "that", "and", "or", "but", "not", "for", "with",
    }
    # 提取中文词和英文词
    words = re.findall(r'[一-鿿]+|[a-zA-Z]+', message.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 1]
    return list(set(keywords))


def search_memories(keywords: list, top_k: int = 5) -> list:
    """搜索相关记忆"""
    data = load_memories()
    facts = data.get("facts", [])
    if not facts:
        return []

    scored = []
    for fact in facts:
        content = json.dumps(fact, ensure_ascii=False).lower()
        score = sum(1 for kw in keywords if kw in content)
        if score > 0:
            scored.append((score, fact))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in scored[:top_k]]


def format_memory_context(memories: list) -> str:
    """格式化记忆上下文"""
    if not memories:
        return ""

    lines = ["[jiaolong 记忆召回]"]
    for i, m in enumerate(memories, 1):
        cat = m.get("category", "general")
        content = m.get("content", "")
        if isinstance(content, str):
            lines.append(f"  {i}. [{cat}] {content[:100]}")
    return "\n".join(lines)


def main():
    """
    主入口：从 stdin 读取上下文，输出记忆上下文
    Claude Code Stop hook 会调用此脚本
    """
    ensure_dirs()

    # 读取 stdin（如果有）
    context = ""
    try:
        if not sys.stdin.isatty():
            context = sys.stdin.read().strip()
    except Exception:
        pass

    # 如果没有上下文，直接退出
    if not context:
        sys.exit(0)

    # 提取关键词并搜索记忆
    keywords = extract_keywords(context)
    if not keywords:
        sys.exit(0)

    memories = search_memories(keywords)
    if memories:
        output = format_memory_context(memories)
        print(output)

    sys.exit(0)


if __name__ == "__main__":
    main()
