# -*- coding: utf-8 -*-
"""
jiaolong工具 - SystemTools (系统/进程/环境)
> 版本: v1.0 | 2026-04-02
> 系统信息、进程管理、环境变量
"""
from __future__ import annotations
import os, sys, platform, subprocess, json, shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
from .tool_spec import ToolSpec, ToolResult, PermissionModel

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class SystemInfoTool(ToolSpec):
    """获取系统信息"""
    name = "system_info"
    description = "获取操作系统/硬件信息"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["system", "info", "read"]

    input_schema = {
        "type": "object",
        "properties": {
            "detail": {"type": "boolean", "description": "详细信息", "default": False}
        }
    }

    def execute(self, detail: bool = False, **kwargs) -> ToolResult:
        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "hostname": platform.node(),
        }
        if detail:
            if HAS_PSUTIL:
                mem = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=0.1)
                info.update({
                    "cpu_percent": cpu,
                    "cpu_count": psutil.cpu_count(),
                    "memory_total_gb": round(mem.total / (1024**3), 2),
                    "memory_available_gb": round(mem.available / (1024**3), 2),
                    "memory_percent": mem.percent,
                })
            else:
                info["note"] = "psutil not available (pip install psutil)"
        return ToolResult(success=True, data=info)


class EnvGetTool(ToolSpec):
    """获取环境变量"""
    name = "env_get"
    description = "读取环境变量"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["system", "env", "read"]

    input_schema = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "变量名（为空则返回所有）"}
        }
    }

    def execute(self, key: str = None, **kwargs) -> ToolResult:
        if key:
            val = os.environ.get(key, "")
            return ToolResult(success=True, data={key: val})
        all_env = {k: v for k, v in os.environ.items()}
        return ToolResult(success=True, data={"all": all_env})


class EnvSetTool(ToolSpec):
    """设置环境变量"""
    name = "env_set"
    description = "设置环境变量（当前进程）"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["system", "env", "write"]

    input_schema = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "变量名"},
            "value": {"type": "string", "description": "变量值"}
        },
        "required": ["key", "value"]
    }

    def execute(self, key: str, value: str, **kwargs) -> ToolResult:
        os.environ[key] = value
        return ToolResult(success=True, data={key: value})


class ProcessListTool(ToolSpec):
    """列出进程"""
    name = "process_list"
    description = "列出正在运行的进程"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["system", "process", "read"]

    input_schema = {
        "type": "object",
        "properties": {
            "name_filter": {"type": "string", "description": "按进程名过滤"},
            "limit": {"type": "integer", "description": "最大数量", "default": 20}
        }
    }

    def execute(self, name_filter: str = None, limit: int = 20, **kwargs) -> ToolResult:
        if not HAS_PSUTIL:
            return ToolResult(success=True, data={"note": "psutil not available", "processes": []})
        processes = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                if name_filter and name_filter.lower() not in info["name"].lower():
                    continue
                processes.append(info)
                if len(processes) >= limit:
                    break
            except Exception:
                pass
        return ToolResult(success=True, data={"count": len(processes), "processes": processes})


class KillProcessTool(ToolSpec):
    """终止进程"""
    name = "process_kill"
    description = "终止指定进程"
    permission_model = PermissionModel.DENY
    risk_level = 3
    tags = ["system", "process", "kill", "dangerous"]

    input_schema = {
        "type": "object",
        "properties": {
            "pid": {"type": "integer", "description": "进程ID"}
        },
        "required": ["pid"]
    }

    def execute(self, pid: int, **kwargs) -> ToolResult:
        can, reason = self.can_execute()
        if not can:
            return ToolResult(success=False, error=reason)
        if not HAS_PSUTIL:
            return ToolResult(success=False, error="psutil not available")
        try:
            p = psutil.Process(pid)
            p.terminate()
            return ToolResult(success=True, data={"pid": pid, "killed": True})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DiskUsageTool(ToolSpec):
    """磁盘使用情况"""
    name = "disk_usage"
    description = "查看磁盘空间使用情况"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["system", "disk", "read"]

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "路径（默认当前目录）"}
        }
    }

    def execute(self, path: str = ".", **kwargs) -> ToolResult:
        try:
            p = Path(path).resolve()
            if HAS_PSUTIL:
                usage = psutil.disk_usage(str(p))
                return ToolResult(success=True, data={
                    "path": str(p),
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent,
                })
            else:
                return ToolResult(success=True, data={
                    "path": str(p),
                    "note": "psutil not available (pip install psutil)"
                })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class RunCommandTool(ToolSpec):
    """执行Shell命令"""
    name = "run_command"
    description = "执行Shell/PowerShell命令"
    permission_model = PermissionModel.CONFIRM
    risk_level = 3
    tags = ["system", "exec", "shell"]

    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "命令"},
            "timeout": {"type": "integer", "description": "超时秒", "default": 30},
            "cwd": {"type": "string", "description": "工作目录"}
        },
        "required": ["command"]
    }

    def execute(self, command: str, timeout: int = 30, cwd: str = None, **kwargs) -> ToolResult:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return ToolResult(
                success=(result.returncode == 0),
                data={
                    "returncode": result.returncode,
                    "stdout": result.stdout[:2000],
                    "stderr": result.stderr[:500],
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"命令超时({timeout}s)")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
