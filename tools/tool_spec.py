# -*- coding: utf-8 -*-
"""
jiaolong工具系统 - ToolSpec 基础规范
> 版本: v1.0 | 2026-04-02
> 参考: Claude Code Tool.ts

所有工具必须继承 ToolSpec，实现:
- name: 工具名
- description: 描述
- input_schema: JSON Schema 格式输入参数
- permission_model: 'auto' | 'confirm' | 'deny'
- execute(): 执行逻辑
"""
from __future__ import annotations
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class PermissionModel(str, Enum):
    AUTO = "auto"          # 自动放行（已审批/低风险）
    CONFIRM = "confirm"    # 每次确认
    DENY = "deny"          # 直接拒绝（高危操作）


class ProgressState(str, Enum):
    PENDING = "pending"     # 等待执行
    RUNNING = "running"     # 执行中
    COMPLETED = "completed" # 已完成
    FAILED = "failed"       # 失败
    BLOCKED = "blocked"      # 被阻塞


class ToolResult:
    """工具执行结果"""
    def __init__(self, success: bool, data: Any = None,
                 error: str = "", state: ProgressState = ProgressState.COMPLETED):
        self.success = success
        self.data = data
        self.error = error
        self.state = state
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "state": self.state.value if isinstance(self.state, Enum) else self.state,
            "timestamp": self.timestamp,
        }

    def __repr__(self):
        return f"ToolResult(success={self.success}, state={self.state}, error={self.error!r})"


class ToolSpec(ABC):
    """
    工具基类（所有工具的规范定义）
    
    使用方式:
        class MyTool(ToolSpec):
            name = "my_tool"
            description = "我的工具"
            permission_model = PermissionModel.CONFIRM
            input_schema = {
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "参数1"}
                },
                "required": ["param1"]
            }
            
            def execute(self, param1: str, **kwargs) -> ToolResult:
                ...
    """

    # === 必须定义的类属性 ===
    name: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = {}
    permission_model: PermissionModel = PermissionModel.CONFIRM

    # === 可选的进度状态 ===
    progress_state: ProgressState = ProgressState.PENDING
    progress_message: str = ""
    progress_percent: float = 0.0

    # === 权限风险等级（用于快速判断）===
    risk_level: int = 1  # 1=低, 2=中, 3=高
    tags: List[str] = []  # 如 ["file", "read", "safe"]

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具逻辑，子类必须实现"""
        pass

    def validate_input(self, **kwargs) -> Tuple[bool, str]:
        """
        验证输入参数是否符合 schema
        返回: (is_valid, error_message)
        """
        try:
            import jsonschema
            jsonschema.validate(instance=kwargs, schema=self.input_schema)
            return True, ""
        except ImportError:
            # 没有 jsonschema，做基本检查
            required = self.input_schema.get("required", [])
            for field in required:
                if field not in kwargs:
                    return False, f"缺少必需参数: {field}"
            return True, ""
        except Exception as e:
            return False, str(e)

    def can_execute(self) -> Tuple[bool, str]:
        """
        检查是否可以执行（权限判断）
        返回: (can_execute, reason)
        """
        if self.permission_model == PermissionModel.DENY:
            return False, f"[DENY] {self.name} 禁止执行（高危操作）"
        if self.permission_model == PermissionModel.CONFIRM:
            return True, f"[CONFIRM] {self.name} 需要确认"
        return True, f"[AUTO] {self.name} 自动放行"

    def update_progress(self, percent: float, message: str = ""):
        """更新执行进度"""
        self.progress_percent = percent
        if message:
            self.progress_message = message

    def get_spec(self) -> dict:
        """返回工具规范（不含execute）"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "permission_model": self.permission_model.value if isinstance(self.permission_model, Enum) else self.permission_model,
            "risk_level": self.risk_level,
            "tags": self.tags,
        }

    def __repr__(self):
        return f"<Tool: {self.name} risk={self.risk_level} permission={self.permission_model}>"


class ToolRegistry:
    """工具注册表（单例）"""
    _instance = None
    _tools: Dict[str, ToolSpec] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, tool: ToolSpec) -> None:
        if not tool.name:
            raise ValueError("工具必须有name")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def list_all(self) -> List[dict]:
        return [t.get_spec() for t in self._tools.values()]

    def list_by_tag(self, tag: str) -> List[ToolSpec]:
        return [t for t in self._tools.values() if tag in t.tags]

    def count(self) -> int:
        return len(self._tools)


# ═════════════════════════════════════════════════════════════════════════════
# 内置基础工具（验证规范可用）
# ═════════════════════════════════════════════════════════════════════════════

class EchoTool(ToolSpec):
    """Echo工具 - 验证工具系统正常工作"""
    name = "echo"
    description = "原样返回输入内容，用于测试"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["test", "safe"]
    input_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "要返回的消息"},
            "count": {"type": "integer", "description": "重复次数", "default": 1}
        },
        "required": ["message"]
    }

    def execute(self, message: str, count: int = 1, **kwargs) -> ToolResult:
        return ToolResult(
            success=True,
            data={"echo": message * count}
        )


class ReadFileTool(ToolSpec):
    """读文件工具"""
    name = "read_file"
    description = "读取文件内容"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["file", "read"]
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径（绝对或相对）"},
            "offset": {"type": "integer", "description": "起始行号", "default": 1},
            "limit": {"type": "integer", "description": "最大行数", "default": 100}
        },
        "required": ["path"]
    }

    def execute(self, path: str, offset: int = 1, limit: int = 100, **kwargs) -> ToolResult:
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            start = max(0, offset - 1)
            end = min(len(lines), start + limit)
            content = "".join(lines[start:end])
            return ToolResult(success=True, data={
                "path": path,
                "total_lines": len(lines),
                "returned_lines": end - start,
                "content": content,
            })
        except FileNotFoundError:
            return ToolResult(success=False, error=f"文件不存在: {path}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    # 验证规范
    print("=== ToolSpec 验证 ===")
    echo = EchoTool()
    spec = echo.get_spec()
    print(f"EchoTool spec: {json.dumps(spec, ensure_ascii=False, indent=2)}")
    
    valid, err = echo.validate_input(message="test")
    print(f"validate_input: valid={valid}, err={err}")
    
    can, reason = echo.can_execute()
    print(f"can_execute: {can}, {reason}")
    
    result = echo.execute(message="hello", count=3)
    print(f"execute: {result}")
    
    # 注册表测试
    registry = ToolRegistry()
    registry.register(echo)
    print(f"\nRegistry count: {registry.count()}")
    print(f"List all: {[t['name'] for t in registry.list_all()]}")
