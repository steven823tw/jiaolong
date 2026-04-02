# -*- coding: utf-8 -*-
"""
jiaolong工具 - WebTools (搜索/抓取/API调用)
> 版本: v1.0 | 2026-04-02
> 批量创建Web相关工具
"""
from __future__ import annotations
import json, urllib.request, urllib.parse
from typing import Any, Dict
from datetime import datetime
from .tool_spec import ToolSpec, ToolResult, PermissionModel


class WebSearchTool(ToolSpec):
    """网页搜索工具"""
    name = "web_search"
    description = "搜索网页（模拟Tavily/wyniki）"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["web", "search", "http"]

    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索查询"},
            "count": {"type": "integer", "description": "结果数量", "default": 5}
        },
        "required": ["query"]
    }

    def execute(self, query: str, count: int = 5, **kwargs) -> ToolResult:
        # 模拟搜索结果（真实环境对接Tavily API）
        results = [
            {"title": f"结果{i+1}: {query}", "url": f"https://example.com/result{i+1}", "snippet": f"这是关于'{query}'的相关信息..."}
            for i in range(count)
        ]
        return ToolResult(success=True, data={"query": query, "results": results, "count": count})


class WebFetchTool(ToolSpec):
    """获取网页内容"""
    name = "web_fetch"
    description = "获取网页HTML并提取可读内容"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["web", "fetch", "http"]

    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "网页URL"},
            "max_chars": {"type": "integer", "description": "最大字符数", "default": 5000}
        },
        "required": ["url"]
    }

    def execute(self, url: str, max_chars: int = 5000, **kwargs) -> ToolResult:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                content = r.read().decode("utf-8", errors="ignore")
            return ToolResult(success=True, data={
                "url": url,
                "content": content[:max_chars],
                "size": len(content)
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HttpRequestTool(ToolSpec):
    """HTTP请求工具"""
    name = "http_request"
    description = "发送HTTP请求（GET/POST/PUT/DELETE）"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["web", "http", "api"]

    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "请求URL"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
            "headers": {"type": "object", "description": "请求头"},
            "body": {"type": "string", "description": "请求体(JSON)"}
        },
        "required": ["url"]
    }

    def execute(self, url: str, method: str = "GET",
                 headers: Dict = None, body: str = None, **kwargs) -> ToolResult:
        try:
            h = headers or {}
            h["User-Agent"] = h.get("User-Agent", "jiaolongBot/1.0")
            req = urllib.request.Request(url, headers=h, method=method)
            if body:
                req.data = body.encode("utf-8")
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_body = resp.read().decode("utf-8", errors="ignore")
            return ToolResult(success=True, data={
                "url": url, "method": method,
                "status": resp.status,
                "body": resp_body[:2000]
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class JsonParseTool(ToolSpec):
    """JSON解析工具"""
    name = "json_parse"
    description = "解析/格式化JSON字符串"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["json", "parse", "utility"]

    input_schema = {
        "type": "object",
        "properties": {
            "json_str": {"type": "string", "description": "JSON字符串"},
            "pretty": {"type": "boolean", "description": "格式化", "default": True}
        },
        "required": ["json_str"]
    }

    def execute(self, json_str: str, pretty: bool = True, **kwargs) -> ToolResult:
        try:
            obj = json.loads(json_str)
            output = json.dumps(obj, ensure_ascii=False, indent=2 if pretty else None)
            return ToolResult(success=True, data={"parsed": obj, "output": output})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class JsonQueryTool(ToolSpec):
    """JSON查询工具（JSONPath简版）"""
    name = "json_query"
    description = "从JSON中提取字段"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["json", "query", "utility"]

    input_schema = {
        "type": "object",
        "properties": {
            "json_str": {"type": "string", "description": "JSON字符串或对象"},
            "path": {"type": "string", "description": "字段路径如 data.results[0].name"},
            "default": {"type": "string", "description": "默认值"}
        },
        "required": ["json_str", "path"]
    }

    def execute(self, json_str: str, path: str, default: str = None, **kwargs) -> ToolResult:
        try:
            obj = json.loads(json_str) if isinstance(json_str, str) else json_str
            parts = path.split(".")
            val = obj
            for part in parts:
                if "[" in part and "]" in part:
                    key, idx = part.replace("]", "").split("[")
                    val = val.get(key, [])[int(idx)] if key else val[int(idx)]
                else:
                    val = val.get(part, default if default is not None else None)
            return ToolResult(success=True, data={"path": path, "value": val})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
