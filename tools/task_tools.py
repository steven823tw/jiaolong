# -*- coding: utf-8 -*-
"""
jiaolong工具 - TaskCreateTool + TaskUpdateTool
> 版本: v1.0 | 2026-04-02
> 对应: Claude Code TaskCreateTool / TaskUpdateTool
> 用途: SRE变更工单/任务系统集成
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from datetime import datetime
from .tool_spec import ToolSpec, ToolResult, PermissionModel, ProgressState


class TaskCreateTool(ToolSpec):
    """创建任务/工单"""
    name = "task_create"
    description = "创建SRE变更工单或任务"
    permission_model = PermissionModel.CONFIRM  # 需要确认
    risk_level = 2
    tags = ["task", "sre", "change"]

    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "任务标题",
                "minLength": 5,
                "maxLength": 100
            },
            "description": {
                "type": "string",
                "description": "任务详细描述"
            },
            "priority": {
                "type": "string",
                "enum": ["L1", "L2", "L3", "L4"],
                "description": "优先级（L1最高）"
            },
            "assignee": {
                "type": "string",
                "description": "负责人（默认: 小笨）",
                "default": "小笨"
            },
            "related_change_id": {
                "type": "string",
                "description": "关联的变更工单ID"
            },
            "l_category": {
                "type": "string",
                "enum": ["L1-recovery", "L2-rollback", "L3-fix", "L4-change"],
                "description": "L等级分类"
            },
            "estimated_minutes": {
                "type": "integer",
                "description": "预计完成时间（分钟）",
                "default": 60
            }
        },
        "required": ["title", "priority"]
    }

    # 任务存储（内存/文件，真实环境对接ITSM）
    _tasks: Dict[str, dict] = {}

    def execute(self, title: str, priority: str,
                 description: str = "", assignee: str = "小笨",
                 related_change_id: str = "", l_category: str = "L3-fix",
                 estimated_minutes: int = 60,
                 **kwargs) -> ToolResult:
        """创建任务"""
        task_id = f"TASK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now().isoformat()

        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "assignee": assignee,
            "related_change_id": related_change_id,
            "l_category": l_category,
            "estimated_minutes": estimated_minutes,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "created_by": "jiaolong系统",
        }

        self._tasks[task_id] = task
        self.update_progress(100, f"任务 {task_id} 已创建")

        return ToolResult(
            success=True,
            data={
                "task_id": task_id,
                "task": task,
                "message": f"任务创建成功: {title}"
            }
        )

    @classmethod
    def get_task(cls, task_id: str) -> Optional[dict]:
        return cls._tasks.get(task_id)

    @classmethod
    def list_tasks(cls, status: str = None) -> list:
        if status:
            return [t for t in cls._tasks.values() if t["status"] == status]
        return list(cls._tasks.values())


class TaskUpdateTool(ToolSpec):
    """更新任务状态"""
    name = "task_update"
    description = "更新SRE任务状态"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["task", "sre", "update"]

    input_schema = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "任务ID"
            },
            "status": {
                "type": "string",
                "enum": ["pending", "running", "completed", "failed", "blocked"],
                "description": "新状态"
            },
            "progress_percent": {
                "type": "number",
                "description": "进度百分比 0-100",
                "minimum": 0,
                "maximum": 100
            },
            "note": {
                "type": "string",
                "description": "备注/说明"
            },
            "result": {
                "type": "string",
                "description": "执行结果摘要"
            }
        },
        "required": ["task_id", "status"]
    }

    def execute(self, task_id: str, status: str,
                 progress_percent: float = None,
                 note: str = "", result: str = "",
                 **kwargs) -> ToolResult:
        """更新任务"""
        task = TaskCreateTool.get_task(task_id)
        if not task:
            return ToolResult(success=False, error=f"任务不存在: {task_id}")

        old_status = task["status"]
        task["status"] = status
        task["updated_at"] = datetime.now().isoformat()
        if note:
            task["note"] = note
        if result:
            task["result"] = result

        state_map = {
            "pending": ProgressState.PENDING,
            "running": ProgressState.RUNNING,
            "completed": ProgressState.COMPLETED,
            "failed": ProgressState.FAILED,
            "blocked": ProgressState.BLOCKED,
        }
        self.progress_state = state_map.get(status, ProgressState.PENDING)
        if progress_percent is not None:
            self.update_progress(progress_percent)
        else:
            self.update_progress(100 if status == "completed" else 50)

        return ToolResult(
            success=True,
            data={
                "task_id": task_id,
                "old_status": old_status,
                "new_status": status,
                "message": f"任务状态更新: {old_status} -> {status}"
            }
        )


class TaskQueryTool(ToolSpec):
    """查询任务"""
    name = "task_query"
    description = "查询任务列表或详情"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["task", "query", "read"]

    input_schema = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID（为空则查询列表）"},
            "status": {
                "type": "string",
                "enum": ["pending", "running", "completed", "failed", "blocked", ""],
                "description": "按状态筛选"
            },
            "assignee": {"type": "string", "description": "按负责人筛选"},
            "limit": {"type": "integer", "description": "返回数量限制", "default": 50}
        }
    }

    def execute(self, task_id: str = None, status: str = None,
                 assignee: str = None, limit: int = 50,
                 **kwargs) -> ToolResult:
        """查询任务"""
        if task_id:
            task = TaskCreateTool.get_task(task_id)
            if not task:
                return ToolResult(success=False, error=f"任务不存在: {task_id}")
            return ToolResult(success=True, data={"task": task})

        tasks = TaskCreateTool.list_tasks(status=status)
        if assignee:
            tasks = [t for t in tasks if t.get("assignee") == assignee]

        return ToolResult(
            success=True,
            data={
                "count": len(tasks),
                "tasks": tasks[:limit]
            }
        )


if __name__ == "__main__":
    print("=== TaskCreateTool 验证 ===")
    tc = TaskCreateTool()
    
    # 创建任务
    r1 = tc.execute(
        title="修复COCO服务器宕机",
        description="COCO 2.0开发服务器无响应",
        priority="L2",
        l_category="L3-fix"
    )
    print(f"创建: {r1.to_dict()}")
    
    # 查询
    tq = TaskQueryTool()
    r2 = tq.execute()
    print(f"查询列表: {r2.to_dict()}")
    
    # 更新
    tu = TaskUpdateTool()
    task_id = r1.data["task_id"]
    r3 = tu.execute(task_id=task_id, status="running", progress_percent=50)
    print(f"更新: {r3.to_dict()}")
