# -*- coding: utf-8 -*-
"""
remember Skill - 记忆检查与整理
> 版本: v1.0 | 2026-04-02
> 触发: /remember
> 功能: 检查记忆系统状态，执行整理
"""
from __future__ import annotations
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill_output import ok, err, skill_main, format_table

_LOW_MEMORY_THRESHOLD = 10  # 低于此值认为记忆较少
from pathlib import Path


@skill_main("remember", required_params=[])
def run(query: str = "", detail: bool = False) -> dict:
    """
    记忆检查

    Args:
        query: 可选，检查特定关键词的记忆
        detail: 是否显示详细信息
    """
    import json

    hot_file = (Path.home() / ".claude" / "jiaolong" / "memory" / "memory_hot.json")

    if not hot_file.exists():
        return err("remember", "记忆文件不存在", "memory_hot.json 未找到")

    try:
        data = json.loads(hot_file.read_text(encoding="utf-8"))
        facts = data if isinstance(data, list) else data.get("facts", [])

        total = len(facts)

        # 按category统计
        cats = {}
        for f in facts:
            c = f.get("category", "?")
            cats[c] = cats.get(c, 0) + 1

        # 如果有query，过滤
        if query:
            facts = [f for f in facts if query.lower() in f.get("content", "").lower()]
            found = len(facts)
            summary = f"找到 {found}/{total} 条包含「{query}」的记忆"
        else:
            found = total
            summary = f"记忆系统共有 {total} 条记忆"

        # 摘要
        cat_lines = [f"{k}: {v}条" for k, v in sorted(cats.items())]

        data_out = {
            "total": total,
            "categories": cats,
            "query": query,
            "found": found,
        }

        hints = []
        if total < _LOW_MEMORY_THRESHOLD:
            hints.append("记忆较少，建议多使用 extract_memories 提取重要信息")
        if total > 100:
            hints.append("记忆量大，可使用 /dream 整合记忆")

        return ok("remember", data=data_out, summary=summary, hints=hints)

    except Exception as e:
        return err("remember", f"读取失败: {e}", "检查 memory_hot.json 格式")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] != "":
        result = run(query=" ".join(args))
    else:
        result = run()
    print(result.get("output", str(result)))
