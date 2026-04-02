# -*- coding: utf-8 -*-
"""
jiaolong工具 - CronCreateTool（定时触发器）
> 版本: v1.0 | 2026-04-02
> 对应: OpenClaw cron 系统
> 用途: 创建定时任务、设置提醒
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from .tool_spec import ToolSpec, ToolResult, PermissionModel, ProgressState


class CronScheduleKind(str, Enum):
    """调度类型"""
    AT = "at"        # 一次性（指定时间）
    EVERY = "every"  # 周期性（间隔）
    CRON = "cron"    # Cron表达式


class CronJob:
    """定时任务记录"""
    _jobs: Dict[str, dict] = {}

    @classmethod
    def create(cls, name: str, schedule_kind: str,
               schedule_config: dict,
               payload: dict,
               enabled: bool = True,
               session_target: str = "isolated") -> str:
        job_id = f"cron-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cls._jobs[job_id] = {
            "id": job_id,
            "name": name,
            "schedule_kind": schedule_kind,
            "schedule_config": schedule_config,
            "payload": payload,
            "enabled": enabled,
            "session_target": session_target,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "next_run": cls._calc_next_run(schedule_kind, schedule_config),
            "run_count": 0,
        }
        return job_id

    @classmethod
    def get(cls, job_id: str) -> Optional[dict]:
        return cls._jobs.get(job_id)

    @classmethod
    def list_all(cls) -> List[dict]:
        return list(cls._jobs.values())

    @classmethod
    def list_enabled(cls) -> List[dict]:
        return [j for j in cls._jobs.values() if j["enabled"]]

    @classmethod
    def _calc_next_run(cls, kind: str, config: dict) -> str:
        now = datetime.now()
        if kind == "at":
            at_str = config.get("at", "")
            try:
                # 简单解析 ISO格式
                return at_str
            except:
                return (now + timedelta(hours=1)).isoformat()
        elif kind == "every":
            interval_ms = config.get("everyMs", 3600000)
            return (now + timedelta(milliseconds=interval_ms)).isoformat()
        elif kind == "cron":
            expr = config.get("expr", "0 * * * *")
            return f"下次按 cron {expr} 执行"
        return now.isoformat()

    @classmethod
    def update_last_run(cls, job_id: str):
        if job_id in cls._jobs:
            cls._jobs[job_id]["last_run"] = datetime.now().isoformat()
            cls._jobs[job_id]["run_count"] += 1


class CronCreateTool(ToolSpec):
    """创建定时任务"""
    name = "cron_create"
    description = "创建OpenClaw定时任务"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["cron", "schedule", "timer"]

    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "任务名称"},
            "schedule_kind": {
                "type": "string",
                "enum": ["at", "every", "cron"],
                "description": "调度类型"
            },
            "at_time": {
                "type": "string",
                "description": "一次性任务时间（ISO8601格式）"
            },
            "every_ms": {
                "type": "integer",
                "description": "周期间隔（毫秒）"
            },
            "cron_expr": {
                "type": "string",
                "description": "Cron表达式（如 '0 8 * * *' 表示每天8点）"
            },
            "message": {
                "type": "string",
                "description": "触发时发送的消息内容"
            },
            "session_target": {
                "type": "string",
                "enum": ["isolated", "main", "current"],
                "description": "会话目标",
                "default": "isolated"
            },
            "enabled": {
                "type": "boolean",
                "description": "是否启用",
                "default": True
            }
        },
        "required": ["name", "schedule_kind"]
    }

    def execute(self, name: str, schedule_kind: str,
                 at_time: str = None,
                 every_ms: int = None,
                 cron_expr: str = None,
                 message: str = "",
                 session_target: str = "isolated",
                 enabled: bool = True,
                 **kwargs) -> ToolResult:
        """创建定时任务"""
        # 构建schedule_config
        if schedule_kind == "at":
            if not at_time:
                return ToolResult(success=False, error="at调度需要 at_time 参数")
            schedule_config = {"kind": "at", "at": at_time}
        elif schedule_kind == "every":
            if not every_ms:
                return ToolResult(success=False, error="every调度需要 every_ms 参数")
            schedule_config = {"kind": "every", "everyMs": every_ms}
        elif schedule_kind == "cron":
            expr = cron_expr or "0 * * * *"
            tz = kwargs.get("tz", "Asia/Shanghai")
            schedule_config = {"kind": "cron", "expr": expr, "tz": tz}
        else:
            return ToolResult(success=False, error=f"未知schedule_kind: {schedule_kind}")

        # 构建payload
        payload = {
            "kind": "agentTurn",  # 或 "systemEvent"
            "message": message or f"[定时任务] {name}",
        }

        # 创建任务（模拟，实际调用cron.add）
        job_id = CronJob.create(
            name=name,
            schedule_kind=schedule_kind,
            schedule_config=schedule_config,
            payload=payload,
            enabled=enabled,
            session_target=session_target,
        )

        self.update_progress(100, f"定时任务 {job_id} 已创建")

        return ToolResult(
            success=True,
            data={
                "job_id": job_id,
                "name": name,
                "schedule": schedule_config,
                "next_run": CronJob.get(job_id)["next_run"],
                "enabled": enabled,
                "message": f"定时任务创建成功: {name}"
            }
        )


class CronListTool(ToolSpec):
    """列出定时任务"""
    name = "cron_list"
    description = "列出所有定时任务"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["cron", "query"]

    input_schema = {
        "type": "object",
        "properties": {
            "enabled_only": {
                "type": "boolean",
                "description": "仅显示启用的任务",
                "default": False
            }
        }
    }

    def execute(self, enabled_only: bool = False, **kwargs) -> ToolResult:
        jobs = CronJob.list_enabled() if enabled_only else CronJob.list_all()
        return ToolResult(
            success=True,
            data={"count": len(jobs), "jobs": jobs}
        )


class CronDeleteTool(ToolSpec):
    """删除定时任务"""
    name = "cron_delete"
    description = "删除定时任务"
    permission_model = PermissionModel.DENY  # 高危禁止直接删除
    risk_level = 3
    tags = ["cron", "delete", "dangerous"]

    input_schema = {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "任务ID"}
        },
        "required": ["job_id"]
    }

    def execute(self, job_id: str, **kwargs) -> ToolResult:
        can, reason = self.can_execute()
        if not can:
            return ToolResult(success=False, error=reason)
        if job_id in CronJob._jobs:
            del CronJob._jobs[job_id]
            return ToolResult(success=True, data={"message": f"已删除: {job_id}"})
        return ToolResult(success=False, error=f"任务不存在: {job_id}")


class ReminderTool(ToolSpec):
    """快速创建提醒（简化的cron）"""
    name = "reminder"
    description = "快速创建简单提醒"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["reminder", "quick"]

    input_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "提醒内容"},
            "minutes": {"type": "integer", "description": "多少分钟后提醒", "default": 30}
        },
        "required": ["message"]
    }

    def execute(self, message: str, minutes: int = 30,
                 **kwargs) -> ToolResult:
        at_time = (datetime.now() + timedelta(minutes=minutes)).isoformat()
        cron = CronCreateTool()
        return cron.execute(
            name=f"提醒: {message[:30]}",
            schedule_kind="at",
            at_time=at_time,
            message=message,
        )


if __name__ == "__main__":
    print("=== CronCreateTool 验证 ===")

    # 创建每日早报提醒
    cron = CronCreateTool()
    r1 = cron.execute(
        name="每日AI早报",
        schedule_kind="cron",
        cron_expr="0 8 * * *",  # 每天8点
        message="[jiaolong] 今日AI早报已生成，请查看",
    )
    print(f"cron_create: {r1.data}")

    # 创建一次性提醒
    r2 = cron.execute(
        name="测试提醒",
        schedule_kind="every",
        every_ms=60000,  # 1分钟后
        message="测试提醒",
    )
    print(f"every: {r2.data}")

    # 列出
    list_tool = CronListTool()
    r3 = list_tool.execute()
    print(f"list: {r3.data['count']} jobs")

    # 快速提醒
    rem = ReminderTool()
    r4 = rem.execute(message="COCO服务器检查", minutes=5)
    print(f"reminder: {r4.data}")
