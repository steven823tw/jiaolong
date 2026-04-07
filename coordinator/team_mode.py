# -*- coding: utf-8 -*-
"""
jiaolong协调器 - Task-CO-5: Team模式（整合所有模块）
> 版本: v1.0 | 2026-04-02
> 用途: 整合 decomposer + role_matcher + messaging + state_sync
> 实现: /team create <goal> -> 自动拆解+分配+执行
"""
from __future__ import annotations
import json
import threading
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from .decomposer import TaskDecomposer, TaskTree
from .role_matcher import RoleMatcher, TaskToRoleAssigner, AgentRole
from .messaging import MessageBus, MessageType, SendMessageTool, ReceiveMessageTool
from .state_sync import TaskStateManager, TaskState


class TeamStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class TeamOrchestrator:
    """
    团队编排器
    整合所有协调器模块，实现自动拆解+分配+执行
    """

    _teams: Dict[str, dict] = {}

    def __init__(self):
        self.decomposer = TaskDecomposer()
        self.matcher = RoleMatcher()
        self.role_assigner = TaskToRoleAssigner()
        self.msg_bus = MessageBus()
        self.sender = SendMessageTool()
        self.receiver = ReceiveMessageTool()
        self.state_mgr = TaskStateManager()

    def create_team(self, goal: str,
                    roles: List[str] = None,
                    team_id: str = None,
                    auto_assign: bool = True) -> dict:
        """
        创建团队并自动拆解任务

        Returns:
            team_info dict
        """
        team_id = team_id or f"team-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 1. 任务拆解
        tree = self.decomposer.decompose(goal, force_roles=roles)

        # 2. 角色分配
        if auto_assign:
            assignments = self.role_assigner.assign(tree)
        else:
            assignments = {}

        # 3. 注册任务到状态管理器
        for task_id, node in tree.nodes.items():
            self.state_mgr.register_task(
                task_id=task_id,
                description=node.description,
                agent_role=node.agent_role,
                team_id=team_id,
            )

        # 4. 创建团队记录
        team_info = {
            "team_id": team_id,
            "goal": goal,
            "status": TeamStatus.CREATED.value,
            "tree": tree,
            "assignments": assignments,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
        }
        self._teams[team_id] = team_info

        # 5. 发送任务消息给各Agent
        for task_id, node in tree.nodes.items():
            if node.agent_role:
                msg = self.sender.send_task(
                    to_agent=node.agent_role,
                    task=node.description,
                    from_agent="boss",
                    context={"team_id": team_id, "task_id": task_id}
                )
                if msg:
                    self.state_mgr.update(task_id, "pending")

        # 6. 启动运行
        team_info["status"] = TeamStatus.RUNNING.value
        team_info["started_at"] = datetime.now().isoformat()

        return team_info

    def get_team(self, team_id: str) -> Optional[dict]:
        return self._teams.get(team_id)

    def get_team_progress(self, team_id: str) -> dict:
        """获取团队进度"""
        team = self._teams.get(team_id)
        if not team:
            return {}

        progress = self.state_mgr.team_progress(team_id)
        return {
            "team_id": team_id,
            "goal": team["goal"],
            "status": team["status"],
            "progress": progress,
            "started_at": team.get("started_at"),
            "completed_at": team.get("completed_at"),
        }

    def trigger_next_tasks(self, team_id: str) -> List[str]:
        """
        触发所有就绪任务（依赖已满足且pending）
        真实环境：实际spawn子Agent执行
        """
        team = self._teams.get(team_id)
        if not team:
            return []

        tree = team["tree"]
        started = []

        ready_tasks = tree.get_ready_tasks()
        for node in ready_tasks:
            if node.status == "pending":
                node.start()
                self.state_mgr.update(node.task_id, "running", progress=0)

                # 模拟：10秒后自动完成
                # 真实环境：子Agent执行完后调用 complete_task
                started.append(node.task_id)

        return started

    def complete_task(self, team_id: str, task_id: str,
                      result: Any = None):
        """完成任务"""
        team = self._teams.get(team_id)
        if not team:
            return

        tree = team["tree"]
        node = tree.get_task(task_id)
        if not node:
            return

        node.complete(result=result)
        self.state_mgr.update(task_id, "completed", progress=100, result=result)

        # 检查是否所有任务都完成
        if tree.is_complete():
            team["status"] = TeamStatus.COMPLETED.value
            team["completed_at"] = datetime.now().isoformat()

            # 发送汇总消息给boss
            self.sender.send_result(
                to_agent="boss",
                result={"team_id": team_id, "goal": team["goal"], "status": "completed"},
            )

    def fail_task(self, team_id: str, task_id: str, error: str):
        """任务失败"""
        team = self._teams.get(team_id)
        if not team:
            return

        tree = team["tree"]
        node = tree.get_task(task_id)
        if node:
            node.fail(error)
            self.state_mgr.update(task_id, "failed", error=error)

    def abort_team(self, team_id: str):
        """中止团队"""
        team = self._teams.get(team_id)
        if team:
            team["status"] = TeamStatus.ABORTED.value
            team["completed_at"] = datetime.now().isoformat()

    def list_teams(self) -> List[dict]:
        """列出所有团队"""
        return [
            {
                "team_id": tid,
                "goal": t["goal"],
                "status": t["status"],
                "created_at": t["created_at"],
            }
            for tid, t in self._teams.items()
        ]

    def summary(self) -> dict:
        """全局汇总"""
        teams = self.list_teams()
        total = len(teams)
        completed = sum(1 for t in teams if t["status"] == TeamStatus.COMPLETED.value)
        running = sum(1 for t in teams if t["status"] == TeamStatus.RUNNING.value)

        state_snap = self.state_mgr.snapshot()

        return {
            "total_teams": total,
            "completed": completed,
            "running": running,
            "total_tasks": state_snap["total_tasks"],
            "tasks_by_state": state_snap["by_state"],
            "teams": teams,
        }


class TeamStatusTool:
    """查看团队状态"""

    @staticmethod
    def status(team_id: str = None) -> dict:
        orchestrator = TeamOrchestrator()
        if team_id:
            return orchestrator.get_team_progress(team_id)
        return orchestrator.summary()


if __name__ == "__main__":
    print("=== TeamOrchestrator 验证 ===")

    orch = TeamOrchestrator()

    # 创建团队
    team_info = orch.create_team(
        goal="分析今日A股热点板块，生成量化选股报告"
    )
    print(f"\n创建团队: {team_info['team_id']}")
    print(f"目标: {team_info['goal']}")
    print(f"状态: {team_info['status']}")

    tree = team_info["tree"]
    print(f"\n任务树:")
    for tid, node in tree.nodes.items():
        print(f"  {tid} [{node.agent_role}] {node.description[:40]} | deps={node.dependencies}")

    # 触发就绪任务
    ready = orch.trigger_next_tasks(team_info["team_id"])
    print(f"\n触发就绪任务: {ready}")

    # 查看进度
    import time
    time.sleep(0.5)

    progress = orch.get_team_progress(team_info["team_id"])
    print(f"\n团队进度:")
    print(f"  {progress['progress']}")

    # 全局汇总
    summary = orch.summary()
    print(f"\n全局汇总: {summary['total_teams']} teams, {summary['total_tasks']} tasks")
