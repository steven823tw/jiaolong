#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
jiaolong Jarvis CLI - 一站式助手命令
> 版本: v1.0 | 2026-04-02
> 用法: python jarvis_cli.py <command> [args]

命令列表:
  recall <query>              记忆召回
  recalljiaolong                  召回jiaolong相关记忆
  /recall 量化                 召回量化相关记忆
  trigger <message>           检测Skills自动触发
  skills                      列出所有Skills
  agents                      显示jiaolongAgent角色
  parallel <name> <func> [args]  提交并行任务
  status                      显示集成状态
  check <file.py>            代码规则检查
  help                        显示帮助
"""
from __future__ import annotations
import sys, json, os
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.expanduser('~/.openclaw/workspace'), 'evolution_framework'))


def cmd_recall(query: str):
    """记忆召回"""
    from openclaw_integration import jiaolong
    r = jiaolong.recall_query(query)
    if r.get("success"):
        if r.get("found", 0) > 0:
            print(r.get("output", ""))
        else:
            print(f"未找到与「{query}」相关的记忆")
    else:
        print(f"错误: {r.get('error')}")


def cmd_trigger(message: str):
    """Skills自动触发"""
    from openclaw_integration import jiaolong
    r = jiaolong.skill_auto_trigger(message)
    if r:
        skill = r["skill"]
        result = r.get("result", {})
        print(f"触发了 [{skill}]")
        if result.get("success"):
            out = result.get("output", "")
            if out:
                print(out)
            elif result.get("found") is not None:
                print(f"找到 {result.get('found')} 条结果")
            else:
                print(f"执行成功")
        else:
            print(f"错误: {result.get('error')}")
    else:
        print("没有匹配的Skills")


def cmd_skills():
    """列出所有Skills"""
    from openclaw_integration import jiaolong
    skills = jiaolong.skill_list()
    print(f"\n=== 可用Skills ({len(skills)}个) ===\n")
    for s in skills:
        triggers = ", ".join(s["triggers"][:5]) if s["triggers"] else "(无触发词)"
        print(f"  {s['name']:20s} {s['description'][:40]}")
        print(f"      触发: {triggers}\n")


def cmd_agents():
    """显示Agent角色"""
    from openclaw_integration import jiaolong
    roles = jiaolong.agent_roles()
    print("\n=== jiaolongAgent角色 ===\n")
    for role, info in roles.items():
        print(f"  {info['color']} {info['name']} ({role})")
        print(f"     专长: {', '.join(info['strengths'])}")
        print(f"     最大并行: {info['max_parallel']}\n")


def cmd_parallel(name: str, func: str, args_str: str = ""):
    """提交并行任务"""
    from openclaw_integration import jiaolong
    args = {}
    if args_str:
        for pair in args_str.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                args[k.strip()] = v.strip()

    # 确定agent
    agent_map = {
        "search": "intel", "analyze": "boss",
        "code": "backend", "report": "ux"
    }
    agent = agent_map.get(func, "boss")

    task_id = jiaolong.parallel_submit(name, func, args, agent=agent)
    if not task_id:
        print(f"未知函数: {func}")
        print(f"可用函数: parallel_search, parallel_analyze, parallel_code, parallel_report")
        return

    print(f"提交任务: {task_id} - {name} ({agent})")
    print("执行中...")

    from time import sleep
    _PARALLEL_WAIT_SECONDS = 0.5
    sleep(_PARALLEL_WAIT_SECONDS)

    results = jiaolong.parallel_run_all()
    progress = jiaolong.parallel_progress()
    print(f"\n完成: {progress['completed']}/{progress['total']} ({progress['percent']:.0f}%)")

    for tid, result in results.items():
        if result:
            print(f"  {tid}: {str(result)[:80]}")


def cmd_status():
    """显示集成状态"""
    from openclaw_integration import jiaolong
    s = jiaolong.status()
    print("\n=== jiaolong集成状态 ===\n")
    print(f"  记忆召回:      {'✅ 启用' if s['recall_enabled'] else '❌ 禁用'}")
    print(f"  Skills触发:   {'✅ 启用' if s['skill_trigger_enabled'] else '❌ 禁用'}")
    print(f"  代码规则:      {'✅ 启用' if s['rules_enabled'] else '❌ 禁用'}")
    print(f"  可用Skills:   {s['skills_count']}个")
    print(f"  并行工作线程: {s['parallel_workers']}个")
    print()


def cmd_check(file_path: str):
    """代码规则检查"""
    from openclaw_integration import jiaolong
    jiaolong.enable_rules()
    r = jiaolong.check_code_rules(file_path)
    print(f"\n=== 规则检查: {file_path} ===\n")
    if r.get("passed"):
        print("✅ 所有规则检查通过")
    else:
        print(f"❌ {r.get('violations_count')} 个违规")
        for v in r.get("violations", []):
            lvl_icon = {"error": "🔴", "warning": "🟡", "info": "🟢"}.get(v["level"], "?")
            print(f"  {lvl_icon} [{v['level']}] {v['message']}")
            if v.get("fix"):
                print(f"     💡 {v['fix']}")


def cmd_help():
    print(__doc__)


# ─────────────────────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        cmd_status()
        print("\n用法示例:")
        print("  python jarvis_cli.py recall jiaolong")
        print("  python jarvis_cli.py trigger /recall 量化")
        print("  python jarvis_cli.py skills")
        print("  python jarvis_cli.py agents")
        print("  python jarvis_cli.py parallel 搜索jiaolong parallel_search query=jiaolong")
        print("  python jarvis_cli.py status")
        print("  python jarvis_cli.py check rules_engine.py")
        sys.exit(0)

    cmd = args[0].lower()

    if cmd in ("recall", "召回"):
        query = " ".join(args[1:]) if len(args) > 1 else ""
        if not query:
            print("用法: jarvis_cli.py recall <关键词>")
        else:
            cmd_recall(query)

    elif cmd in ("trigger", "触发"):
        message = " ".join(args[1:]) if len(args) > 1 else ""
        if not message:
            print("用法: jarvis_cli.py trigger <消息>")
        else:
            cmd_trigger(message)

    elif cmd == "skills":
        cmd_skills()

    elif cmd == "agents":
        cmd_agents()

    elif cmd == "parallel":
        if len(args) < 3:
            print("用法: jarvis_cli.py parallel <名称> <函数> [参数]")
            print("函数: parallel_search, parallel_analyze, parallel_code, parallel_report")
        else:
            name = args[1]
            func = args[2]
            args_str = args[3] if len(args) > 3 else ""
            cmd_parallel(name, func, args_str)

    elif cmd == "status":
        cmd_status()

    elif cmd == "check":
        if len(args) < 2:
            print("用法: jarvis_cli.py check <文件.py>")
        else:
            cmd_check(args[1])

    elif cmd in ("help", "--help", "-h"):
        cmd_help()

    else:
        print(f"未知命令: {cmd}")
        print("用法: python jarvis_cli.py [recall|trigger|skills|agents|parallel|status|check|help]")
