# -*- coding: utf-8 -*-
"""
jiaolong工具 - MemoryTools (记忆系统专用)
> 版本: v1.0 | 2026-04-02
> 记忆读写、搜索、OMLX操作
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from .tool_spec import ToolSpec, ToolResult, PermissionModel


WORKSPACE = Path(r"C:\Users\steve\.openclaw\workspace")
MEMORY_DIR = WORKSPACE / "memory"
HOT_FILE = MEMORY_DIR / "memory_hot.json"


class MemoryReadTool(ToolSpec):
    """读取记忆"""
    name = "memory_read"
    description = "读取memory_hot.json中的记忆"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["memory", "read", "omlx"]

    input_schema = {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "按category筛选"},
            "limit": {"type": "integer", "description": "返回数量", "default": 50}
        }
    }

    def execute(self, category: str = None, limit: int = 50, **kwargs) -> ToolResult:
        try:
            with open(HOT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            facts = data.get("facts", [])
            if category:
                facts = [f for f in facts if f.get("category") == category]
            facts = facts[-limit:]
            return ToolResult(success=True, data={
                "count": len(facts),
                "facts": [{"id": f.get("id"), "content": f.get("content")[:80],
                           "category": f.get("category"), "confidence": f.get("confidence")}
                          for f in facts]
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MemorySearchTool(ToolSpec):
    """搜索记忆"""
    name = "memory_search"
    description = "在记忆中搜索关键词"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["memory", "search"]

    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "category": {"type": "string", "description": "限定category"}
        }
    },
    required = ["query"]

    def execute(self, query: str, category: str = None, **kwargs) -> ToolResult:
        try:
            with open(HOT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            q = query.lower()
            facts = data.get("facts", [])
            results = []
            for f in facts:
                content = f.get("content", "").lower()
                if q in content:
                    if category is None or f.get("category") == category:
                        results.append({
                            "id": f.get("id"),
                            "content": f.get("content"),
                            "category": f.get("category"),
                            "confidence": f.get("confidence"),
                        })
            return ToolResult(success=True, data={
                "query": query,
                "found": len(results),
                "results": results[:20]
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MemoryWriteTool(ToolSpec):
    """写入记忆"""
    name = "memory_write"
    description = "向memory_hot.json写入单条记忆"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["memory", "write", "omlx"]

    input_schema = {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "记忆内容"},
            "category": {
                "type": "string",
                "enum": ["context", "goal", "preference", "project", "knowledge",
                        "behavior", "investment", "feedback", "decision"],
                "description": "记忆类别"
            },
            "confidence": {"type": "number", "description": "置信度", "default": 0.80}
        },
        "required": ["content", "category"]
    }

    def execute(self, content: str, category: str, confidence: float = 0.80,
                 **kwargs) -> ToolResult:
        import hashlib
        try:
            with open(HOT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            facts = data.get("facts", [])

            ts = datetime.now().isoformat()
            fid = hashlib.md5((content + ts).encode()).hexdigest()[:12]
            new_fact = {
                "id": f"manual_{fid}",
                "content": content[:200],
                "category": category,
                "confidence": confidence,
                "createdAt": ts,
                "lastAccessed": ts,
                "accessCount": 1,
                "source": "memory_write_tool",
            }
            facts.append(new_fact)
            data["facts"] = facts
            with open(HOT_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return ToolResult(success=True, data={
                "id": new_fact["id"],
                "category": category,
                "total_facts": len(facts)
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MemoryStatsTool(ToolSpec):
    """记忆统计"""
    name = "memory_stats"
    description = "查看记忆系统统计信息"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["memory", "stats"]

    input_schema = {"type": "object", "properties": {}}

    def execute(self, **kwargs) -> ToolResult:
        try:
            with open(HOT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            facts = data.get("facts", [])

            cats = {}
            sources = {}
            total_conf = 0
            for f in facts:
                c = f.get("category", "?")
                cats[c] = cats.get(c, 0) + 1
                s = f.get("source", "?")
                sources[s] = sources.get(s, 0) + 1
                total_conf += f.get("confidence", 0)

            avg_conf = total_conf / len(facts) if facts else 0
            balance = 1 - (max(cats.values()) - min(cats.values())) / max(cats.values()) if cats else 0

            return ToolResult(success=True, data={
                "total_facts": len(facts),
                "by_category": cats,
                "by_source": sources,
                "avg_confidence": round(avg_conf, 3),
                "category_balance": round(balance, 3),
                "file_size_kb": round(HOT_FILE.stat().st_size / 1024, 1),
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MemoryOMLXTool(ToolSpec):
    """OMLX记忆交换操作"""
    name = "memory_omlx"
    description = "调用OMLX MemorySwapManager操作"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["memory", "omlx", "swap"]

    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["status", "swap", "search", "touch"],
                "description": "操作类型"
            },
            "query": {"type": "string", "description": "搜索查询"},
            "fact_id": {"type": "string", "description": "记忆ID"}
        }
    }

    def execute(self, action: str, query: str = None,
                 fact_id: str = None, **kwargs) -> ToolResult:
        try:
            sys.path.insert(0, str(MEMORY_DIR))
            from memory_swap_manager import MemorySwapManager
            mgr = MemorySwapManager()

            if action == "status":
                stats = mgr.status()
                return ToolResult(success=True, data={"status": stats})

            if action == "search" and query:
                results = mgr.search(query)
                return ToolResult(success=True, data={"query": query, "found": len(results), "results": results[:10]})

            if action == "touch" and fact_id:
                mgr.touch_fact(fact_id)
                return ToolResult(success=True, data={"touched": fact_id})

            return ToolResult(success=True, data={"message": f"action={action} executed"})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
