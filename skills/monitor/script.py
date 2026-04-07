# -*- coding: utf-8 -*-
"""
monitor Skill - 主动监控系统状态
> 版本: v1.0 | 2026-04-02
> 触发: /monitor
> 功能: 检查COCO服务器/量化系统/记忆新鲜度/任务状态
"""
from __future__ import annotations
import sys
import os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.expanduser('~/.openclaw/workspace'), 'evolution_framework'))

from skill_output import ok, err, skill_main
import json
from pathlib import Path

_SECONDS_PER_DAY = 86400


@skill_main("monitor", required_params=[])
def run(target: str = "all") -> dict:
    """
    主动监控

    Args:
        target: all/coco/quant/memory/tasks
    """
    checks = []

    if target in ("all", "coco"):
        checks.append(_check_coco())

    if target in ("all", "quant"):
        checks.append(_check_quant())

    if target in ("all", "memory"):
        checks.append(_check_memory())

    if target in ("all", "tasks"):
        checks.append(_check_tasks())

    # 汇总
    ok_count = sum(1 for c in checks if c["status"] == "ok")
    warn_count = sum(1 for c in checks if c["status"] == "warn")
    error_count = sum(1 for c in checks if c["status"] == "error")

    status_icon = "✅" if error_count == 0 else "🔴"
    summary = f"检查 {len(checks)} 项: {ok_count}✅ {warn_count}🟡 {error_count}❌"

    return ok("monitor", data={"checks": checks, "summary": summary},
              summary=summary)


def _check_coco() -> dict:
    """检查COCO开发服务器"""
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://localhost:5173/",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        urllib.request.urlopen(req, timeout=3)
        return {"name": "COCO开发服务器", "status": "ok",
                "detail": "localhost:5173 在线", "icon": "✅"}
    except Exception:
        return {"name": "COCO开发服务器", "status": "warn",
                "detail": "localhost:5173 离线", "icon": "🔴"}


def _check_quant() -> dict:
    """检查量化系统"""
    quant_dir = Path(os.path.expanduser('~/.openclaw/workspace/quant'))
    if not quant_dir.exists():
        return {"name": "量化系统", "status": "warn",
                "detail": "quant目录不存在", "icon": "🟡"}

    db_file = quant_dir / "stock_data.db"
    if db_file.exists():
        import time
        age_days = (time.time() - db_file.stat().st_mtime) / _SECONDS_PER_DAY
        detail = f"stock_data.db ({age_days:.1f}天前更新)"
        if age_days > 1:
            return {"name": "量化系统", "status": "warn",
                    "detail": detail, "icon": "🟡"}
        return {"name": "量化系统", "status": "ok",
                "detail": detail, "icon": "✅"}
    return {"name": "量化系统", "status": "warn",
            "detail": "stock_data.db不存在", "icon": "🟡"}


def _check_memory() -> dict:
    """检查记忆新鲜度"""
    hot_file = Path(os.path.expanduser('~/.openclaw/workspace/memory/memory_hot.json'))
    if not hot_file.exists():
        return {"name": "记忆系统", "status": "error",
                "detail": "memory_hot.json不存在", "icon": "❌"}

    try:
        import time
        age_days = (time.time() - hot_file.stat().st_mtime) / _SECONDS_PER_DAY
        detail = f"memory_hot.json ({age_days:.1f}天前更新)"

        data = json.loads(hot_file.read_text(encoding="utf-8"))
        facts = data if isinstance(data, list) else data.get("facts", [])
        count = len(facts)

        if age_days > 1:
            return {"name": "记忆新鲜度", "status": "warn",
                    "detail": f"{detail}，{count}条记忆", "icon": "🟡"}
        return {"name": "记忆新鲜度", "status": "ok",
                "detail": f"{detail}，{count}条记忆", "icon": "✅"}
    except Exception as e:
        return {"name": "记忆系统", "status": "warn",
                "detail": f"读取异常: {e}", "icon": "🟡"}


def _check_tasks() -> dict:
    """检查今日任务"""
    exp_dir = Path(os.path.expanduser('~/.openclaw/workspace/experiments'))
    if not exp_dir.exists():
        return {"name": "实验任务", "status": "warn",
                "detail": "experiments目录不存在", "icon": "🟡"}

    try:
        results = list(exp_dir.glob("*.json"))
        today = datetime.now().strftime("%Y-%m-%d")
        today_results = [r for r in results if today in r.name]

        total = len(results)
        detail = f"共{total}个实验记录，今日{len(today_results)}个"

        return {"name": "实验任务", "status": "ok",
                "detail": detail, "icon": "✅"}
    except Exception as e:
        return {"name": "实验任务", "status": "warn",
                "detail": f"检查异常: {e}", "icon": "🟡"}


if __name__ == "__main__":
    result = run()
    print(result.get("output", str(result)))
