# -*- coding: utf-8 -*-
"""Tests for parallel_executor module."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parallel_executor import (
    AGENT_ROLES,
    ParallelExecutor,
    ParallelTask,
    TaskStatus,
)


class TestTaskStatus:
    def test_has_pending(self):
        assert TaskStatus.PENDING.value == "pending"

    def test_has_running(self):
        assert TaskStatus.RUNNING.value == "running"

    def test_has_completed(self):
        assert TaskStatus.COMPLETED.value == "completed"

    def test_has_failed(self):
        assert TaskStatus.FAILED.value == "failed"

    def test_has_cancelled(self):
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_has_waiting_deps(self):
        assert TaskStatus.WAITING_DEPS.value == "waiting_deps"


class TestParallelTask:
    def test_create_task(self):
        task = ParallelTask(task_id="t1", name="test", func=lambda: 42)
        assert task.task_id == "t1"
        assert task.name == "test"
        assert task.status == TaskStatus.PENDING

    def test_to_dict(self):
        task = ParallelTask(task_id="t1", name="test", func=lambda: 42)
        d = task.to_dict()
        assert d["task_id"] == "t1"
        assert d["status"] == "pending"


class TestParallelExecutor:
    def test_create_executor(self):
        executor = ParallelExecutor(max_workers=3)
        assert executor.max_workers == 3

    def test_submit_task(self):
        executor = ParallelExecutor(max_workers=2)
        task_id = executor.submit("test", lambda: 42)
        assert task_id is not None

    def test_run_single_task(self):
        executor = ParallelExecutor(max_workers=2)
        executor.submit("add", lambda: 1 + 1)
        results = executor.run_all()
        assert len(results) >= 1

    def test_run_multiple_tasks(self):
        executor = ParallelExecutor(max_workers=4)
        executor.submit("task1", lambda: 10)
        executor.submit("task2", lambda: 20)
        executor.submit("task3", lambda: 30)
        results = executor.run_all()
        assert len(results) == 3

    def test_task_with_args(self):
        executor = ParallelExecutor(max_workers=2)
        executor.submit("multiply", lambda x, y: x * y, args=(3, 4))
        results = executor.run_all()
        # Find the result
        for key, val in results.items():
            if hasattr(val, 'result'):
                assert val.result == 12

    def test_list_tasks(self):
        executor = ParallelExecutor(max_workers=2)
        executor.submit("t1", lambda: 1)
        executor.submit("t2", lambda: 2)
        tasks = executor.list_tasks()
        assert len(tasks) == 2


class TestAgentRoles:
    def test_boss_role_exists(self):
        assert "boss" in AGENT_ROLES

    def test_intel_role_exists(self):
        assert "intel" in AGENT_ROLES

    def test_ux_role_exists(self):
        assert "ux" in AGENT_ROLES

    def test_boss_strengths(self):
        assert "决策" in AGENT_ROLES["boss"]["strengths"]

    def test_intel_max_parallel(self):
        assert AGENT_ROLES["intel"]["max_parallel"] == 5
