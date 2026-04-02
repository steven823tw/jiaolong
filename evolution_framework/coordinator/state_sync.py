# -*- coding: utf-8 -*-
"""
jiaolong协调器 - Task-CO-4: 任务状态同步
> 版本: v1.0 | 2026-04-02
> 用途: 所有子任务状态实时同步到主控
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class TaskState(str, Enum):
    PENDING = "pending"     # 等待执行
    RUNNING = "running"     # 执行中
    COMPLETED = "completed" # 已完成
    FAILED = "failed"       # 失败
    BLOCKED = "blocked"     # 被阻塞


class TaskStateRecord:
    """任务状态记录"""
    def __init__(self, task_id: str, description: str,
                 agent_role: str = None,
                 parent_team: str = None):
        self.task_id = task_id
        self.description = description
        self.agent_role = agent_role
        self.parent_team = parent_team
        self.state: TaskState = TaskState.PENDING
        self.progress_percent: float = 0.0
        self.progress_message: str = ""
        self.result: Any = None
        self.error: str = ""
        self.created_at: str = datetime.now().isoformat()
        self.started_at: str = None
        self.completed_at: str = None
        self.updated_at: str = datetime.now().isoformat()
        self.state_history: List[dict] = []

    def transition_to(self, new_state: TaskState,
                       message: str = "",
                       result: Any = None):
        """状态转换"""
        old = self.state
        self.state = new_state
        self.updated_at = datetime.now().isoformat()

        if new_state == TaskState.RUNNING and not self.started_at:
            self.started_at = datetime.now().isoformat()

        if new_state in (TaskState.COMPLETED, TaskState.FAILED):
            self.completed_at = datetime.now().isoformat()

        if message:
            self.progress_message = message
        if result is not None:
            self.result = result

        self.state_history.append({
            "from": old.value if isinstance(old, Enum) else old,
            "to": new_state.value if isinstance(new_state, Enum) else new_state,
            "timestamp": datetime.now().isoformat(),
            "message": message,
        })

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "agent_role": self.agent_role,
            "parent_team": self.parent_team,
            "state": self.state.value if isinstance(self.state, Enum) else self.state,
            "progress_percent": self.progress_percent,
            "progress_message": self.progress_message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "updated_at": self.updated_at,
        }


class TaskStateManager:
    """
    任务状态管理器（单例）
    管理所有子任务状态，支持实时同步
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._tasks: Dict[str, TaskStateRecord] = {}
        self._teams: Dict[str, List[str]] = {}  # team_id -> [task_ids]

    def register_task(self, task_id: str, description: str,
                     agent_role: str = None,
                     team_id: str = None) -> TaskStateRecord:
        """注册新任务"""
        record = TaskStateRecord(
            task_id=task_id,
            description=description,
            agent_role=agent_role,
            parent_team=team_id,
        )
        self._tasks[task_id] = record

        if team_id:
            if team_id not in self._teams:
                self._teams[team_id] = []
            if task_id not in self._teams[team_id]:
                self._teams[team_id].append(task_id)

        return record

    def get_task(self, task_id: str) -> Optional[TaskStateRecord]:
        return self._tasks.get(task_id)

    def update(self, task_id: str, state: str,
               progress: float = None,
               message: str = "",
               result: Any = None,
               error: str = "") -> bool:
        """更新任务状态"""
        record = self._tasks.get(task_id)
        if not record:
            return False

        try:
            state_enum = TaskState(state)
        except ValueError:
            return False

        record.transition_to(state_enum, message=message, result=result)

        if progress is not None:
            record.progress_percent = progress
        if error:
            record.error = error

        return True

    def get_team_tasks(self, team_id: str) -> List[TaskStateRecord]:
        """获取团队所有任务"""
        task_ids = self._teams.get(team_id, [])
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks]

    def get_all(self) -> List[TaskStateRecord]:
        """获取所有任务"""
        return list(self._tasks.values())

    def get_by_state(self, state: str) -> List[TaskStateRecord]:
        """按状态筛选"""
        try:
            state_enum = TaskState(state)
        except ValueError:
            return []
        return [r for r in self._tasks.values() if r.state == state_enum]

    def get_by_agent(self, agent_role: str) -> List[TaskStateRecord]:
        """按Agent筛选"""
        return [r for r in self._tasks.values() if r.agent_role == agent_role]

    def get_running_count(self) -> int:
        """运行中任务数"""
        return len(self.get_by_state("running"))

    def get_blocked_tasks(self) -> List[TaskStateRecord]:
        """获取所有被阻塞的任务"""
        blocked = []
        for r in self._tasks.values():
            if r.state == TaskState.PENDING:
                # 检查依赖是否都完成了
                # 需要从外部context获取依赖信息
                pass
        return blocked

    def team_progress(self, team_id: str) -> dict:
        """团队进度"""
        tasks = self.get_team_tasks(team_id)
        if not tasks:
            return {"total": 0, "completed": 0, "failed": 0, "running": 0, "pending": 0, "percent": 0}

        total = len(tasks)
        completed = sum(1 for t in tasks if t.state == TaskState.COMPLETED)
        failed = sum(1 for t in tasks if t.state == TaskState.FAILED)
        running = sum(1 for t in tasks if t.state == TaskState.RUNNING)
        pending = sum(1 for t in tasks if t.state == TaskState.PENDING)
        blocked = sum(1 for t in tasks if t.state == TaskState.BLOCKED)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "blocked": blocked,
            "percent": (completed / total * 100) if total else 0,
        }

    def snapshot(self) -> dict:
        """完整快照"""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_tasks": len(self._tasks),
            "by_state": {
                "pending": len(self.get_by_state("pending")),
                "running": len(self.get_by_state("running")),
                "completed": len(self.get_by_state("completed")),
                "failed": len(self.get_by_state("failed")),
                "blocked": len(self.get_by_state("blocked")),
            },
            "teams": {
                tid: self.team_progress(tid)
                for tid in self._teams
            },
            "tasks": {tid: r.to_dict() for tid, r in self._tasks.items()},
        }


if __name__ == "__main__":
    print("=== TaskStateManager 验证 ===")

    mgr = TaskStateManager()

    # 注册任务
    t1 = mgr.register_task("T01", "搜集A股数据", agent_role="intel", team_id="team-001")
    t2 = mgr.register_task("T02", "分析板块", agent_role="intel", team_id="team-001")
    t3 = mgr.register_task("T03", "生成报告", agent_role="ux", team_id="team-001", )

    print(f"注册任务: T01={t1.task_id}, T02={t2.task_id}, T03={t3.task_id}")

    # 更新状态
    mgr.update("T01", "running", progress=50, message="正在搜集...")
    mgr.update("T01", "completed", progress=100, result={"rows": 100})

    mgr.update("T02", "running", progress=30)
    mgr.update("T03", "pending")

    # 团队进度
    progress = mgr.team_progress("team-001")
    print(f"\n团队进度:")
    print(f"  {progress}")

    # 按Agent查看
    intel_tasks = mgr.get_by_agent("intel")
    print(f"\nintel任务: {[t.task_id for t in intel_tasks]}")

    # 快照
    snap = mgr.snapshot()
    print(f"\n快照: total={snap['total_tasks']}")
