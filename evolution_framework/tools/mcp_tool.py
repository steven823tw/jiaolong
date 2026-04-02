# -*- coding: utf-8 -*-
"""
jiaolong工具 - MCPTool (Model Context Protocol)
> 版本: v1.0 | 2026-04-02
> 对应: Claude Code MCPTool
> 用途: 调用外部MCP Server工具
"""
from __future__ import annotations
import json
import subprocess
from typing import Any, Dict, List, Optional
from datetime import datetime
from .tool_spec import ToolSpec, ToolResult, PermissionModel, ProgressState


class MCPClient:
    """MCP客户端（管理MCP Server连接）"""
    _servers: Dict[str, dict] = {}

    @classmethod
    def register_server(cls, name: str, command: List[str],
                        env: Dict[str, str] = None, port: int = 8080):
        """注册MCP Server"""
        cls._servers[name] = {
            "name": name,
            "command": command,
            "env": env or {},
            "port": port,
            "status": "stopped",
            "registered_at": datetime.now().isoformat(),
        }

    @classmethod
    def list_servers(cls) -> List[dict]:
        return list(cls._servers.values())

    @classmethod
    def get_server(cls, name: str) -> Optional[dict]:
        return cls._servers.get(name)

    @classmethod
    async def call_tool(cls, server_name: str, tool_name: str,
                        arguments: Dict[str, Any]) -> dict:
        """
        调用MCP Server工具（模拟实现）
        真实环境：通过stdio或HTTP与MCP Server通信
        """
        server = cls._servers.get(server_name)
        if not server:
            return {"error": f"Server不存在: {server_name}"}

        # 模拟调用（实际会用 MCP JSON-RPC 协议）
        # {
        #   "jsonrpc": "2.0",
        #   "method": "tools/call",
        #   "params": {
        #       "name": tool_name,
        #       "arguments": arguments
        #   },
        #   "id": 1
        # }
        return {
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
            "result": f"[模拟] {server_name}.{tool_name} 执行成功",
            "called_at": datetime.now().isoformat(),
        }


class MCPTool(ToolSpec):
    """MCP协议集成工具"""
    name = "mcp_call"
    description = "调用外部MCP Server工具"
    permission_model = PermissionModel.CONFIRM  # 外部调用需确认
    risk_level = 3  # 高风险（外部通信）
    tags = ["mcp", "external", "protocol"]

    input_schema = {
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "MCP Server名称"
            },
            "tool": {
                "type": "string",
                "description": "工具名称"
            },
            "arguments": {
                "type": "object",
                "description": "工具参数",
                "default": {}
            },
            "timeout": {
                "type": "integer",
                "description": "超时（秒）",
                "default": 30
            }
        },
        "required": ["server", "tool"]
    }

    def execute(self, server: str, tool: str,
                 arguments: dict = None,
                 timeout: int = 30,
                 **kwargs) -> ToolResult:
        """调用MCP工具"""
        arguments = arguments or {}

        # 检查server是否存在
        srv = MCPClient.get_server(server)
        if not srv:
            # 尝试列出可用server
            available = [s["name"] for s in MCPClient.list_servers()]
            return ToolResult(
                success=False,
                error=f"Server不存在: {server}",
                data={"available_servers": available}
            )

        # 调用（模拟）
        self.update_progress(50, f"调用 {server}.{tool}...")
        
        # 真实环境：
        # import asyncio
        # result = await MCPClient.call_tool(server, tool, arguments)
        result = {
            "server": server,
            "tool": tool,
            "arguments": arguments,
            "result": f"[模拟] {server}.{tool} 调用成功",
        }

        return ToolResult(
            success=True,
            data=result
        )


class MCPRegisterTool(ToolSpec):
    """注册MCP Server"""
    name = "mcp_register"
    description = "注册新的MCP Server"
    permission_model = PermissionModel.DENY  # 禁止（系统级操作）
    risk_level = 3
    tags = ["mcp", "admin", "system"]

    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Server名称"},
            "command": {
                "type": "array",
                "items": {"type": "string"},
                "description": "启动命令"
            },
            "port": {"type": "integer", "description": "端口", "default": 8080}
        },
        "required": ["name", "command"]
    }

    def execute(self, name: str, command: List[str],
                 port: int = 8080,
                 **kwargs) -> ToolResult:
        # DENY权限会阻止执行
        can, reason = self.can_execute()
        if not can:
            return ToolResult(success=False, error=reason)
        MCPClient.register_server(name, command, port=port)
        return ToolResult(success=True, data={"message": f"Server注册: {name}"})


class MCPListServersTool(ToolSpec):
    """列出已注册的MCP Servers"""
    name = "mcp_list_servers"
    description = "列出所有MCP Server"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["mcp", "query"]

    input_schema = {
        "type": "object",
        "properties": {
            "filter": {"type": "string", "description": "按名称筛选"}
        }
    }

    def execute(self, filter: str = None, **kwargs) -> ToolResult:
        servers = MCPClient.list_servers()
        if filter:
            servers = [s for s in servers if filter.lower() in s["name"].lower()]
        return ToolResult(
            success=True,
            data={"count": len(servers), "servers": servers}
        )


if __name__ == "__main__":
    print("=== MCPTool 验证 ===")

    # 注册测试server
    MCPClient.register_server(
        name="test_server",
        command=["python", "-m", "mcp_server"],
        port=8080
    )

    # 列出servers
    list_tool = MCPListServersTool()
    r1 = list_tool.execute()
    print(f"list_servers: {r1.data}")

    # 调用工具
    mcp = MCPTool()
    r2 = mcp.execute(server="test_server", tool="test_tool",
                      arguments={"input": "hello"})
    print(f"call: success={r2.success}, data={r2.data}")
