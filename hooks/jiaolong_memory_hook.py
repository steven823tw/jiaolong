# -*- coding: utf-8 -*-
"""
jiaolong → Claude Code Native Memory Recall Hook
> 版本: v6.0.0 | 2026-05-29
> 用途: Claude Code Stop hook - 从原生记忆系统召回相关记忆，注入上下文

进化点:
- 放弃 memory_hot.json，从 ~/.claude/projects/{project}/memory/*.md 读取
- 关键词匹配 + 类别权重 + 时间衰减
- 输出格式遵循 Claude Code 系统提示风格
"""
from __future__ import annotations
import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# 路径配置
# ─────────────────────────────────────────────────────────────────────────────

HOME = Path.home()
CLAUDE_PROJECTS = HOME / ".claude" / "projects"


def _sanitize(text: str) -> str:
    """Remove lone surrogates that break UTF-8 JSON serialization."""
    return text.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")


def get_project_memory_dir(cwd: str) -> Path:
    """根据 cwd 推断 Claude Code 项目记忆目录"""
    if not cwd:
        cwd = os.getcwd()
    project_name = cwd.replace(":\\", "--").replace("\\", "--").replace(":", "--")
    project_name = project_name.rstrip("-")
    return CLAUDE_PROJECTS / project_name / "memory"


def parse_hook_input(raw: str) -> dict:
    """Parse Claude Code hook JSON stdin."""
    try:
        data = json.loads(raw, strict=False)
        return {
            "session_id": data.get("session_id", ""),
            "tool_name": data.get("tool_name", ""),
            "cwd": data.get("cwd", ""),
            "tool_input": data.get("tool_input", {}),
            "hook_event_name": data.get("hook_event_name", ""),
        }
    except (json.JSONDecodeError, TypeError):
        return {"raw_text": raw}


# ─────────────────────────────────────────────────────────────────────────────
# 原生记忆读取
# ─────────────────────────────────────────────────────────────────────────────

def load_native_memories(memory_dir: Path) -> list:
    """从原生 .md 记忆文件加载所有记忆"""
    memories = []
    if not memory_dir.exists():
        return memories

    for md_file in memory_dir.glob("*.md"):
        if md_file.name == "MEMORY.md":
            continue  # 跳过索引文件

        try:
            content = md_file.read_text(encoding="utf-8")
            # 解析 frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    body = parts[2].strip()

                    # 提取字段
                    name = ""
                    description = ""
                    mem_type = "reference"
                    for line in frontmatter.split("\n"):
                        line = line.strip()
                        if line.startswith("name:"):
                            name = line[5:].strip()
                        elif line.startswith("description:"):
                            description = line[12:].strip()
                        elif line.startswith("type:"):
                            mem_type = line[5:].strip()

                    memories.append({
                        "name": name,
                        "description": description,
                        "type": mem_type,
                        "body": body,
                        "file": md_file.name,
                    })
        except Exception:
            continue

    return memories


# ─────────────────────────────────────────────────────────────────────────────
# 关键词提取与匹配
# ─────────────────────────────────────────────────────────────────────────────

STOP_WORDS = {
    "的", "了", "是", "在", "我", "你", "他", "她", "它",
    "这", "那", "有", "和", "与", "或", "但", "不", "也",
    "就", "都", "把", "被", "让", "给", "从", "到", "对",
    "请", "帮", "可以", "需要", "什么", "怎么", "如何",
    "the", "a", "an", "is", "are", "was", "were", "be",
    "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can",
    "i", "you", "he", "she", "it", "we", "they", "this",
    "that", "and", "or", "but", "not", "for", "with",
    "to", "of", "in", "on", "at", "by", "from", "as",
}


def extract_keywords(text: str) -> list:
    """从文本中提取关键词"""
    words = re.findall(r'[一-鿿]{2,}|[a-zA-Z]{3,}', text.lower())
    keywords = [w for w in words if w not in STOP_WORDS]
    return list(set(keywords))


# 类别权重
TYPE_WEIGHTS = {
    "feedback": 1.5,    # 反馈类记忆最重要
    "user": 1.3,        # 用户偏好
    "project": 1.2,     # 项目相关
    "reference": 1.0,   # 参考资料
}


def score_memory(memory: dict, keywords: list) -> float:
    """计算记忆与关键词的相关性分数"""
    if not keywords:
        return 0.0

    # 搜索范围: description + body
    search_text = f"{memory.get('description', '')} {memory.get('body', '')}".lower()

    # 关键词匹配
    matches = sum(1 for kw in keywords if kw in search_text)
    if matches == 0:
        return 0.0

    # 基础分 = 匹配数 / 总关键词数
    base_score = matches / len(keywords)

    # 类别权重
    mem_type = memory.get("type", "reference")
    type_weight = TYPE_WEIGHTS.get(mem_type, 1.0)

    # 精确匹配加分（完整短语出现在记忆中）
    exact_bonus = 0
    for kw in keywords:
        if len(kw) >= 3 and kw in search_text:
            exact_bonus += 0.1

    return base_score * type_weight + exact_bonus


# ─────────────────────────────────────────────────────────────────────────────
# 格式化输出
# ─────────────────────────────────────────────────────────────────────────────

def format_recall_output(memories: list) -> str:
    """格式化记忆召回输出"""
    if not memories:
        return ""

    lines = ["<system-reminder>", "Recalled memories:", ""]
    for m in memories:
        name = m.get("name", "")
        desc = m.get("description", "")
        mem_type = m.get("type", "")
        body = m.get("body", "")

        # 截断 body
        if len(body) > 300:
            body = body[:300] + "..."

        lines.append(f"- [{name}] ({mem_type}): {desc}")
        if body:
            lines.append(f"  {body}")
        lines.append("")

    lines.append("</system-reminder>")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # 读取 stdin
    content = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.buffer.read()
            content = raw.decode("utf-8", errors="replace").strip()
    except Exception:
        try:
            if not sys.stdin.isatty():
                content = _sanitize(sys.stdin.read().strip())
        except Exception:
            pass

    if not content:
        sys.exit(0)

    # 解析 hook 输入
    hook_data = parse_hook_input(content)
    cwd = hook_data.get("cwd", os.getcwd())

    # 构建查询文本
    query_parts = []
    tool_input = hook_data.get("tool_input", {})
    if isinstance(tool_input, dict):
        command = tool_input.get("command", "")
        if command:
            query_parts.append(command)
        file_path = tool_input.get("file_path", tool_input.get("filePath", ""))
        if file_path:
            query_parts.append(file_path)

    if hook_data.get("raw_text"):
        query_parts.append(hook_data["raw_text"][:500])

    query = " ".join(query_parts)
    if not query or len(query) < 5:
        sys.exit(0)

    # 提取关键词
    keywords = extract_keywords(query)
    if not keywords:
        sys.exit(0)

    # 加载原生记忆
    memory_dir = get_project_memory_dir(cwd)
    memories = load_native_memories(memory_dir)
    if not memories:
        sys.exit(0)

    # 评分排序
    scored = [(score_memory(m, keywords), m) for m in memories]
    scored.sort(key=lambda x: x[0], reverse=True)

    # 取 top 5，且分数 > 0
    top = [m for score, m in scored[:5] if score > 0]
    if not top:
        sys.exit(0)

    # 输出
    output = format_recall_output(top)
    if output:
        print(output)

    sys.exit(0)


if __name__ == "__main__":
    main()
