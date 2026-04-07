# -*- coding: utf-8 -*-
"""
jiaolong工具系统 - tools package (v2 扩展版)
> 版本: v2.0 | 2026-04-02
> 包含: 40+工具（Skeleton框架 + Claude Code规范）
"""
from .tool_spec import (
    ToolSpec, ToolResult, ToolRegistry,
    PermissionModel, ProgressState,
    EchoTool, ReadFileTool,
)

# File tools
from .file_tools import (
    WriteFileTool, AppendFileTool, CopyFileTool,
    MoveFileTool, DeleteFileTool, ListDirTool,
    FileInfoTool, SearchInFileTool, HashFileTool,
)

# Web tools
from .web_tools import (
    WebSearchTool, WebFetchTool, HttpRequestTool,
    JsonParseTool, JsonQueryTool,
)

# System tools
from .system_tools import (
    SystemInfoTool, EnvGetTool, EnvSetTool,
    ProcessListTool, KillProcessTool, DiskUsageTool,
    RunCommandTool,
)

# Quant tools
from .quant_tools import (
    StockScreenTool, FactorCalcTool, BacktestTool,
    PortfolioTool, MarketDataTool,
)

# Memory tools
from .memory_tools import (
    MemoryReadTool, MemorySearchTool, MemoryWriteTool,
    MemoryStatsTool, MemoryOMLXTool,
)

# Task tools
from .task_tools import (
    TaskCreateTool, TaskUpdateTool, TaskQueryTool,
)

# Notebook
from .notebook_tool import NotebookEditTool, Notebook

# MCP
from .mcp_tool import (
    MCPTool, MCPRegisterTool, MCPListServersTool, MCPClient,
)

# Agent
from .agent_tool import (
    AgentTool, AgentStatusTool, AgentKillTool, AgentRole,
)

# Team
from .team_tool import TeamCreateTool, TeamStatusTool, TeamTaskTree

# Cron
from .cron_tool import (
    CronCreateTool, CronListTool, CronDeleteTool, ReminderTool,
)

# 工具注册表
TOOL_REGISTRY = ToolRegistry()

# 注册所有内置工具
BUILTIN_TOOLS = [
    # 基础 (2)
    EchoTool(), ReadFileTool(),
    # 文件操作 (9)
    WriteFileTool(), AppendFileTool(), CopyFileTool(),
    MoveFileTool(), DeleteFileTool(), ListDirTool(),
    FileInfoTool(), SearchInFileTool(), HashFileTool(),
    # Web工具 (5)
    WebSearchTool(), WebFetchTool(), HttpRequestTool(),
    JsonParseTool(), JsonQueryTool(),
    # 系统工具 (7)
    SystemInfoTool(), EnvGetTool(), EnvSetTool(),
    ProcessListTool(), KillProcessTool(), DiskUsageTool(),
    RunCommandTool(),
    # 量化工具 (5)
    StockScreenTool(), FactorCalcTool(), BacktestTool(),
    PortfolioTool(), MarketDataTool(),
    # 记忆工具 (5)
    MemoryReadTool(), MemorySearchTool(), MemoryWriteTool(),
    MemoryStatsTool(), MemoryOMLXTool(),
    # Task工具 (3)
    TaskCreateTool(), TaskUpdateTool(), TaskQueryTool(),
    # Notebook (1)
    NotebookEditTool(),
    # MCP (3)
    MCPTool(), MCPRegisterTool(), MCPListServersTool(),
    # Agent (3)
    AgentTool(), AgentStatusTool(), AgentKillTool(),
    # Team (2)
    TeamCreateTool(), TeamStatusTool(),
    # Cron (4)
    CronCreateTool(), CronListTool(), CronDeleteTool(), ReminderTool(),
]

for tool in BUILTIN_TOOLS:
    TOOL_REGISTRY.register(tool)

__all__ = [
    "ToolSpec", "ToolResult", "ToolRegistry",
    "PermissionModel", "ProgressState",
    "EchoTool", "ReadFileTool",
    # File
    "WriteFileTool", "AppendFileTool", "CopyFileTool",
    "MoveFileTool", "DeleteFileTool", "ListDirTool",
    "FileInfoTool", "SearchInFileTool", "HashFileTool",
    # Web
    "WebSearchTool", "WebFetchTool", "HttpRequestTool",
    "JsonParseTool", "JsonQueryTool",
    # System
    "SystemInfoTool", "EnvGetTool", "EnvSetTool",
    "ProcessListTool", "KillProcessTool", "DiskUsageTool",
    "RunCommandTool",
    # Quant
    "StockScreenTool", "FactorCalcTool", "BacktestTool",
    "PortfolioTool", "MarketDataTool",
    # Memory
    "MemoryReadTool", "MemorySearchTool", "MemoryWriteTool",
    "MemoryStatsTool", "MemoryOMLXTool",
    # Task
    "TaskCreateTool", "TaskUpdateTool", "TaskQueryTool",
    # Notebook
    "NotebookEditTool", "Notebook",
    # MCP
    "MCPTool", "MCPRegisterTool", "MCPListServersTool", "MCPClient",
    # Agent
    "AgentTool", "AgentStatusTool", "AgentKillTool", "AgentRole",
    # Team
    "TeamCreateTool", "TeamStatusTool", "TeamTaskTree",
    # Cron
    "CronCreateTool", "CronListTool", "CronDeleteTool", "ReminderTool",
    "TOOL_REGISTRY",
]

if __name__ == "__main__":
    print("=== jiaolong工具系统 v2 ===")
    print(f"注册工具数: {TOOL_REGISTRY.count()}")
    print(f"\n分类统计:")
    tags_count = {}
    for t in TOOL_REGISTRY.list_all():
        primary_tag = t["tags"][0] if t["tags"] else "other"
        tags_count[primary_tag] = tags_count.get(primary_tag, 0) + 1
    for tag, cnt in sorted(tags_count.items()):
        print(f"  {tag}: {cnt}")
