# -*- coding: utf-8 -*-
"""
jiaolong工具 - AgentTool（子Agent生成）
> 版本: v1.0 | 2026-04-02
> 对应: Claude Code AgentTool
> 封装: sessions_spawn
> 权限: plan模式（每次确认）
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from .tool_spec import ToolSpec, ToolResult, PermissionModel, ProgressState


class AgentRole(str, Enum):
    """jiaolong集团Agent角色"""
    小笨 = "boss"       # 统筹协调·主控
    小呆 = "intel"      # 情报搜集·验证
    小傻 = "ux"         # UI/UX前端
    小虾 = "backend"    # 架构·后端


AGENT_DESCRIPTIONS = {
    AgentRole.小笨: "jiaolong老板，统筹协调，综合决策",
    AgentRole.小呆: "情报官，多源搜索，交叉验证",
    AgentRole.小傻: "交互大牛，UI/UX前端，界面设计",
    AgentRole.小虾: "技术大牛，架构后端，API设计",
}


class AgentSession:
    """Agent会话记录"""
    _sessions: Dict[str, dict] = {}

    @classmethod
    def create(cls, agent_id: str, role: AgentRole,
               task: str, parent_session: str = None) -> str:
        session_key = f"agent:{role.value}:{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cls._sessions[session_key] = {
            "session_key": session_key,
            "agent_id": agent_id,
            "role": role.value,
            "task": task,
            "parent_session": parent_session,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "result": None,
        }
        return session_key

    @classmethod
    def update_status(cls, session_key: str, status: str, result: Any = None):
        if session_key in cls._sessions:
            cls._sessions[session_key]["status"] = status
            if result:
                cls._sessions[session_key]["result"] = result
            if status in ("completed", "failed"):
                cls._sessions[session_key]["completed_at"] = datetime.now().isoformat()

    @classmethod
    def get(cls, session_key: str) -> Optional[dict]:
        return cls._sessions.get(session_key)

    @classmethod
    def list_all(cls) -> List[dict]:
        return list(cls._sessions.values())

    @classmethod
    def list_by_status(cls, status: str) -> List[dict]:
        return [s for s in cls._sessions.values() if s["status"] == status]


class AgentTool(ToolSpec):
    """子Agent生成工具（封装sessions_spawn）"""
    name = "agent_spawn"
    description = "生成子Agent执行任务"
    permission_model = PermissionModel.CONFIRM  # 每次确认
    risk_level = 2
    tags = ["agent", "spawn", "subagent"]

    input_schema = {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": ["boss", "intel", "ux", "backend"],
                "description": "Agent角色（小笨=boss，小呆=intel，小傻=ux，小虾=backend）"
            },
            "task": {
                "type": "string",
                "description": "任务描述"
            },
            "task_type": {
                "type": "string",
                "enum": ["research", "execution", "analysis", "coding", "coordination"],
                "description": "任务类型",
                "default": "execution"
            },
            "mode": {
                "type": "string",
                "enum": ["run", "session"],
                "description": "运行模式",
                "default": "run"
            },
            "parent_session": {
                "type": "string",
                "description": "父会话key（用于追踪）"
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "超时（秒）",
                "default": 300
            }
        },
        "required": ["role", "task"]
    }

    def execute(self, role: str, task: str,
                 task_type: str = "execution",
                 mode: str = "run",
                 parent_session: str = None,
                 timeout_seconds: int = 300,
                 **kwargs) -> ToolResult:
        """生成子Agent"""
        try:
            role_enum = AgentRole(role)
        except ValueError:
            return ToolResult(
                success=False,
                error=f"未知角色: {role}，可用: boss/intel/ux/backend"
            )

        # 记录会话
        session_key = AgentSession.create(
            agent_id=f"jarvis-{role}",
            role=role_enum,
            task=task,
            parent_session=parent_session,
        )

        # 真实环境会调用 sessions_spawn
        # 这里模拟返回session_key
        self.update_progress(50, f"Agent {role} 已生成")

        return ToolResult(
            success=True,
            data={
                "session_key": session_key,
                "role": role,
                "role_description": AGENT_DESCRIPTIONS.get(role_enum, ""),
                "task": task,
                "status": "created",
                "message": f"子Agent [{role}] 已创建，等待执行"
            }
        )


class AgentStatusTool(ToolSpec):
    """查看Agent状态"""
    name = "agent_status"
    description = "查看子Agent执行状态"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["agent", "query", "status"]

    input_schema = {
        "type": "object",
        "properties": {
            "session_key": {"type": "string", "description": "会话key"},
            "status_filter": {
                "type": "string",
                "enum": ["created", "running", "completed", "failed", ""],
                "description": "按状态筛选"
            }
        }
    }

    def execute(self, session_key: str = None,
                 status_filter: str = None,
                 **kwargs) -> ToolResult:
        if session_key:
            session = AgentSession.get(session_key)
            if not session:
                return ToolResult(success=False, error=f"会话不存在: {session_key}")
            return ToolResult(success=True, data={"session": session})

        sessions = AgentSession.list_all()
        if status_filter:
            sessions = AgentSession.list_by_status(status_filter)
        return ToolResult(
            success=True,
            data={"count": len(sessions), "sessions": sessions}
        )


class AgentKillTool(ToolSpec):
    """终止Agent"""
    name = "agent_kill"
    description = "终止正在运行的子Agent"
    permission_model = PermissionModel.DENY  # 高危禁止
    risk_level = 3
    tags = ["agent", "kill", "dangerous"]

    input_schema = {
        "type": "object",
        "properties": {
            "session_key": {"type": "string", "description": "要终止的会话key"}
        },
        "required": ["session_key"]
    }

    def execute(self, session_key: str, **kwargs) -> ToolResult:
        can, reason = self.can_execute()
        if not can:
            return ToolResult(success=False, error=reason)
        AgentSession.update_status(session_key, "failed")
        return ToolResult(success=True, data={"message": f"已终止: {session_key}"})


if __name__ == "__main__":
    print("=== AgentTool 验证 ===")

    # 生成子Agent
    spawn = AgentTool()
    r1 = spawn.execute(
        role="intel",
        task="搜集今日A股热点板块",
        task_type="research"
    )
    print(f"spawn: {r1.data}")

    session_key = r1.data["session_key"]

    # 查看状态
    status = AgentStatusTool()
    r2 = status.execute()
    print(f"list: {r2.data['count']} sessions")
