# -*- coding: utf-8 -*-
"""
remember Skill - 记忆检查与整理
> 版本: v6.1.0 | 2026-06-01
> 触发: /remember
> 功能: 检查原生记忆系统状态，执行整理
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill_output import ok, err, skill_main, format_table

_LOW_MEMORY_THRESHOLD = 10

CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"


def _get_memory_dir() -> Path:
    return CLAUDE_PROJECTS / "C--cc" / "memory"


def _load_md_memories(memory_dir: Path) -> list:
    """从原生 .md 文件加载记忆"""
    memories = []
    if not memory_dir.exists():
        return memories
    for md_file in memory_dir.glob("*.md"):
        if md_file.name == "MEMORY.md":
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
            name = md_file.stem
            mem_type = "reference"
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].strip().split("\n"):
                        line = line.strip()
                        if line.startswith("name:"):
                            name = line[5:].strip().strip('"').strip("'")
                        elif line.startswith("type:"):
                            mem_type = line[5:].strip().strip('"').strip("'")
            memories.append({"name": name, "type": mem_type, "file": md_file.name})
        except Exception:
            continue
    return memories


@skill_main("remember", required_params=[])
def run(query: str = "", detail: bool = False) -> dict:
    """记忆检查（原生 .md 系统）"""
    memory_dir = _get_memory_dir()

    if not memory_dir.exists():
        return err("remember", "记忆目录不存在", str(memory_dir))

    memories = _load_md_memories(memory_dir)
    total = len(memories)

    # 按type统计
    types = {}
    for m in memories:
        t = m.get("type", "?")
        types[t] = types.get(t, 0) + 1

    # 如果有query，过滤
    if query:
        memories = [m for m in memories if query.lower() in m.get("name", "").lower()]
        found = len(memories)
        summary = f"找到 {found}/{total} 条包含「{query}」的记忆"
    else:
        found = total
        summary = f"记忆系统共有 {total} 条记忆"

    data_out = {
        "total": total,
        "types": types,
        "query": query,
        "found": found,
    }

    hints = []
    if total < _LOW_MEMORY_THRESHOLD:
        hints.append("记忆较少，建议多使用 extract_memories 提取重要信息")
    if total > 100:
        hints.append("记忆量大，可使用 /dream 整合记忆")

    return ok("remember", data=data_out, summary=summary, hints=hints)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] != "":
        result = run(query=" ".join(args))
