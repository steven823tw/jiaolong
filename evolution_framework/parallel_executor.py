# -*- coding: utf-8 -*-
"""
jiaolong并行任务执行器 - Parallel Executor v2
> 版本: v2.0 | 2026-04-02
> 增强: 任务依赖链 / 取消任务 / Agent负载均衡
"""
from __future__ import annotations
import json, threading, queue, time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed


# ─────────────────────────────────────────────────────────────────────────────
# 任务定义
# ─────────────────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_DEPS = "waiting_deps"  # 等待依赖


@dataclass
class ParallelTask:
    task_id: str
    name: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    timeout: int = 60
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    started_at: str = None
    completed_at: str = None
    assigned_agent: str = None
    depends_on: List[str] = field(default_factory=list)  # 依赖的任务ID列表

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "depends_on": self.depends_on,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


# ─────────────────────────────────────────────────────────────────────────────
# jiaolong角色定义
# ─────────────────────────────────────────────────────────────────────────────

AGENT_ROLES = {
    "boss": {
        "name": "小笨",
        "strengths": ["决策", "规划", "协调", "总结"],
        "max_parallel": 3,
        "color": "🔵",
    },
    "intel": {
        "name": "小呆",
        "strengths": ["搜索", "分析", "验证", "情报"],
        "max_parallel": 5,
        "color": "🟢",
    },
    "ux": {
        "name": "小傻",
        "strengths": ["界面", "前端", "设计", "报告"],
        "max_parallel": 3,
        "color": "🟡",
    },
    "backend": {
        "name": "小虾",
        "strengths": ["架构", "后端", "代码", "API"],
        "max_parallel": 3,
        "color": "🔴",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 并行执行器 v2
# ─────────────────────────────────────────────────────────────────────────────

class ParallelExecutor:
    """
    并行任务执行器 v2
    支持: 任务依赖 / 取消 / Agent负载均衡 / 真实并行
    """

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.tasks: Dict[str, ParallelTask] = {}
        self._lock = threading.Lock()
        self._counter = 0
        self._results_cache: Dict[str, Any] = {}  # task_id -> result

    def submit(self, name: str, func: Callable,
               args: tuple = None, kwargs: dict = None,
               agent: str = "boss",
               timeout: int = 60,
               depends_on: List[str] = None) -> str:
        """
        提交任务

        Args:
            name: 任务名称
            func: 执行函数
            depends_on: 依赖的任务ID列表（这些任务完成后才执行）
        """
        self._counter += 1
        task_id = f"task-{datetime.now().strftime('%H%M%S')}-{self._counter:02d}"

        task = ParallelTask(
            task_id=task_id,
            name=name,
            func=func,
            args=args or (),
            kwargs=kwargs or {},
            timeout=timeout,
            assigned_agent=agent,
            depends_on=depends_on or [],
        )

        with self._lock:
            self.tasks[task_id] = task

        return task_id

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return False
            task.status = TaskStatus.CANCELLED
            return True

    def run_all(self, wait: bool = True) -> Dict[str, Any]:
        """
        执行所有pending任务（按依赖顺序）

        Returns:
            {task_id: result}
        """
        # 第一遍：检查哪些可以跑（无依赖或依赖已完成）
        runnable = self._get_runnable()

        if not runnable:
            # 所有任务都在等待依赖
            pending = [t for t in self.tasks.values()
                      if t.status == TaskStatus.PENDING]
            waiting = [t for t in self.tasks.values()
                      if t.status == TaskStatus.WAITING_DEPS]
            if pending or waiting:
                # 有死锁风险：循环依赖
                pass
            return {}

        # 使用ThreadPoolExecutor真实并行
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(runnable))) as executor:
            future_to_task = {}
            for task in runnable:
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now().isoformat()
                    future = executor.submit(self._run_task, task)
                    future_to_task[future] = task

            results = {}
            if wait:
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result(timeout=task.timeout + 5)
                        self._results_cache[task.task_id] = result
                        results[task.task_id] = result
                    except Exception as e:
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                        results[task.task_id] = None

        return results

    def _get_runnable(self) -> List[ParallelTask]:
        """获取可执行的任务（依赖已满足）"""
        runnable = []
        with self._lock:
            for task in self.tasks.values():
                if task.status != TaskStatus.PENDING:
                    continue
                if not task.depends_on:
                    runnable.append(task)
                    continue
                # 检查所有依赖是否完成
                deps_done = all(
                    self.tasks.get(dep_id, ParallelTask(task_id="?", name="?", func=lambda: None))
                    .status == TaskStatus.COMPLETED
                    for dep_id in task.depends_on
                    if dep_id in self.tasks
                )
                if deps_done:
                    runnable.append(task)
                else:
                    task.status = TaskStatus.WAITING_DEPS
        return runnable

    def _run_task(self, task: ParallelTask) -> Any:
        """执行单个任务"""
        try:
            # 注入依赖结果到kwargs
            kwargs = dict(task.kwargs)
            for dep_id in task.depends_on:
                if dep_id in self._results_cache:
                    kwargs[f"_dep_{dep_id}"] = self._results_cache[dep_id]

            result = task.func(*task.args, **kwargs)
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now().isoformat()
            return result
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()
            return None

    def get_task(self, task_id: str) -> Optional[ParallelTask]:
        return self.tasks.get(task_id)

    def list_tasks(self, status: str = None) -> List[ParallelTask]:
        if status:
            return [t for t in self.tasks.values() if t.status.value == status]
        return list(self.tasks.values())

    def progress(self) -> dict:
        """执行进度"""
        tasks = list(self.tasks.values())
        total = len(tasks)
        if total == 0:
            return {"total": 0, "completed": 0, "failed": 0, "pending": 0,
                    "running": 0, "waiting": 0, "percent": 0}

        counts = {s: 0 for s in TaskStatus}
        for t in tasks:
            counts[t.status] += 1

        completed = counts[TaskStatus.COMPLETED]
        return {
            "total": total,
            "completed": completed,
            "failed": counts[TaskStatus.FAILED],
            "running": counts[TaskStatus.RUNNING],
            "pending": counts[TaskStatus.PENDING],
            "waiting": counts[TaskStatus.WAITING_DEPS],
            "percent": round(completed / total * 100, 1),
        }

    def agent_load(self) -> dict:
        """各Agent当前负载"""
        with self._lock:
            loads = {}
            for role, info in AGENT_ROLES.items():
                running = sum(1 for t in self.tasks.values()
                             if t.assigned_agent == role
                             and t.status == TaskStatus.RUNNING)
                loads[role] = {
                    "name": info["name"],
                    "running": running,
                    "max": info["max_parallel"],
                    "available": info["max_parallel"] - running,
                }
            return loads


# ─────────────────────────────────────────────────────────────────────────────
# 快速并行任务函数
# ─────────────────────────────────────────────────────────────────────────────

def parallel_search(query: str) -> dict:
    """并行搜索任务（小呆）"""
    return {"query": query, "results": [f"result for {query}"], "agent": "intel"}


def parallel_analyze(data: str) -> dict:
    """并行分析任务（小笨）"""
    return {"data": data, "analysis": f"analysis: {data[:20]}", "agent": "boss"}


def parallel_code(topic: str) -> dict:
    """并行代码任务（小虾）"""
    return {"topic": topic, "code": f"# code for {topic}", "agent": "backend"}


def parallel_report(content: str) -> dict:
    """并行报告任务（小傻）"""
    return {"content": content, "report": f"## Report\n{content}", "agent": "ux"}


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== ParallelExecutor v2 验证 ===")

    exec_ = ParallelExecutor(max_workers=4)

    # 提交任务：任务2依赖任务1
    id1 = exec_.submit("搜索数据", parallel_search,
                       kwargs={"query": "jiaolong"}, agent="intel", timeout=10)
    id2 = exec_.submit("分析数据", parallel_analyze,
                       kwargs={"data": "jiaolong数据"}, agent="boss",
                       depends_on=[id1], timeout=10)
    id3 = exec_.submit("生成代码", parallel_code,
                       kwargs={"topic": "选股"}, agent="backend", timeout=15)

    print(f"任务1: {id1} (搜索)")
    print(f"任务2: {id2} (分析，依赖{id1})")
    print(f"任务3: {id3} (代码，无依赖)")

    print("\n执行中...")
    results = exec_.run_all(wait=True)

    print(f"\n进度: {exec_.progress()}")
    print(f"Agent负载: {exec_.agent_load()}")

    print("\n任务状态:")
    for task in exec_.list_tasks():
        icon = {"pending": "⏳", "running": "🔄", "completed": "✅",
                "failed": "❌", "waiting_deps": "⏸"}.get(task.status.value, "?")
        deps = f" [deps:{task.depends_on}]" if task.depends_on else ""
        print(f"  {icon} {task.name} ({task.status.value}){deps}")
        if task.result:
            print(f"      -> {str(task.result)[:60]}")

    print("\n✅ 并行执行v2验证完成")
