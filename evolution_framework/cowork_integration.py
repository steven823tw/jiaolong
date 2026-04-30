# -*- coding: utf-8 -*-
"""
jiaolong × Claude Code Cowork 集成核心
> 版本: v5.0.0 | 2026-04-30
> 功能:
>   1. 记忆召回注入（每次对话前自动召回相关记忆）
>   2. Skills自动触发（监听消息，自动执行Skills）
>   3. jiaolong角色并行执行（整合parallel_executor）
>   4. 代码规则检查（每次写代码前自动检查）
>   5. Claude Code hooks 集成（自动记忆注入）
"""
from __future__ import annotations
import json, sys, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import os
WORKSPACE = Path(os.environ.get("JIAOLONG_WORKSPACE", str(Path.home() / ".claude" / "jiaolong")))
SYS_PROMPT_FILE = WORKSPACE / "AGENTS.md"


# ─────────────────────────────────────────────────────────────────────────────
# 导入所有模块
# ─────────────────────────────────────────────────────────────────────────────

sys.path.insert(0, str(WORKSPACE / "evolution_framework"))

from memory_recall import MemoryInjector, MemoryRetriever
from skill_trigger import AutoTrigger, SkillExecutor, register_trigger
from parallel_executor import ParallelExecutor, AGENT_ROLES
from rules_engine import RulesEngine, check_rules


# ─────────────────────────────────────────────────────────────────────────────
# jiaolong集成类
# ─────────────────────────────────────────────────────────────────────────────

class JiaolongIntegration:
    """
    jiaolong × Claude Code Cowork 集成核心
    整合记忆召回/Skills触发/并行执行/规则检查
    """

    def __init__(self):
        self.recall_injector = MemoryInjector(top_k=10)
        self.skill_auto = AutoTrigger()
        self.skill_executor = SkillExecutor()
        self.parallel_exec = ParallelExecutor(max_workers=5)
        self.rules_engine = RulesEngine()
        self._recall_enabled = True
        self._skill_trigger_enabled = True
        self._rules_enabled = True   # 已启用（太早会影响开发速度）

    # ─────────────────────────────────────────────────────────────────────────
    # 记忆召回
    # ─────────────────────────────────────────────────────────────────────────

    def recall_before_message(self, message: str) -> str:
        """
        每次用户消息前调用，召回相关记忆并返回上下文

        Returns:
            格式化的记忆上下文字符串，可直接注入system prompt
        """
        if not self._recall_enabled:
            return ""

        try:
            context = self.recall_injector.build_context_prompt(message, max_memories=8)
            return context
        except Exception as e:
            return f"\n\n[记忆召回错误: {e}]\n"

    def recall_query(self, query: str, top_k: int = 10) -> dict:
        """直接查询记忆"""
        try:
            retriever = MemoryRetriever(top_k=top_k)
            memories = retriever.retrieve(query)
            if not memories:
                return {"success": True, "found": 0, "output": f"未找到与「{query}」相关的记忆"}
            lines = [f"\n## 相关记忆（{len(memories)}条）\n"]
            for i, m in enumerate(memories, 1):
                cat = m.get("category", "?")
                conf = m.get("confidence", 0)
                content = m.get("content", "")
                score = m.get("_relevance_score", 0)
                cat_emoji = {
                    "decision": "🎯", "preference": "💡", "project": "📋",
                    "goal": "🎯", "context": "📎", "knowledge": "📚",
                    "behavior": "🔄", "feedback": "💬", "investment": "💰",
                }.get(cat, "📝")
                lines.append(f"{i}. {cat_emoji} [{cat}] (置信{conf:.0%} | 相关{score:.1f})")
                lines.append(f"   {content}\n")
            return {"success": True, "found": len(memories), "output": "\n".join(lines)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────────────────────
    # Skills自动触发
    # ─────────────────────────────────────────────────────────────────────────

    def skill_auto_trigger(self, message: str) -> Optional[dict]:
        """
        检测消息中的Skill触发词，自动执行

        Returns:
            如果触发返回 {"triggered": True, "skill": str, "result": dict}
            否则返回 None
        """
        if not self._skill_trigger_enabled:
            return None

        try:
            result = self.skill_auto.process(message)
            if result.get("triggered"):
                return result
            return None
        except Exception as e:
            return None

    def skill_execute(self, skill_name: str, params: dict = None) -> dict:
        """直接执行指定Skill"""
        try:
            return self.skill_executor.execute(skill_name, params or {})
        except Exception as e:
            return {"success": False, "error": str(e)}

    def skill_list(self) -> List[dict]:
        """列出所有可用Skills"""
        skills_dir = WORKSPACE / "evolution_framework" / "skills"
        skills = []
        for d in skills_dir.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                md = (d / "SKILL.md").read_text(encoding="utf-8")
                # 提取触发词
                triggers = re.findall(r"`(/?\w+)`", md)
                # 提取描述
                desc_match = re.search(r"> (.+)", md)
                desc = desc_match.group(1) if desc_match else ""
                skills.append({
                    "name": d.name,
                    "description": desc,
                    "triggers": triggers[:5],
                    "path": str(d)
                })
        return skills

    def register_custom_trigger(self, keyword: str, skill_name: str):
        """注册自定义触发词"""
        register_trigger(keyword, skill_name)

    # ─────────────────────────────────────────────────────────────────────────
    # 并行执行
    # ─────────────────────────────────────────────────────────────────────────

    def parallel_submit(self, name: str, func_name: str, args: dict = None,
                       agent: str = "boss", timeout: int = 60) -> str:
        """
        提交并行任务

        Args:
            name: 任务名称
            func_name: 函数名（parallel_search/parallel_analyze/parallel_code/parallel_report）
            args: 函数参数
            agent: Agent角色
            timeout: 超时秒

        Returns:
            task_id
        """
        from parallel_executor import (
            parallel_search, parallel_analyze, parallel_code, parallel_report
        )
        func_map = {
            "parallel_search": parallel_search,
            "parallel_analyze": parallel_analyze,
            "parallel_code": parallel_code,
            "parallel_report": parallel_report,
        }
        func = func_map.get(func_name)
        if not func:
            return None
        return self.parallel_exec.submit(
            name=name, func=func, kwargs=args or {},
            agent=agent, timeout=timeout
        )

    def parallel_run_all(self) -> dict:
        """执行所有pending任务"""
        return self.parallel_exec.run_all(wait=True)

    def parallel_progress(self) -> dict:
        """获取并行执行进度"""
        return self.parallel_exec.progress()

    def parallel_status(self, task_id: str = None) -> dict:
        """获取任务状态"""
        if task_id:
            task = self.parallel_exec.get_task(task_id)
            if task:
                return {"task_id": task_id, **task.to_dict()}
            return {"error": f"任务不存在: {task_id}"}
        tasks = self.parallel_exec.list_tasks()
        return {
            "count": len(tasks),
            "progress": self.parallel_exec.progress(),
            "tasks": [t.to_dict() for t in tasks[-10:]]  # 最近10个
        }

    def agent_roles(self) -> dict:
        """获取jiaolongAgent角色信息"""
        return AGENT_ROLES

    # ─────────────────────────────────────────────────────────────────────────
    # 代码规则检查
    # ─────────────────────────────────────────────────────────────────────────

    def check_code_rules(self, file_path: str) -> dict:
        """检查代码文件规则"""
        if not self._rules_enabled:
            return {"enabled": False, "message": "代码规则检查已禁用"}
        result = check_rules(file_path)
        return result

    def check_content_rules(self, content: str, file_path: str = "temp.py") -> dict:
        """检查代码内容规则"""
        if not self._rules_enabled:
            return {"enabled": False}
        violations = self.rules_engine.check_content(content, file_path)
        return {
            "enabled": True,
            "violations_count": len(violations),
            "passed": len(violations) == 0,
            "violations": [
                {"rule": v.rule, "level": v.level.value, "message": v.message,
                 "fix": v.fix_suggestion}
                for v in violations
            ]
        }

    def enable_rules(self):
        """启用代码规则检查"""
        self._rules_enabled = True

    def disable_rules(self):
        """禁用代码规则检查"""
        self._rules_enabled = False

    # ─────────────────────────────────────────────────────────────────────────
    # 配置
    # ─────────────────────────────────────────────────────────────────────────

    def enable_recall(self):
        self._recall_enabled = True

    def disable_recall(self):
        self._recall_enabled = False

    def enable_skill_trigger(self):
        self._skill_trigger_enabled = True

    def disable_skill_trigger(self):
        self._skill_trigger_enabled = False

    def status(self) -> dict:
        """获取集成状态"""
        skills = self.skill_list()
        return {
            "recall_enabled": self._recall_enabled,
            "skill_trigger_enabled": self._skill_trigger_enabled,
            "rules_enabled": self._rules_enabled,
            "skills_count": len(skills),
            "parallel_workers": self.parallel_exec.max_workers,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 全局实例
# ─────────────────────────────────────────────────────────────────────────────

jiaolong = JiaolongIntegration()


# ─────────────────────────────────────────────────────────────────────────────
# CLI / 快速入口
# ─────────────────────────────────────────────────────────────────────────────

def recall(query: str) -> dict:
    """快速记忆召回"""
    return jiaolong.recall_query(query)


def trigger(message: str) -> Optional[dict]:
    """快速Skills触发"""
    return jiaolong.skill_auto_trigger(message)


def execute(skill: str, **kwargs) -> dict:
    """快速Skill执行"""
    return jiaolong.skill_execute(skill, kwargs)


def parallel(name: str, func: str, args: dict = None, agent: str = "boss") -> str:
    """快速并行任务提交"""
    return jiaolong.parallel_submit(name, func, args, agent)


def check(file_path: str) -> dict:
    """快速规则检查"""
    return jiaolong.check_code_rules(file_path)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    print("=== jiaolong × OpenClaw 集成验证 ===")

    # 状态
    print(f"\n状态: {jiaolong.status()}")

    # 记忆召回
    print("\n--- 记忆召回 ---")
    for q in ["jiaolong", "COCO"]:
        r = jiaolong.recall_query(q)
        print(f"[{q}] found={r.get('found', 0)}")

    # Skills列表
    print("\n--- Skills列表 ---")
    skills = jiaolong.skill_list()
    print(f"可用Skills: {len(skills)}")
    for s in skills[:5]:
        print(f"  - {s['name']}: {s['triggers']}")

    # Agent角色
    print("\n--- jiaolongAgent角色 ---")
    roles = jiaolong.agent_roles()
    for role, info in roles.items():
        print(f"  {info['color']} {role}: {info['name']} (并行{info['max_parallel']})")

    # Skills自动触发
    print("\n--- Skills自动触发 ---")
    for msg in ["/recall jiaolong", "帮我选股", "你好"]:
        r = jiaolong.skill_auto_trigger(msg)
        if r:
            print(f"  '{msg}' -> {r['skill']} (found={r['result'].get('found', 'N/A')})")
        else:
            print(f"  '{msg}' -> (无匹配)")

    print("\n✅ jiaolong集成核心验证完成！")
