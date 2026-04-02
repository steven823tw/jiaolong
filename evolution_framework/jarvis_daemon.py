# -*- coding: utf-8 -*-
"""
jiaolongDaemon服务 - 基于Windows Task Scheduler
> 版本: v1.0 | 2026-04-02
> 功能:
>   - 定时任务调度（基于Task Scheduler）
>   - 自动进化循环
>   - 记忆整理提醒
>   - 量化数据同步
>
> 安装: python jarvis_daemon.py install
> 卸载: python jarvis_daemon.py uninstall
> 状态: python jarvis_daemon.py status
> 运行: python jarvis_daemon.py run
"""
from __future__ import annotations
import sys, os, json, time, subprocess
from pathlib import Path
from datetime import datetime, timedelta

WORKSPACE = Path(r"C:\Users\steve\.openclaw\workspace")
DAEMON_DIR = WORKSPACE / "evolution_framework" / "daemon"
PID_FILE = DAEMON_DIR / "jarvis_daemon.pid"
CONFIG_FILE = DAEMON_DIR / "daemon_config.json"
LOG_FILE = DAEMON_DIR / "daemon.log"


# ─────────────────────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "version": "1.0",
    "tasks": [
        {
            "id": "memory_cleanup",
            "name": "记忆整理",
            "schedule": "daily",      # daily / hourly / interval
            "time": "20:00",           # HH:MM (for daily)
            "interval_hours": None,    # for interval
            "enabled": True,
            "script": "memory_swap_manager.py",
            "args": ["--swap"],
            "description": "每日20:00执行记忆冷热交换"
        },
        {
            "id": "quant_sync",
            "name": "量化数据同步",
            "schedule": "interval",
            "interval_hours": 4,
            "enabled": True,
            "script": None,
            "description": "每4小时同步量化数据"
        },
        {
            "id": "evolve_check",
            "name": "进化检查",
            "schedule": "daily",
            "time": "06:00",
            "enabled": True,
            "script": "evolution.py",
            "args": ["--check"],
            "description": "每日06:00检查是否需要进化"
        },
        {
            "id": "status_report",
            "name": "每日状态报告",
            "schedule": "daily",
            "time": "09:00",
            "enabled": False,
            "script": "jarvis_cli.py",
            "args": ["status_report"],
            "description": "每日09:00发送状态报告到微信"
        },
    ],
    "evolve": {
        "enabled": True,
        "auto_evolve_interval_hours": 168,  # 7天
        "min_confidence_gain": 0.1,
    },
    "notification": {
        "enabled": True,
        "on_error": True,
        "on_evolve": True,
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# PID管理
# ─────────────────────────────────────────────────────────────────────────────

def write_pid():
    DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def read_pid():
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except:
        return None


def is_running():
    """检查进程是否在运行"""
    pid = read_pid()
    if not pid:
        return False
    try:
        # Windows: tasklist
        output = subprocess.check_output(
            ["tasklist", "/FI", f"PID eq {pid}"],
            text=True, encoding="utf-8", errors="ignore"
        )
        return str(pid) in output
    except:
        return False


def clear_pid():
    if PID_FILE.exists():
        PID_FILE.unlink()


# ─────────────────────────────────────────────────────────────────────────────
# 配置管理
# ─────────────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except:
        return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# 日志
# ─────────────────────────────────────────────────────────────────────────────

def log(msg: str):
    DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")


# ─────────────────────────────────────────────────────────────────────────────
# 任务执行
# ─────────────────────────────────────────────────────────────────────────────

def run_task(task: dict) -> dict:
    """执行单个定时任务"""
    if not task.get("enabled"):
        return {"task_id": task["id"], "status": "skipped", "reason": "disabled"}

    script = task.get("script")
    if not script:
        return {"task_id": task["id"], "status": "skipped", "reason": "no_script"}

    script_path = DAEMON_DIR / script
    if not script_path.exists():
        script_path = WORKSPACE / "evolution_framework" / script

    if not script_path.exists():
        return {"task_id": task["id"], "status": "error", "reason": f"script not found: {script}"}

    try:
        args = task.get("args", [])
        cmd = [sys.executable, str(script_path)] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=300,
            cwd=str(WORKSPACE)
        )
        return {
            "task_id": task["id"],
            "status": "ok" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout[:500] if result.stdout else "",
            "stderr": result.stderr[:200] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"task_id": task["id"], "status": "error", "reason": "timeout"}
    except Exception as e:
        return {"task_id": task["id"], "status": "error", "reason": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 主循环
# ─────────────────────────────────────────────────────────────────────────────

def main_loop():
    """主循环：每分钟检查一次任务"""
    log("Jarvis Daemon 启动")
    write_pid()

    last_run: dict = {}  # task_id -> last_run timestamp
    config = load_config()

    while True:
        now = datetime.now()
        minute = now.minute

        # 每分钟检查一次
        for task in config.get("tasks", []):
            if not task.get("enabled"):
                continue

            task_id = task["id"]
            schedule = task.get("schedule", "daily")

            # 检查是否应该运行
            should_run = False

            if schedule == "daily":
                run_time = task.get("time", "00:00")
                h, m = map(int, run_time.split(":"))
                if now.hour == h and now.minute == m:
                    # 今天还没跑过
                    if last_run.get(task_id, "").startswith(now.strftime("%Y-%m-%d")):
                        should_run = False
                    else:
                        should_run = True

            elif schedule == "interval":
                interval_hours = task.get("interval_hours", 1)
                last = last_run.get(task_id)
                if last:
                    last_time = datetime.fromisoformat(last)
                    if (now - last_time).total_seconds() >= interval_hours * 3600:
                        should_run = True
                else:
                    should_run = True  # 第一次

            elif schedule == "hourly":
                if minute == 0:
                    if last_run.get(task_id, "").startswith(now.strftime("%Y-%m-%d %H:")):
                        should_run = False
                    else:
                        should_run = True

            if should_run:
                log(f"执行任务: {task['name']} ({task_id})")
                result = run_task(task)
                last_run[task_id] = now.isoformat()
                status = result.get("status", "?")
                log(f"任务完成: {task_id} -> {status}")

        # 休眠到下一分钟
        time.sleep(60 - datetime.now().second)


# ─────────────────────────────────────────────────────────────────────────────
# Windows Task Scheduler 集成
# ─────────────────────────────────────────────────────────────────────────────

def install_scheduled_task():
    """安装Windows计划任务（开机自启）"""
    exe_path = sys.executable
    script_path = __file__
    task_name = "JarvisDaemon"

    cmd = [
        "schtasks", "/Create",
        "/TN", task_name,
        "/TR", f'"{exe_path}" "{script_path}" run',
        "/SC", "ONLOGON",
        "/F"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 计划任务已创建: {task_name} (开机自启)")
            return True
        else:
            print(f"❌ 创建失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        return False


def uninstall_scheduled_task():
    """卸载Windows计划任务"""
    task_name = "JarvisDaemon"
    cmd = ["schtasks", "/Delete", "/TN", task_name, "/F"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 计划任务已删除")
            return True
        else:
            print(f"❌ 删除失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 删除失败: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def cmd_status():
    """显示Daemon状态"""
    config = load_config()
    running = is_running()
    pid = read_pid()

    print("\n=== Jarvis Daemon 状态 ===\n")
    print(f"  进程状态: {'RUNNING' if running else 'STOPPED'} (PID: {pid or 'N/A'})")
    print(f"  配置版本: {config.get('version', '?')}")
    print(f"  定时任务: {len(config.get('tasks', []))}个")
    print()

    print("  任务列表:")
    for t in config.get("tasks", []):
        icon = "[ON]" if t.get("enabled") else "[OFF]"
        sched = t.get("schedule", "?")
        if sched == "daily":
            info = f"每日 {t.get('time', '?')}"
        elif sched == "interval":
            info = f"每{t.get('interval_hours', '?')}小时"
        elif sched == "hourly":
            info = "每小时"
        else:
            info = sched
        print(f"    {icon} {t['name']}: {info}")

    print()
    if LOG_FILE.exists():
        log_lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").strip().split("\n")
        print(f"  最近日志 ({len(log_lines)}条):")
        for line in log_lines[-5:]:
            print(f"    {line}")
    print()


def cmd_install():
    """安装Daemon"""
    config = DEFAULT_CONFIG.copy()
    save_config(config)
    print(f"✅ 配置文件已写入: {CONFIG_FILE}")
    install_scheduled_task()


def cmd_uninstall():
    """卸载Daemon"""
    uninstall_scheduled_task()
    if PID_FILE.exists():
        PID_FILE.unlink()
    print("✅ 已清理")


def cmd_run():
    """运行Daemon"""
    if is_running():
        print(f"Daemon已在运行 (PID: {read_pid()})")
        return
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nDaemon已停止")
        clear_pid()


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "status":
        cmd_status()
    elif args[0] == "install":
        cmd_install()
    elif args[0] == "uninstall":
        cmd_uninstall()
    elif args[0] == "run":
        cmd_run()
    elif args[0] == "test":
        # 测试：运行所有启用的任务
        config = load_config()
        print("=== 测试所有任务 ===\n")
        for task in config.get("tasks", []):
            if task.get("enabled"):
                print(f"测试: {task['name']}")
                result = run_task(task)
                print(f"  -> {result['status']}: {result.get('reason', '')}")
                print()
    else:
        print("用法:")
        print("  python jarvis_daemon.py         # 显示状态")
        print("  python jarvis_daemon.py status  # 显示状态")
        print("  python jarvis_daemon.py install  # 安装开机自启")
        print("  python jarvis_daemon.py uninstall  # 卸载")
        print("  python jarvis_daemon.py run     # 前台运行")
        print("  python jarvis_daemon.py test    # 测试所有任务")
