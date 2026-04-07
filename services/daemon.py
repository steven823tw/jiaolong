# -*- coding: utf-8 -*-
"""
jiaolong Daemon 服务
> 版本: v1.0 | 2026-04-02
> 对应: Claude Code server/daemon.ts
> 用途: 后台驻守服务，支持定时任务、事件触发、自动进化
"""
from __future__ import annotations
import json, threading, time
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import queue

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace"))


class DaemonStatus(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class DaemonEvent:
    """Daemon事件"""
    def __init__(self, event_type: str, data: Any = None):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class DaemonJob:
    """Daemon定时任务"""
    def __init__(self, job_id: str, name: str,
                 func: Callable, interval_seconds: int,
                 enabled: bool = True):
        self.job_id = job_id
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.last_run: str = None
        self.next_run: str = None
        self.run_count: int = 0
        self.last_result: Any = None

    def run(self):
        """执行任务"""
        try:
            self.last_result = self.func()
            self.last_run = datetime.now().isoformat()
            self.run_count += 1
        except Exception as e:
            self.last_result = {"error": str(e)}

    def calc_next_run(self) -> str:
        """计算下次执行时间"""
        next_time = datetime.now() + timedelta(seconds=self.interval_seconds)
        self.next_run = next_time.isoformat()
        return self.next_run


class DaemonEventQueue:
    """Daemon事件队列"""
    def __init__(self):
        self._queue: List[DaemonEvent] = []
        self._lock = threading.Lock()

    def push(self, event: DaemonEvent):
        with self._lock:
            self._queue.append(event)
            if len(self._queue) > 1000:
                self._queue = self._queue[-500:]

    def pop(self) -> Optional[DaemonEvent]:
        with self._lock:
            if self._queue:
                return self._queue.pop(0)
            return None

    def peek(self, count: int = 10) -> List[DaemonEvent]:
        with self._lock:
            return self._queue[:count]

    def size(self) -> int:
        with self._lock:
            return len(self._queue)


class Daemon:
    """
    jiaolongDaemon服务
    后台驻守，支持：
    - 定时任务调度
    - 事件驱动触发
    - 自动进化循环
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._daemon_status = DaemonStatus.STOPPED
        self.jobs: Dict[str, DaemonJob] = {}
        self.event_queue = DaemonEventQueue()
        self._thread: threading.Thread = None
        self._stop_event = threading.Event()
        self.started_at: str = None
        self.handed_tasks: List[dict] = []
        self.auto_evolve_enabled = False
        self.evolve_interval_hours = 24

    # ─────────────────────────────────────────────────────────────────────────
    # 生命周期管理
    # ─────────────────────────────────────────────────────────────────────────

    def start(self):
        """启动Daemon"""
        if self._daemon_status == DaemonStatus.RUNNING:
            return {"status": "already_running"}

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._daemon_status = DaemonStatus.RUNNING
        self.started_at = datetime.now().isoformat()
        return {"status": "started", "started_at": self.started_at}

    def stop(self):
        """停止Daemon"""
        if self._daemon_status == DaemonStatus.STOPPED:
            return {"status": "already_stopped"}

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._daemon_status = DaemonStatus.STOPPED
        return {"status": "stopped", "uptime": self._get_uptime()}

    def pause(self):
        """暂停Daemon"""
        if self._daemon_status != DaemonStatus.RUNNING:
            return {"status": "not_running"}
        self._daemon_status = DaemonStatus.PAUSED
        return {"status": "paused"}

    def resume(self):
        """恢复Daemon"""
        if self._daemon_status != DaemonStatus.PAUSED:
            return {"status": "not_paused"}
        self._daemon_status = DaemonStatus.RUNNING
        return {"status": "resumed"}

    def _run_loop(self):
        """主循环"""
        while not self._stop_event.is_set():
            if self._daemon_status == DaemonStatus.RUNNING:
                # 执行到期的定时任务
                self._check_jobs()

                # 处理事件队列
                self._process_events()

                # 自动进化检查
                if self.auto_evolve_enabled:
                    self._check_auto_evolve()

            time.sleep(1)

    def _check_jobs(self):
        """检查并执行到期的任务"""
        now = datetime.now()
        for job in list(self.jobs.values()):
            if not job.enabled:
                continue
            if job.last_run is None:
                job.run()
                job.calc_next_run()
            else:
                last = datetime.fromisoformat(job.last_run)
                if (now - last).total_seconds() >= job.interval_seconds:
                    job.run()
                    job.calc_next_run()

    def _process_events(self):
        """处理事件队列"""
        while True:
            event = self.event_queue.pop()
            if not event:
                break
            self._handle_event(event)

    def _handle_event(self, event: DaemonEvent):
        """处理单个事件"""
        if event.event_type == "on_timer":
            pass  # 定时器事件
        elif event.event_type == "on_heartbeat":
            self._handle_heartbeat(event.data)
        elif event.event_type == "on_message":
            self._handle_message(event.data)
        elif event.event_type == "auto_evolve":
            self._run_auto_evolve()

    def _handle_heartbeat(self, data: dict):
        """处理心跳"""
        # 检查COCO服务器状态
        pass

    def _handle_message(self, data: dict):
        """处理消息"""
        pass

    def _check_auto_evolve(self):
        """检查是否需要自动进化"""
        pass

    def _run_auto_evolve(self):
        """运行自动进化"""
        # 读取当前状态 -> 提出假设 -> 小范围验证
        pass

    def _get_uptime(self) -> str:
        """获取运行时间"""
        if not self.started_at:
            return "0s"
        start = datetime.fromisoformat(self.started_at)
        delta = datetime.now() - start
        return str(delta)

    # ─────────────────────────────────────────────────────────────────────────
    # 任务管理
    # ─────────────────────────────────────────────────────────────────────────

    def add_job(self, name: str, func: Callable,
                 interval_seconds: int = 3600,
                 job_id: str = None) -> str:
        """添加定时任务"""
        job_id = job_id or f"job-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        job = DaemonJob(
            job_id=job_id,
            name=name,
            func=func,
            interval_seconds=interval_seconds,
        )
        self.jobs[job_id] = job
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """移除定时任务"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            return True
        return False

    def enable_job(self, job_id: str) -> bool:
        """启用任务"""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = True
            return True
        return False

    def disable_job(self, job_id: str) -> bool:
        """禁用任务"""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = False
            return True
        return False

    def list_jobs(self) -> List[dict]:
        """列出所有任务"""
        return [
            {
                "job_id": j.job_id,
                "name": j.name,
                "enabled": j.enabled,
                "interval_seconds": j.interval_seconds,
                "last_run": j.last_run,
                "next_run": j.next_run,
                "run_count": j.run_count,
            }
            for j in self.jobs.values()
        ]

    def run_job(self, job_id: str):
        """手动触发任务"""
        if job_id in self.jobs:
            self.jobs[job_id].run()
            return {"success": True, "result": self.jobs[job_id].last_result}
        return {"success": False, "error": f"任务不存在: {job_id}"}

    # ─────────────────────────────────────────────────────────────────────────
    # 事件管理
    # ─────────────────────────────────────────────────────────────────────────

    def emit(self, event_type: str, data: Any = None):
        """发送事件"""
        event = DaemonEvent(event_type, data)
        self.event_queue.push(event)

    def get_events(self, count: int = 10) -> List[dict]:
        """获取最近事件"""
        events = self.event_queue.peek(count)
        return [e.to_dict() for e in events]

    # ─────────────────────────────────────────────────────────────────────────
    # 自动进化配置
    # ─────────────────────────────────────────────────────────────────────────

    def enable_auto_evolve(self, interval_hours: int = 24):
        """启用自动进化"""
        self.auto_evolve_enabled = True
        self.evolve_interval_hours = interval_hours
        # 添加进化任务
        self.add_job(
            name="auto_evolve",
            func=lambda: self.emit("auto_evolve"),
            interval_seconds=interval_hours * 3600,
            job_id="auto_evolve",
        )
        return {"enabled": True, "interval_hours": interval_hours}

    def disable_auto_evolve(self):
        """禁用自动进化"""
        self.auto_evolve_enabled = False
        self.remove_job("auto_evolve")
        return {"enabled": False}

    # ─────────────────────────────────────────────────────────────────────────
    # 状态
    # ─────────────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        """获取Daemon状态"""
        jobs_summary = {
            "total": len(self.jobs),
            "enabled": sum(1 for j in self.jobs.values() if j.enabled),
            "disabled": sum(1 for j in self.jobs.values() if not j.enabled),
        }
        return {
            "status": self._daemon_status.value,
            "started_at": self.started_at,
            "uptime": self._get_uptime(),
            "jobs": jobs_summary,
            "event_queue_size": self.event_queue.size(),
            "auto_evolve_enabled": self.auto_evolve_enabled,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 内置Daemon任务
# ─────────────────────────────────────────────────────────────────────────────

def _heartbeat_check():
    """心跳检查任务"""
    # 检查COCO服务器
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:5173/", timeout=3)
        return {"coco": "up"}
    except Exception:
        return {"coco": "down"}


def _extract_memories_task():
    """记忆提取任务"""
    try:
        import sys
        sys.path.insert(0, str(WORKSPACE))
        from extract_memories_omlx import run_extract
        # 读取今日会话
        today_files = sorted((WORKSPACE / "memory").glob("2026-04-*.md"))
        if today_files:
            conv = today_files[-1].read_text(encoding="utf-8")
            report = run_extract(conv, dry_run=False)
            return {"extracted": report.get("added", 0)}
    except Exception as e:
        return {"error": str(e)}
    return {"extracted": 0}


# ─────────────────────────────────────────────────────────────────────────────
# CLI入口
# ─────────────────────────────────────────────────────────────────────────────

def get_daemon() -> Daemon:
    """获取Daemon单例"""
    return Daemon()


if __name__ == "__main__":
    print("=== Daemon 验证 ===")

    daemon = Daemon()

    # 状态
    print(f"初始状态: {daemon.status()}")

    # 启动
    result = daemon.start()
    print(f"启动: {result}")

    # 添加任务
    job1 = daemon.add_job(
        name="心跳检查",
        func=_heartbeat_check,
        interval_seconds=10,
    )
    print(f"添加任务: {job1}")

    job2 = daemon.add_job(
        name="记忆提取",
        func=_extract_memories_task,
        interval_seconds=60,
    )
    print(f"添加任务: {job2}")

    # 立即运行一个任务
    daemon.run_job(job1)

    # 列出任务
    jobs = daemon.list_jobs()
    print(f"任务列表: {len(jobs)}")
    for j in jobs:
        print(f"  [{j['job_id']}] {j['name']} enabled={j['enabled']} last_run={j['last_run']}")

    # 状态
    print(f"\n状态: {daemon.status()}")

    # 停止
    import time
    time.sleep(2)
    stop_result = daemon.stop()
    print(f"\n停止: {stop_result}")
