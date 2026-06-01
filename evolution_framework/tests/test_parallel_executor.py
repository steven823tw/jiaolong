# -*- coding: utf-8 -*-
"""Tests for parallel_executor module."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parallel_executor import AGENT_ROLES, ParallelExecutor, ParallelTask, TaskStatus


class TestTaskStatus:
    def test_enum_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.WAITING_DEPS.value == "waiting_deps"


class TestParallelTask:
    def test_create_with_defaults(self):
        task = ParallelTask(task_id="t1", name="test", func=lambda: 42)
        assert task.task_id == "t1"
        assert task.status == TaskStatus.PENDING
        assert task.depends_on == []

    def test_to_dict(self):
        task = ParallelTask(task_id="t1", name="test", func=lambda: 42)
        d = task.to_dict()
        assert d["task_id"] == "t1"
        assert d["status"] == "pending"


class TestExecutorBasic:
    def test_create_executor(self):
        executor = ParallelExecutor(max_workers=3)
        assert executor.max_workers == 3

    def test_submit_returns_task_id(self):
        executor = ParallelExecutor(max_workers=2)
        tid = executor.submit("test", lambda: 42)
        assert tid is not None
        assert tid in executor.tasks

    def test_submit_with_agent(self):
        executor = ParallelExecutor(max_workers=2)
        tid = executor.submit("search", lambda: 1, agent="intel")
        assert executor.tasks[tid].assigned_agent == "intel"

    def test_list_tasks(self):
        executor = ParallelExecutor(max_workers=2)
        executor.submit("t1", lambda: 1)
        executor.submit("t2", lambda: 2)
        assert len(executor.list_tasks()) == 2


class TestExecutorRunAll:
    def test_single_task_completes(self):
        executor = ParallelExecutor(max_workers=2)
        tid = executor.submit("add", lambda: 1 + 1)
        results = executor.run_all()
        assert tid in results
        assert executor.tasks[tid].status == TaskStatus.COMPLETED

    def test_multiple_tasks_parallel(self):
        executor = ParallelExecutor(max_workers=4)
        tids = [executor.submit(f"t-{i}", lambda i=i: i * 10) for i in range(5)]
        results = executor.run_all()
        assert len(results) == 5
        for tid in tids:
            assert executor.tasks[tid].status == TaskStatus.COMPLETED

    def test_task_with_args(self):
        executor = ParallelExecutor(max_workers=2)
        tid = executor.submit("multiply", lambda x, y: x * y, args=(3, 4))
        results = executor.run_all()
        assert results[tid] == 12

    def test_empty_executor(self):
        assert ParallelExecutor(max_workers=2).run_all() == {}


class TestExecutorErrorHandling:
    def test_failing_task_marks_failed(self):
        executor = ParallelExecutor(max_workers=2)
        tid = executor.submit("boom", lambda: 1 / 0)
        results = executor.run_all()
        assert executor.tasks[tid].status == TaskStatus.FAILED
        assert "division" in executor.tasks[tid].error.lower()

    def test_failing_does_not_block_others(self):
        executor = ParallelExecutor(max_workers=2)
        tid_bad = executor.submit("fail", lambda: (_ for _ in ()).throw(RuntimeError("x")))
        tid_ok = executor.submit("ok", lambda: 99)
        results = executor.run_all()
        assert executor.tasks[tid_ok].status == TaskStatus.COMPLETED

    def test_exception_returns_none(self):
        executor = ParallelExecutor(max_workers=2)
        tid = executor.submit("fail", lambda: 1 / 0)
        results = executor.run_all()
        assert results[tid] is None


class TestExecutorCancellation:
    def test_cancel_pending(self):
        executor = ParallelExecutor(max_workers=1)
        tid = executor.submit("slow", lambda: 0.5)
        assert executor.cancel(tid) is True
        assert executor.tasks[tid].status == TaskStatus.CANCELLED

    def test_cancel_completed_false(self):
        executor = ParallelExecutor(max_workers=2)
        tid = executor.submit("fast", lambda: 1)
        executor.run_all()
        assert executor.cancel(tid) is False

    def test_cancel_nonexistent_false(self):
        assert ParallelExecutor(2).cancel("nope") is False


class TestExecutorDependencies:
    def test_no_dep_task_runs_immediately(self):
        """无依赖的任务应该立即执行"""
        executor = ParallelExecutor(max_workers=2)
        tid = executor.submit("independent", lambda: 42)
        results = executor.run_all()
        assert results[tid] == 42

    def test_cancelled_dep_blocks_dependent(self):
        """被取消的依赖应该阻塞依赖它的任务"""
        executor = ParallelExecutor(max_workers=2)
        tid1 = executor.submit("dep", lambda: 42)
        executor.cancel(tid1)
        tid2 = executor.submit("child", lambda: 1, depends_on=[tid1])
        results = executor.run_all()
        assert executor.tasks[tid2].status == TaskStatus.WAITING_DEPS


class TestExecutorProgress:
    def test_progress_tracks_states(self):
        executor = ParallelExecutor(max_workers=2)
        executor.submit("a", lambda: 1)
        executor.submit("b", lambda: 2)
        p = executor.progress()
        assert p["pending"] == 2
        assert p["total"] == 2
        executor.run_all()
        p = executor.progress()
        assert p["completed"] == 2
        assert p["percent"] == 100.0

    def test_progress_empty(self):
        p = ParallelExecutor().progress()
        assert p["total"] == 0


class TestExecutorThreadSafety:
    def test_concurrent_submit(self):
        executor = ParallelExecutor(max_workers=4)
        tids = []
        lock = threading.Lock()

        def submit_task(i):
            tid = executor.submit(f"task-{i}", lambda i=i: i)
            with lock:
                tids.append(tid)

        threads = [threading.Thread(target=submit_task, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(executor.tasks) == 10
        results = executor.run_all()
        assert len(results) == 10


class TestAgentRoles:
    def test_all_roles_exist(self):
        assert "boss" in AGENT_ROLES
        assert "intel" in AGENT_ROLES
        assert "ux" in AGENT_ROLES

    def test_boss_strengths(self):
        assert "决策" in AGENT_ROLES["boss"]["strengths"]

    def test_intel_max_parallel(self):
        assert AGENT_ROLES["intel"]["max_parallel"] == 5
