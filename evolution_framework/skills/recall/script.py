# -*- coding: utf-8 -*-
"""
recall Skill - 记忆召回（增强版）
> 版本: v2.0 | 2026-04-02
> 增强: 自然语言/时间过滤/类别过滤
> 触发: /recall <关键词>
>       /recall jiaolong
>       /recall jiaolong recent 5
>       /recall jiaolong category=project
>       /recall recent 5 (最近的5条记忆)
>       /recall decision (所有决策类记忆)
"""
from __future__ import annotations
import sys, re
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory_recall import MemoryRetriever

# ─────────────────────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_TOP_K = 10
_MAX_TOP_K = 20


# ─────────────────────────────────────────────────────────────────────────────
# 自然语言查询解析
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "决策": "decision",
    "偏好": "preference",
    "项目": "project",
    "目标": "goal",
    "背景": "context",
    "知识": "knowledge",
    "行为": "behavior",
    "反馈": "feedback",
    "投资": "investment",
    "技术": "technical",
}

TIME_KEYWORDS = {
    "最近": ("days", 7),
    "上周": ("days", 7),
    "本月": ("days", 30),
    "今天": ("days", 1),
    "昨天": ("days", 1),
    "三天内": ("days", 3),
    "一周内": ("days", 7),
    "一个月内": ("days", 30),
}


def parse_query(raw: str) -> dict:
    """
    解析自然语言查询，返回 {query, category, time_range, top_k}

    支持格式:
      /recall jiaolong                    → query="jiaolong"
      /recall jiaolong recent 5           → query="jiaolong" recent=7days top_k=5
      /recall jiaolong category=project    → query="jiaolong" category="project"
      /recall recent 5                 → query="" recent=7days top_k=5
      /recall decision                 → category="decision"
      /recall jiaolong 2026-04             → query="jiaolong" time="2026-04"
      /recall jiaolong吗                   → query="jiaolong"
    """
    raw = raw.strip()
    result = {
        "query": "",
        "category": None,
        "time_range": None,  # {"type": "days", "value": 7}
        "top_k": DEFAULT_TOP_K,
    }

    # 移除触发词前缀
    raw = re.sub(r"^/?recall\s+", "", raw, flags=re.IGNORECASE)

    # 提取 top_k: /recall xxx 5
    top_k_match = re.search(r'\b(\d+)\s*$', raw)
    if top_k_match:
        result["top_k"] = min(int(top_k_match.group(1)), _MAX_TOP_K)
        raw = raw[:top_k_match.start()].strip()

    # 提取 category=xxx
    cat_match = re.search(r'category=(\w+)', raw, re.IGNORECASE)
    if cat_match:
        cat_name = cat_match.group(1).lower()
        # 支持中文或英文类别名
        result["category"] = CATEGORY_KEYWORDS.get(cat_name, cat_name)
        raw = raw[:cat_match.start()].strip() + raw[cat_match.end():].strip()

    # 提取 recent/N days
    time_match = re.search(r'(最近|上周|本月|今天|昨天|三天内|一周内|一个月内|recent)', raw, re.IGNORECASE)
    if time_match:
        kw = time_match.group(1)
        if kw.lower() == "recent":
            result["time_range"] = {"type": "days", "value": 7}
        else:
            result["time_range"] = {"type": "days", "value": TIME_KEYWORDS.get(kw, (None, 7))[1]}
        raw = raw[:time_match.start()].strip() + raw[time_match.end():].strip()

    # 提取月份: 2026-04 或 2026/04
    month_match = re.search(r'(202[3-9][-/]\d{2})', raw)
    if month_match:
        result["time_range"] = {"type": "month", "value": month_match.group(1)}
        raw = raw[:month_match.start()].strip() + raw[month_match.end():].strip()

    # 清理 query
    result["query"] = raw.strip()

    # 如果只剩数字（如 "5 recent"），清空query
    if result["query"].isdigit():
        result["top_k"] = min(int(result["query"]), 20)
        result["query"] = ""

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 时间过滤
# ─────────────────────────────────────────────────────────────────────────────

def filter_by_time(memories: list, time_range: dict) -> list:
    """根据时间范围过滤记忆"""
    if not time_range:
        return memories

    now = datetime.now()

    if time_range["type"] == "days":
        cutoff = now - timedelta(days=time_range["value"])
        return [
            m for m in memories
            if _get_mem_time(m) and _get_mem_time(m) >= cutoff
        ] or memories  # 如果过滤后为空，返回全部

    if time_range["type"] == "month":
        target_month = time_range["value"]  # "2026-04"
        return [
            m for m in memories
            if _get_mem_time(m) and _get_mem_time(m).strftime("%Y-%m") == target_month
        ] or memories

    return memories


def _get_mem_time(m: dict) -> datetime:
    """从记忆条目提取时间"""
    ts = m.get("timestamp") or m.get("createdAt") or m.get("updatedAt", "")
    if not ts:
        return None
    try:
        if isinstance(ts, str):
            # 支持多种格式
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(ts[:19], fmt)
                except ValueError:
                    continue
            return None
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 主执行函数
# ─────────────────────────────────────────────────────────────────────────────

def run(query: str = "", top_k: int = DEFAULT_TOP_K, category: str = None,
        time_range: dict = None, raw_query: str = "") -> dict:
    """
    执行记忆召回

    Args:
        query: 搜索关键词（已解析）
        top_k: 返回数量
        category: 类别过滤
        time_range: 时间范围过滤
        raw_query: 原始查询（用于解析）

    Returns:
        {"success": bool, "query": str, "found": int, "output": str}
    """
    # 如果有原始查询，先解析
    if raw_query:
        parsed = parse_query(raw_query)
        query = query or parsed["query"]
        top_k = parsed["top_k"]
        category = category or parsed["category"]
        time_range = time_range or parsed["time_range"]

    # 解析原始查询
    if raw_query:
        parsed = parse_query(raw_query)
        query = query or parsed["query"]
        top_k = parsed["top_k"]
        category = category or parsed["category"]
        time_range = time_range or parsed["time_range"]

    if not query and not category and not time_range:
        return {
            "success": False,
            "error": "用法:\n  /recall <关键词>          - 关键词召回\n  /recall jiaolong recent 5    - 最近5条\n  /recall jiaolong category=project - 项目类\n  /recall recent 5            - 最近5条（不限关键词）"
        }

    retriever = MemoryRetriever(top_k=top_k * 2)  # 多召回一些，过滤后够用

    if query:
        memories = retriever.retrieve(query)
    else:
        # 无关键词：直接从hot文件扫描
        memories = _scan_by_category_all()

    # 类别过滤
    if category:
        memories = [m for m in memories if m.get("category") == category]
        # 如果过滤后为空，尝试从hot文件直接扫描
        if not memories:
            memories = _scan_by_category(category)

    # 时间过滤
    if time_range:
        memories = filter_by_time(memories, time_range)

    # 取top_k
    memories = memories[:top_k]

    if not memories:
        return {
            "success": True,
            "query": query or category or "all",
            "found": 0,
            "output": f"未找到与「{query or category}」相关的记忆"
        }

    # 格式化输出
    lines = [f"\n## 相关记忆（{len(memories)}条）\n"]

    cat_emoji = {
        "decision": "🎯", "preference": "💡", "project": "📋",
        "goal": "🎯", "context": "📎", "knowledge": "📚",
        "behavior": "🔄", "feedback": "💬", "investment": "💰",
    }

    for i, m in enumerate(memories, 1):
        cat = m.get("category", "?")
        conf = m.get("confidence", 0)
        content = m.get("content", "")
        score = m.get("_relevance_score", 0)
        created = _get_mem_time(m)
        date_str = created.strftime("%Y-%m-%d") if created else ""

        emoji = cat_emoji.get(cat, "📝")

        lines.append(f"{i}. {emoji} [{cat}] (置信{conf:.0%} | 相关度{score:.1f})")
        lines.append(f"   {content}")
        if date_str:
            lines.append(f"   📅 {date_str}")
        lines.append("")

    output = "\n".join(lines)
    return {
        "success": True,
        "query": query,
        "category": category,
        "found": len(memories),
        "output": output
    }


def _scan_by_category(category: str) -> list:
    """直接从memory_hot.json扫描指定category的记忆"""
    import json
    from pathlib import Path

    hot_file = (Path.home() / ".claude" / "jiaolong" / "memory" / "memory_hot.json")
    if not hot_file.exists():
        return []

    try:
        data = json.loads(hot_file.read_text(encoding="utf-8"))
        facts = data if isinstance(data, list) else data.get("facts", [])
        return [f for f in facts if f.get("category") == category]
    except Exception:
        return []


def _scan_by_category_all() -> list:
    """直接从memory_hot.json扫描所有记忆（无关键词时）"""
    import json
    from pathlib import Path

    hot_file = (Path.home() / ".claude" / "jiaolong" / "memory" / "memory_hot.json")
    if not hot_file.exists():
        return []

    try:
        data = json.loads(hot_file.read_text(encoding="utf-8"))
        facts = data if isinstance(data, list) else data.get("facts", [])
        return facts
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# CLI / Skill入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        print("用法:")
        print("  python script.py jiaolong")
        print("  python script.py jiaolong recent 5")
        print("  python script.py decision")
        print("  python script.py category=project jiaolong")
        sys.exit(0)

    raw_query = " ".join(args)
    parsed = parse_query(raw_query)

    print(f"解析结果: query='{parsed['query']}' category={parsed['category']} "
          f"time={parsed['time_range']} top_k={parsed['top_k']}")

    result = run(raw_query=raw_query)

    if result.get("success"):
        print(result.get("output", ""))
        print(f"\n(共 {result.get('found', 0)} 条)")
    else:
        print(f"错误: {result.get('error')}")
