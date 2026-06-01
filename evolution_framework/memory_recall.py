# -*- coding: utf-8 -*-
"""
jiaolong记忆召回增强 - Memory Recall Enhancement
> 版本: v6.1.0 | 2026-06-01
> 对应: Claude Code 原生记忆系统 (~/.claude/projects/{project}/memory/*.md)
> 用途: 每次对话自动召回相关记忆，注入上下文
>
> v6.1.0: 从 memory_hot.json 迁移到原生 .md 文件系统
"""
from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import os

HOME = Path.home()
CLAUDE_PROJECTS = HOME / ".claude" / "projects"

# 原生记忆类型 → 类别权重映射
TYPE_WEIGHTS = {
    "feedback": 1.5,    # 反馈类记忆最重要
    "user": 1.3,        # 用户偏好
    "project": 1.2,     # 项目相关
    "reference": 1.0,   # 参考资料
}


def get_project_memory_dir(cwd: str = None) -> Path:
    """根据 cwd 推断 Claude Code 项目记忆目录

    Claude Code 将记忆存储在 ~/.claude/projects/{project}/memory/
    其中 project 是 cwd 路径的编码（:→--, \→--）
    注意: 项目记忆在 workspace 根目录，不是子目录
    """
    if not cwd:
        cwd = os.getcwd()
    # 尝试从 cwd 向上查找包含 .claude 的 workspace 根目录
    path = Path(cwd)
    for parent in [path] + list(path.parents):
        project_name = str(parent).replace(":\\", "--").replace("\\", "--").replace(":", "--").rstrip("-")
        memory_dir = CLAUDE_PROJECTS / project_name / "memory"
        if memory_dir.exists() and any(memory_dir.glob("*.md")):
            return memory_dir
    # 回退: 使用 cwd 本身
    project_name = cwd.replace(":\\", "--").replace("\\", "--").replace(":", "--").rstrip("-")
    return CLAUDE_PROJECTS / project_name / "memory"


def parse_md_frontmatter(content: str) -> dict:
    """解析 .md 文件的 YAML frontmatter"""
    result = {"name": "", "description": "", "type": "reference", "body": ""}
    if not content.startswith("---"):
        result["body"] = content
        return result

    parts = content.split("---", 2)
    if len(parts) >= 3:
        frontmatter = parts[1].strip()
        result["body"] = parts[2].strip()

        for line in frontmatter.split("\n"):
            line = line.strip()
            if line.startswith("name:"):
                result["name"] = line[5:].strip().strip('"').strip("'")
            elif line.startswith("description:"):
                result["description"] = line[12:].strip().strip('"').strip("'")
            elif line.startswith("type:"):
                result["type"] = line[5:].strip().strip('"').strip("'")
    else:
        result["body"] = content

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 记忆检索器
# ─────────────────────────────────────────────────────────────────────────────

class MemoryRetriever:
    """
    记忆检索器 - 从 Claude Code 原生 .md 记忆系统召回相关记忆
    """

    def __init__(self, top_k: int = 10, memory_dir: Path = None):
        self.top_k = top_k
        self._memory_dir = memory_dir

    def retrieve(self, query: str, session_history: List[dict] = None,
                 category_filter: str = None,
                 hours_back: int = 168) -> List[dict]:
        """
        召回与当前上下文相关的记忆

        Args:
            query: 当前对话主题
            session_history: 最近会话历史（可选）
            category_filter: 只召回特定type
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
        query_words = set(re.findall(r"[一-龥]{2,}|\w+", query_lower))

        for fact in facts:
            score = 0.0
            content = fact.get("content", "").lower()
            mem_type = fact.get("type", "reference")

            # 类别权重
            type_weight = TYPE_WEIGHTS.get(mem_type, 1.0)

            # 关键词精确匹配
            content_words = set(re.findall(r"[一-龥]{2,}|\w+", content))
            exact_matches = query_words & content_words
            score += len(exact_matches) * 2.0 * type_weight

            # 模糊匹配（包含）
            for qw in query_words:
                if qw in content:
                    score += 0.5 * type_weight

            # 完整短语匹配
            if query_lower in content:
                score += 3.0 * type_weight

            # 类别奖励
            if category_filter and mem_type == category_filter:
                score += 1.0

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
        """从 Claude Code 原生 .md 记忆文件加载记忆"""
        memory_dir = self._memory_dir or get_project_memory_dir()
        if not memory_dir.exists():
            return []

        facts = []
        cutoff = datetime.now() - timedelta(hours=hours_back)

        for md_file in memory_dir.glob("*.md"):
            if md_file.name == "MEMORY.md":
                continue  # 跳过索引文件

            try:
                raw = md_file.read_text(encoding="utf-8")
                parsed = parse_md_frontmatter(raw)

                # 获取文件修改时间作为创建时间
                mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                if mtime < cutoff:
                    continue  # 跳过太旧的记忆

                facts.append({
                    "content": parsed["body"],
                    "name": parsed["name"],
                    "description": parsed["description"],
                    "type": parsed["type"],
                    "category": parsed["type"],  # 兼容旧格式
                    "createdAt": mtime.isoformat(),
                    "source": str(md_file.name),
                    "confidence": 0.8,
                })
            except Exception:
                continue

        return facts

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

    def __init__(self, top_k: int = 10, memory_dir: Path = None):
        self.retriever = MemoryRetriever(top_k=top_k, memory_dir=memory_dir)
        self._top_k = top_k

    def build_context_prompt(self, query: str,
                            session_history: List[dict] = None,
                            max_memories: int = 10) -> str:
        """
        构建记忆上下文提示

        Returns:
            格式化的记忆上下文字符串，可直接注入system prompt
        """
        memories = self.retriever.retrieve(query, session_history)
        if not memories:
            return ""

        lines = ["## 相关记忆\n"]
        for i, mem in enumerate(memories[:max_memories], 1):
            name = mem.get("name", "unnamed")
            mem_type = mem.get("type", "reference")
            desc = mem.get("description", "")
            content = mem.get("content", "")
            score = mem.get("_relevance_score", 0)

            lines.append(f"### {i}. [{mem_type}] {name}")
            if desc:
                lines.append(f"**描述**: {desc}")
            lines.append(f"**相关度**: {score}")
            lines.append(f"**内容**: {content[:500]}")
            lines.append("")

        return "\n".join(lines)
