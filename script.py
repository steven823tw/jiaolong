# -*- coding: utf-8 -*-
"""
jiaolong AI 助手框架 - 入口 Skill

> 版本: v4.1.0 | 2026-04-02
> 功能: jiaolong框架的元入口，提供状态查询和引导
"""
from __future__ import annotations
from typing import Any, Dict


def run(command: str = "status", **kwargs) -> Dict[str, Any]:
    """
    jiaolong框架入口

    Args:
        command: status/info/modules/skills/help
    """
    if command == "status":
        return _status()
    elif command == "info":
        return _info()
    elif command == "modules":
        return _modules()
    elif command == "skills":
        return _skills_list()
    else:
        return {
            "success": True,
            "output": _help_text()
        }


def _status() -> Dict[str, Any]:
    """框架状态"""
    try:
        import sys
        import json
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from openclaw_integration import jiaolong

        s = jiaolong.status()
        hot_file = Path(__file__).parent.parent.parent / "memory" / "memory_hot.json"
        memory_count = 0
        if hot_file.exists():
            data = json.loads(hot_file.read_text(encoding="utf-8"))
            facts = data if isinstance(data, list) else data.get("facts", [])
            memory_count = len(facts)

        from evolution_framework.jarvis_daemon import load_config
        cfg = load_config()

        output = f"""
## jiaolong框架 v4.1.0 状态

**记忆召回**: {'✅ 启用' if s['recall_enabled'] else '❌ 禁用'}
**Skills触发**: {'✅ 启用' if s['skill_trigger_enabled'] else '❌ 禁用'}
**代码规则**: {'✅ 启用' if s['rules_enabled'] else '❌ 禁用'}

**可用Skills**: {s['skills_count']}个
**记忆存储**: {memory_count}条
**Daemon任务**: {len(cfg.get('tasks', []))}个

---
使用 `/recall <关键词>` 测试记忆召回
使用 `/jiaolong info` 查看详细信息
"""
        return {"success": True, "output": output}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _info() -> Dict[str, Any]:
    """框架信息"""
    output = """
## jiaolong AI 助手框架 v4.1.0

**定位**: OpenClaw 的能力放大器

### 8 大核心能力
1. 🧠 语义记忆召回 — 每次对话自动注入相关历史
2. ⚡ Skills自动触发 — 关键词即触发
3. 🔄 并行任务执行 — 多线程效率 +60%
4. 📋 clean-code规则 — 写代码自动检查
5. 🤖 LLM能力层 — 对话压缩/任务分解/记忆提取
6. 🔄 智能记忆演进 — 三层自动升降级
7. ⏰ Daemon守护 — 定时调度+进程管理
8. 🧩 任务智能分解 — 复杂任务自动拆解

### 安装
```bash
# 1. 复制 evolution_framework 到 OpenClaw workspace
# 2. 配置 openclaw.json 启用 Hooks
# 3. python evolution_framework/jarvis_cli.py status
```

### 文档
- SKILL.md (本文件) — 概览
- evolution_framework/ — 完整源码
"""
    return {"success": True, "output": output}


def _modules() -> Dict[str, Any]:
    """核心模块列表"""
    modules = [
        ("openclaw_integration", "v1.1", "集成核心，统一接口"),
        ("skill_trigger", "v1.0", "Skills自动触发引擎"),
        ("memory_recall", "v1.0", "语义记忆召回"),
        ("parallel_executor", "v2.0", "任务依赖链并行"),
        ("rules_engine", "v2.0", "clean-code规则检查"),
        ("jarvis_cli", "v1.0", "命令行工具"),
        ("jarvis_daemon", "v1.0", "定时守护服务"),
        ("skill_output", "v1.0", "统一输出格式化"),
        ("llm_core", "v1.0", "多Provider LLM管理"),
        ("context_compressor", "v1.0", "LLM对话压缩"),
        ("task_decomposer", "v1.0", "LLM任务分解"),
        ("memory_evolution", "v1.0", "三层记忆演进"),
    ]
    output = "## 核心模块 (14个)\n\n"
    for name, ver, desc in modules:
        output += f"- **{name}** ({ver}) — {desc}\n"
    return {"success": True, "output": output}


def _skills_list() -> Dict[str, Any]:
    """Skills列表"""
    skills = [
        ("recall", "/recall, 查记忆", "记忆召回"),
        ("remember", "/remember", "记忆检查"),
        ("monitor", "/monitor", "主动监控"),
        ("evolve", "/evolve, 开始进化", "自进化实验"),
        ("research", "/research, 分析", "深度研究"),
        ("simplify", "/simplify, 简化", "任务简化"),
        ("quant_screen", "/quant_screen, 选股", "量化选股"),
        ("dream", "/dream, 整合记忆", "记忆整理"),
        ("status_report", "/status_report", "状态报告"),
        ("team_analyze", "/team_analyze", "多Agent协作"),
    ]
    output = "## 可用Skills (13个)\n\n"
    for name, trigger, desc in skills:
        output += f"- **{name}** — {trigger}\n    {desc}\n"
    return {"success": True, "output": output}


def _help_text() -> str:
    return """
## jiaolong框架 v4.1.0

**用法**: /jiaolong <command>

**命令**:
- `status` — 框架状态
- `info` — 详细信息
- `modules` — 核心模块列表
- `skills` — 可用Skills列表

**示例**:
```
/jiaolong status
/jiaolong info
/jiaolong modules
/jiaolong skills
```
"""


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    result = run(cmd)
    print(result.get("output", result.get("error", "Error")))
