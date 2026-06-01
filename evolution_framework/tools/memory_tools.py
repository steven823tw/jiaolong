# -*- coding: utf-8 -*-
"""
jiaolong工具 - MemoryTools (原生记忆系统)
> 版本: v6.1.0 | 2026-06-01
> 记忆读写、搜索（原生 .md 格式）
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from .tool_spec import ToolSpec, ToolResult, PermissionModel


CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
NATIVE_MEMORY_DIR = CLAUDE_PROJECTS / "C--cc" / "memory"


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
            description = ""
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].strip().split("\n"):
                        line = line.strip()
                        if line.startswith("name:"):
                            name = line[5:].strip().strip('"').strip("'")
                        elif line.startswith("description:"):
                            description = line[12:].strip().strip('"').strip("'")
                        elif line.startswith("type:"):
                            mem_type = line[5:].strip().strip('"').strip("'")
                    body = parts[2].strip()
                else:
                    body = content
            else:
                body = content
            memories.append({
                "name": name,
                "description": description,
                "type": mem_type,
                "content": body,
                "file": md_file.name,
            })
        except Exception:
            continue
    return memories


class MemoryReadTool(ToolSpec):
    """读取原生记忆"""
    name = "memory_read"
    description = "读取原生 .md 记忆文件"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["memory", "read"]

    input_schema = {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "按type筛选"},
            "limit": {"type": "integer", "description": "返回数量", "default": 50}
        }
    }

    def execute(self, category: str = None, limit: int = 50, **kwargs) -> ToolResult:
        try:
            memories = _load_md_memories(NATIVE_MEMORY_DIR)
            if category:
                memories = [m for m in memories if m.get("type") == category]
            return ToolResult(success=True, data=memories[:limit])
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MemoryWriteTool(ToolSpec):
    """写入记忆（创建 .md 文件）"""
    name = "memory_write"
    description = "向原生记忆系统写入一条记忆"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["memory", "write"]

    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "记忆名称"},
            "content": {"type": "string", "description": "记忆内容"},
            "type": {"type": "string", "description": "类型", "default": "reference"}
        },
        "required": ["name", "content"]
    }

    def execute(self, name: str, content: str, type: str = "reference", **kwargs) -> ToolResult:
        try:
            NATIVE_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            safe_name = name.replace(" ", "-").replace("/", "-")[:50]
            md_file = NATIVE_MEMORY_DIR / f"{safe_name}.md"
            md_content = f"""---
name: {name}
description: {content[:100]}
type: {type}
---

{content}
"""
            md_file.write_text(md_content, encoding="utf-8")
            return ToolResult(success=True, data={"file": str(md_file)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
