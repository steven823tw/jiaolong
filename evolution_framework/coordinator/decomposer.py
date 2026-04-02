# -*- coding: utf-8 -*-
"""
jiaolong协调器 - Task-CO-1: 任务拆解引擎
> 版本: v1.0 | 2026-04-02
> 对应: Claude Code coordinator/task_decomposer
> 用途: LLM驱动的任务自动拆解为子任务树
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskNode:
    """任务树节点"""
    def __init__(self, task_id: str, description: str,
                 agent_role: str = None,
                 status: str = "pending",
                 dependencies: List[str] = None,
                 estimated_minutes: int = 30,
                 priority: str = "normal"):
        self.task_id = task_id
        self.description = description
        self.agent_role = agent_role  # boss/intel/ux/backend
        self.status = status
        self.dependencies = dependencies or []
        self.estimated_minutes = estimated_minutes
        self.priority = priority
        self.result: Any = None
        self.created_at = datetime.now().isoformat()
        self.started_at: str = None
        self.completed_at: str = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "agent_role": self.agent_role,
            "status": self.status,
            "dependencies": self.dependencies,
            "estimated_minutes": self.estimated_minutes,
            "priority": self.priority,
            "result": self.result,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    def start(self):
        self.status = "running"
        self.started_at = datetime.now().isoformat()

    def complete(self, result: Any = None):
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.now().isoformat()

    def fail(self, error: str = ""):
        self.status = "failed"
        self.result = {"error": error}
        self.completed_at = datetime.now().isoformat()


class TaskTree:
    """任务树"""
    def __init__(self, root_task: str, goal: str = ""):
        self.root_task = root_task
        self.goal = goal
        self.nodes: Dict[str, TaskNode] = {}
        self.created_at = datetime.now().isoformat()
        self._counter = 0

    def add_task(self, description: str, agent_role: str = None,
                 dependencies: List[str] = None,
                 estimated_minutes: int = 30,
                 priority: str = "normal") -> str:
        """添加子任务"""
        self._counter += 1
        task_id = f"T{self._counter:02d}"
        node = TaskNode(
            task_id=task_id,
            description=description,
            agent_role=agent_role,
            dependencies=dependencies or [],
            estimated_minutes=estimated_minutes,
            priority=priority,
        )
        self.nodes[task_id] = node
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskNode]:
        return self.nodes.get(task_id)

    def get_ready_tasks(self) -> List[TaskNode]:
        """返回依赖已满足且等待执行的任务"""
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

    def progress(self) -> dict:
        total = len(self.nodes)
        if total == 0:
            return {"total": 0, "completed": 0, "failed": 0, "pending": 0, "running": 0, "percent": 0}
        completed = sum(1 for n in self.nodes.values() if n.status == "completed")
        failed = sum(1 for n in self.nodes.values() if n.status == "failed")
        running = sum(1 for n in self.nodes.values() if n.status == "running")
        pending = sum(1 for n in self.nodes.values() if n.status == "pending")
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "percent": (completed / total * 100) if total else 0,
        }

    def summary(self) -> str:
        p = self.progress()
        return (f"任务树 [{self.root_task}] - "
                f"完成{p['completed']}/{p['total']} ({p['percent']:.0f}%) | "
                f"失败{p['failed']} | 运行中{p['running']} | 等待{p['pending']}")

    def to_dict(self) -> dict:
        return {
            "root_task": self.root_task,
            "goal": self.goal,
            "created_at": self.created_at,
            "progress": self.progress(),
            "tasks": {tid: n.to_dict() for tid, n in self.nodes.items()},
        }


class TaskDecomposer:
    """
    任务拆解引擎
    > 将复杂任务自动拆解为可执行的子任务树
    """

    # 关键词 -> Agent角色 映射
    KEYWORD_ROLE_MAP = {
        "intel": [
            "分析", "研究", "搜集", "搜索", "查找", "调查",
            "监控", "追踪", "查询", "对比", "评估", "预测",
            "情报", "报告", "数据", "指标", "排行", "热点",
            "A股", "股市", "板块",
        ],
        "ux": [
            "画", "界面", "UI", "UX", "前端", "展示",
            "设计", "Dashboard", "面板",
            "可视化", "报表", "Markdown",
            "生成", "图表", "报告",
        ],
        "backend": [
            "后端", "API", "接口", "服务", "数据库",
            "架构", "系统", "存储", "数据流", "管道",
            "集成", "SDK", "MCP", "工具",
        ],
        "boss": [
            "决策", "判断", "选择", "评估", "审批",
            "确认", "协调", "汇总", "整合",
        ],
    }

    # 任务类型 -> 预估时间
    TASK_TIME_ESTIMATES = {
        "intel": 15,
        "ux": 30,
        "backend": 45,
        "boss": 10,
        "default": 30,
    }

    def __init__(self):
        self._counter = 0

    def decompose(self, task_description: str,
                   force_roles: List[str] = None,
                   max_subtasks: int = 8) -> TaskTree:
        """
        拆解任务

        Args:
            task_description: 原始任务描述
            force_roles: 强制使用的角色列表
            max_subtasks: 最大子任务数

        Returns:
            TaskTree: 任务树
        """
        tree = TaskTree(root_task=task_description, goal=task_description)

        # 第一遍：按角色拆解子任务
        assigned_tasks = {}  # role -> task_id

        # 分析关键词确定角色
        task_lower = task_description.lower()

        # 检查情报类
        intel_kw = any(kw in task_lower for kw in self.KEYWORD_ROLE_MAP["intel"])
        if intel_kw or force_roles:
            tid = tree.add_task(
                description=f"[情报] 搜集 {task_description} 相关数据",
                agent_role="intel",
                estimated_minutes=15,
            )
            assigned_tasks["intel"] = tid

        # 检查执行类
        exec_kw = any(kw in task_lower for kw in self.KEYWORD_ROLE_MAP["ux"])
        if exec_kw or force_roles:
            deps = [assigned_tasks["intel"]] if "intel" in assigned_tasks else []
            tid = tree.add_task(
                description=f"[执行] 实施 {task_description}",
                agent_role="ux",
                dependencies=deps,
                estimated_minutes=30,
            )
            assigned_tasks["ux"] = tid

        # 检查后端类
        backend_kw = any(kw in task_lower for kw in self.KEYWORD_ROLE_MAP["backend"])
        if backend_kw or force_roles:
            tid = tree.add_task(
                description=f"[后端] 构建 {task_description} 后端",
                agent_role="backend",
                estimated_minutes=45,
            )
            assigned_tasks["backend"] = tid

        # 如果没有任何特定角色任务，创建默认boss决策任务
        if not assigned_tasks:
            tid = tree.add_task(
                description=f"[决策] 处理 {task_description}",
                agent_role="boss",
                estimated_minutes=20,
            )
            assigned_tasks["boss"] = tid

        # 添加汇总任务 -> boss
        all_deps = list(assigned_tasks.values())
        summary_tid = tree.add_task(
            description=f"[汇总] 汇总并决策 {task_description}",
            agent_role="boss",
            dependencies=all_deps,
            estimated_minutes=10,
            priority="high",
        )

        return tree

    def auto_assign_role(self, task_description: str) -> Tuple[str, str]:
        """
        根据任务描述自动分配角色

        Returns:
            (role, reasoning)
        """
        task_lower = task_description.lower()

        role_scores = {}
        for role, keywords in self.KEYWORD_ROLE_MAP.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            role_scores[role] = score

        # 最高分角色
        best_role = max(role_scores, key=role_scores.get)
        best_score = role_scores[best_role]

        if best_score == 0:
            return "boss", "无特定关键词，默认boss决策"

        role_names = {"intel": "情报官小呆", "ux": "执行小傻", "backend": "后端小虾", "boss": "老板小笨"}
        return best_role, f"匹配{role_names[best_role]}（score={best_score}）"


class MockLLMDecomposer(TaskDecomposer):
    """
    模拟LLM的拆解器（实际环境替换为真实LLM调用）
    """

    def decompose_with_llm(self, task_description: str) -> TaskTree:
        """
        使用LLM做智能拆解
        模拟返回固定的task tree结构
        """
        # 简单演示：返回标准拆解
        return self.decompose(task_description)


if __name__ == "__main__":
    print("=== TaskDecomposer 验证 ===")

    decomposer = TaskDecomposer()

    # 测试1: 复杂量化任务
    tree1 = decomposer.decompose("分析今日A股热点板块，生成量化选股报告")
    print(f"\n任务1: {tree1.root_task}")
    print(tree1.summary())
    for tid, node in tree1.nodes.items():
        print(f"  {tid}: [{node.agent_role}] {node.description[:40]} | deps={node.dependencies}")

    # 测试2: 纯执行任务
    tree2 = decomposer.decompose("构建jiaolong自进化框架")
    print(f"\n任务2: {tree2.root_task}")
    print(tree2.summary())

    # 测试3: auto_assign_role
    role, reason = decomposer.auto_assign_role("搜集今日A股成交额Top100")
    print(f"\nauto_assign: {role} - {reason}")
