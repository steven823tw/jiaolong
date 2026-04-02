# -*- coding: utf-8 -*-
"""
jiaolong工具 - TeamCreateTool（多Agent团队）
> 版本: v1.0 | 2026-04-02
> 对应: Claude Code TeamCreateTool
> 用途: jiaolong集团4角色自动分配，复杂任务自动拆解+分配+汇总
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from .tool_spec import ToolSpec, ToolResult, PermissionModel, ProgressState
from .agent_tool import AgentSession, AgentRole, AGENT_DESCRIPTIONS


class TaskNode:
    """任务树节点"""
    def __init__(self, task_id: str, description: str,
                 assigned_to: str = None,
                 status: str = "pending",
                 dependencies: List[str] = None):
        self.task_id = task_id
        self.description = description
        self.assigned_to = assigned_to
        self.status = status  # pending/running/completed/failed
        self.dependencies = dependencies or []
        self.result: Any = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "status": self.status,
            "dependencies": self.dependencies,
            "result": self.result,
        }


class TeamTaskTree:
    """团队任务树"""
    def __init__(self, goal: str):
        self.goal = goal
        self.nodes: Dict[str, TaskNode] = {}
        self.created_at = datetime.now().isoformat()

    def add_node(self, task_id: str, description: str,
                 assigned_to: str = None,
                 dependencies: List[str] = None) -> TaskNode:
        node = TaskNode(
            task_id=task_id,
            description=description,
            assigned_to=assigned_to,
            dependencies=dependencies or [],
        )
        self.nodes[task_id] = node
        return node

    def assign(self, task_id: str, agent_role: str) -> bool:
        if task_id in self.nodes:
            self.nodes[task_id].assigned_to = agent_role
            return True
        return False

    def update_status(self, task_id: str, status: str, result: Any = None):
        if task_id in self.nodes:
            self.nodes[task_id].status = status
            if result:
                self.nodes[task_id].result = result

    def get_ready_tasks(self) -> List[TaskNode]:
        """返回所有依赖已满足且等待执行的任务"""
        ready = []
        for node in self.nodes.values():
            if node.status != "pending":
                continue
            deps_done = all(
                self.nodes[d].status == "completed"
                for d in node.dependencies
                if d in self.nodes
            )
            if deps_done:
                ready.append(node)
        return ready

    def is_complete(self) -> bool:
        return all(n.status in ("completed", "failed") for n in self.nodes.values())

    def summary(self) -> dict:
        total = len(self.nodes)
        completed = sum(1 for n in self.nodes.values() if n.status == "completed")
        failed = sum(1 for n in self.nodes.values() if n.status == "failed")
        running = sum(1 for n in self.nodes.values() if n.status == "running")
        pending = sum(1 for n in self.nodes.values() if n.status == "pending")
        return {
            "goal": self.goal,
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "progress_percent": (completed / total * 100) if total else 0,
        }


class TeamCreateTool(ToolSpec):
    """创建多Agent团队"""
    name = "team_create"
    description = "创建jiaolong集团4角色团队，自动拆解任务"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["team", "multi-agent", "orchestration"]

    input_schema = {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "团队目标（复杂任务描述）"
            },
            "auto_decompose": {
                "type": "boolean",
                "description": "是否自动拆解任务",
                "default": True
            },
            "roles": {
                "type": "array",
                "items": {"type": "string", "enum": ["boss", "intel", "ux", "backend"]},
                "description": "使用的角色（默认全部4个）"
            }
        },
        "required": ["goal"]
    }

    # 团队任务树缓存
    _teams: Dict[str, TeamTaskTree] = {}

    def _decompose_task(self, goal: str) -> List[dict]:
        """
        任务拆解（简单规则版）
        真实环境：用LLM做智能拆解
        """
        task_id_counter = 1

        def make_id():
            nonlocal task_id_counter
            tid = f"T{task_id_counter:02d}"
            task_id_counter += 1
            return tid

        # 简单规则：goal中包含关键词则拆解
        tasks = []
        goal_lower = goal.lower()

        # 情报类任务 -> 小呆
        intel_keywords = ["分析", "研究", "搜集", "查找", "搜索", "调查", "监控"]
        for kw in intel_keywords:
            if kw in goal_lower:
                tid = make_id()
                tasks.append({
                    "task_id": tid,
                    "description": f"[情报] {goal}",
                    "agent": "intel",
                    "dependencies": []
                })
                break

        # 执行类任务 -> 小傻
        exec_keywords = ["画", "做", "创建", "生成", "设计", "构建", "开发"]
        for kw in exec_keywords:
            if kw in goal_lower:
                tid = make_id()
                intel_id = tasks[0]["task_id"] if tasks else None
                tasks.append({
                    "task_id": tid,
                    "description": f"[执行] {goal}",
                    "agent": "ux",
                    "dependencies": [intel_id] if intel_id else []
                })
                break

        # 后端类任务 -> 小虾
        backend_keywords = ["接口", "API", "后端", "服务", "数据", "数据库"]
        for kw in backend_keywords:
            if kw in goal_lower:
                tid = make_id()
                tasks.append({
                    "task_id": tid,
                    "description": f"[后端] {goal}",
                    "agent": "backend",
                    "dependencies": []
                })
                break

        # 如果没有匹配，默认给小笨决策
        if not tasks:
            tid = make_id()
            tasks.append({
                "task_id": tid,
                "description": f"[决策] {goal}",
                "agent": "boss",
                "dependencies": []
            })

        # 添加汇总任务 -> 小笨
        tid = make_id()
        dep_ids = [t["task_id"] for t in tasks]
        tasks.append({
            "task_id": tid,
            "description": f"[汇总] 汇总 {goal} 的结果",
            "agent": "boss",
            "dependencies": dep_ids
        })

        return tasks

    def execute(self, goal: str,
                 auto_decompose: bool = True,
                 roles: List[str] = None,
                 **kwargs) -> ToolResult:
        """创建团队"""
        team_id = f"team-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        tree = TeamTaskTree(goal)

        if auto_decompose:
            task_specs = self._decompose_task(goal)
            for spec in task_specs:
                tree.add_node(
                    task_id=spec["task_id"],
                    description=spec["description"],
                    assigned_to=spec["agent"],
                    dependencies=spec["dependencies"],
                )
        else:
            # 单任务
            tree.add_node(
                task_id="T01",
                description=goal,
                assigned_to="boss",
                dependencies=[]
            )

        self._teams[team_id] = tree

        # 模拟生成子Agent
        ready = tree.get_ready_tasks()
        spawned = []
        for node in ready:
            session_key = AgentSession.create(
                agent_id=f"jarvis-{node.assigned_to}",
                role=AgentRole(node.assigned_to),
                task=node.description,
                parent_session=team_id,
            )
            spawned.append({
                "task_id": node.task_id,
                "agent": node.assigned_to,
                "session_key": session_key,
                "role_desc": AGENT_DESCRIPTIONS.get(AgentRole(node.assigned_to), ""),
            })
            node.status = "running"

        summary = tree.summary()
        self.update_progress(
            summary["progress_percent"],
            f"团队 {team_id} 已创建，{len(spawned)} 个任务运行中"
        )

        return ToolResult(
            success=True,
            data={
                "team_id": team_id,
                "goal": goal,
                "task_tree": {
                    "total_tasks": summary["total_tasks"],
                    "tasks": [n.to_dict() for n in tree.nodes.values()]
                },
                "spawned_agents": spawned,
                "summary": summary,
                "message": f"团队已创建: {len(spawned)} 个任务运行中"
            }
        )


class TeamStatusTool(ToolSpec):
    """查看团队状态"""
    name = "team_status"
    description = "查看团队任务进度"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["team", "query", "status"]

    input_schema = {
        "type": "object",
        "properties": {
            "team_id": {"type": "string", "description": "团队ID"}
        },
        "required": ["team_id"]
    }

    def execute(self, team_id: str, **kwargs) -> ToolResult:
        tree = TeamCreateTool._teams.get(team_id)
        if not tree:
            return ToolResult(success=False, error=f"团队不存在: {team_id}")

        summary = tree.summary()
        return ToolResult(
            success=True,
            data={
                "team_id": team_id,
                "goal": tree.goal,
                "summary": summary,
                "tasks": [n.to_dict() for n in tree.nodes.values()],
            }
        )


if __name__ == "__main__":
    print("=== TeamCreateTool 验证 ===")

    team = TeamCreateTool()

    # 测试：创建分析A股的团队
    r1 = team.execute(
        goal="分析今日A股热点板块并生成报告"
    )
    print(f"team_create: {json.dumps(r1.data, ensure_ascii=False, indent=2)}")

    team_id = r1.data["team_id"]

    # 查看状态
    status = TeamStatusTool()
    r2 = status.execute(team_id=team_id)
    print(f"\nteam_status:")
    print(f"  progress: {r2.data['summary']['progress_percent']:.0f}%")
    print(f"  pending: {r2.data['summary']['pending']}")
    print(f"  running: {r2.data['summary']['running']}")
