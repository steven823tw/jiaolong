# -*- coding: utf-8 -*-
"""
jiaolong Skills自动触发器
> 版本: v1.0 | 2026-04-02
> 对应: Claude Code skills/auto_trigger 机制
> 用途: 关键词自动触发Skills，减少重复操作
"""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

WORKSPACE = Path(r"C:\Users\steve\.openclaw\workspace")
SKILLS_DIR = WORKSPACE / "evolution_framework" / "skills"
DEFAULT_TOP_K = 10


# ─────────────────────────────────────────────────────────────────────────────
# 触发规则
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_TRIGGERS = {
    # 记忆类
    "记得": "remember",
    "查记忆": "remember",
    "查一下记忆": "recall",
    "记得什么": "recall",
    "/remember": "remember",
    "/recall": "recall",
    "召回": "recall",
    "相关记忆": "recall",

    # 进化类
    "开始进化": "evolve",
    "/evolve": "evolve",
    "开始实验": "evolve",

    # 记忆整理
    "整合记忆": "dream",
    "/dream": "dream",
    "记忆整理": "dream",

    # 主动监控
    "状态报告": "status_report",
    "/status_report": "status_report",
    "状态检查": "monitor",
    "/monitor": "monitor",

    # 任务分析
    "分析": "research",
    "/research": "research",
    "调研": "research",

    # 简化任务
    "简化": "simplify",
    "/simplify": "simplify",

    # 量化选股
    "选股": "quant_screen",
    "/quant_screen": "quant_screen",
    "筛选股票": "quant_screen",

    # 团队协作
    "团队分析": "team_analyze",
    "/team_analyze": "team_analyze",
}


class SkillTrigger:
    """
    Skills自动触发器
    监听消息，检测关键词，自动触发对应Skill
    """

    def __init__(self, custom_triggers: Dict[str, str] = None):
        """
        Args:
            custom_triggers: 自定义触发词 {keyword: skill_name}
        """
        self.triggers = dict(DEFAULT_TRIGGERS)
        if custom_triggers:
            self.triggers.update(custom_triggers)

        # 构建高效匹配
        self._sorted_triggers = sorted(
            self.triggers.items(),
            key=lambda x: -len(x[0])  # 优先匹配长词
        )

    def detect(self, message: str) -> Optional[str]:
        """
        检测消息是否包含触发词

        Returns:
            skill_name 如果匹配，否则 None
        """
        if not message:
            return None

        msg_lower = message.lower()

        # 优先匹配长词（避免短词误匹配）
        for keyword, skill_name in self._sorted_triggers:
            if keyword.lower() in msg_lower:
                return skill_name

        return None

    def detect_all(self, message: str) -> List[str]:
        """检测所有匹配的触发词（可能有多个）"""
        if not message:
            return []

        msg_lower = message.lower()
        matched = []

        for keyword, skill_name in self._sorted_triggers:
            if keyword.lower() in msg_lower:
                matched.append(skill_name)

        return matched


# ─────────────────────────────────────────────────────────────────────────────
# Skill执行器
# ─────────────────────────────────────────────────────────────────────────────

class SkillExecutor:
    """
    Skill执行器
    根据skill_name加载并执行对应Skill
    """

    def __init__(self):
        self.skills_dir = SKILLS_DIR
        self._skill_cache: Dict[str, callable] = {}

    def execute(self, skill_name: str, params: Dict[str, Any] = None,
                raw_message: str = "") -> dict:
        """
        执行Skill

        Args:
            skill_name: Skill名称
            params: 执行参数
            raw_message: 原始消息（用于解析参数）

        Returns:
            {"success": bool, "output": str, "error": str}
        """
        params = dict(params or {})

        # 从原始消息中解析参数（如果params为空）
        if not params and raw_message:
            params = self._parse_message(raw_message, skill_name)

        # 优先从Python模块执行
        result = self._execute_from_module(skill_name, params)
        if result is not None:
            return result

        # 回退：读取SKILL.md作为说明
        return self._execute_from_md(skill_name)

    def _parse_message(self, message: str, skill_name: str) -> dict:
        """从消息中解析参数"""
        # /recall jiaolong -> query="jiaolong"
        if skill_name == "recall":
            # 去掉触发词，取剩余部分作为query
            for kw in ["/recall", "召回", "相关记忆", "查一下记忆", "记得什么"]:
                if kw in message:
                    query = message.replace(kw, "").strip()
                    if query:
                        return {"query": query, "top_k": DEFAULT_TOP_K}
            return {}

        if skill_name == "research":
            for kw in ["/research", "分析", "调研"]:
                if kw in message:
                    topic = message.replace(kw, "").strip()
                    if topic:
                        return {"topic": topic}
            return {}

        if skill_name == "quant_screen":
            for kw in ["/quant_screen", "选股", "筛选股票"]:
                if kw in message:
                    return {}
            return {}

        return {}

    def _execute_from_module(self, skill_name: str, params: Dict) -> Optional[dict]:
        """从Python模块执行"""
        # 检查skill script
        script_path = self.skills_dir / skill_name / "script.py"
        if script_path.exists():
            try:
                # 动态import
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    f"skill_{skill_name}", str(script_path)
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, 'run'):
                        result = module.run(**params)
                        if isinstance(result, dict):
                            return result
            except Exception as e:
                return {"success": False, "error": f"执行失败: {e}"}

        # 检查package __init__
        init_path = self.skills_dir / skill_name / "__init__.py"
        if init_path.exists():
            # 尝试直接导入
            try:
                module = __import__(f"skills.{skill_name}", fromlist=["run"])
                if hasattr(module, 'run'):
                    result = module.run(**params)
                    if isinstance(result, dict):
                        return result
            except Exception:
                pass

        return None

    def _execute_from_md(self, skill_name: str) -> dict:
        """读取SKILL.md作为参考"""
        md_path = self.skills_dir / skill_name / "SKILL.md"
        if md_path.exists():
            content = md_path.read_text(encoding="utf-8")
            return {
                "success": True,
                "skill": skill_name,
                "output": f"[{skill_name}] SKILL.md 参考:\n{content[:500]}"
            }
        return {
            "success": False,
            "error": f"Skill不存在: {skill_name}"
        }


# ─────────────────────────────────────────────────────────────────────────────
# 完整自动触发流程
# ─────────────────────────────────────────────────────────────────────────────

class AutoTrigger:
    """
    完整自动触发器
    检测 -> 执行 -> 返回结果
    """

    def __init__(self, custom_triggers: Dict[str, str] = None):
        self.trigger = SkillTrigger(custom_triggers)
        self.executor = SkillExecutor()

    def process(self, message: str, params: Dict[str, Any] = None) -> dict:
        """
        处理消息：检测触发词并执行

        Returns:
            {"triggered": bool, "skill": str, "result": dict}
        """
        params = params or {}

        skill_name = self.trigger.detect(message)
        if not skill_name:
            return {"triggered": False, "skill": None, "result": None}

        result = self.executor.execute(skill_name, params, raw_message=message)
        return {
            "triggered": True,
            "skill": skill_name,
            "message": message[:100],
            "result": result,
        }

    def process_all(self, message: str, params: Dict[str, Any] = None) -> List[dict]:
        """处理所有匹配的触发词"""
        params = params or {}
        skills = self.trigger.detect_all(message)

        results = []
        for skill_name in skills:
            result = self.executor.execute(skill_name, params, raw_message=message)
            results.append({
                "triggered": True,
                "skill": skill_name,
                "message": message[:100],
                "result": result,
            })

        return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI / 工具接口
# ─────────────────────────────────────────────────────────────────────────────

def auto_trigger(message: str, params: Dict = None) -> dict:
    """自动触发入口"""
    auto = AutoTrigger()
    return auto.process(message, params)


def register_trigger(keyword: str, skill_name: str):
    """注册自定义触发词"""
    DEFAULT_TRIGGERS[keyword] = skill_name


if __name__ == "__main__":
    print("=== Skills自动触发器验证 ===")

    auto = AutoTrigger()

    # 测试触发检测
    test_messages = [
        "查一下记忆jiaolong",
        "/recall 量化",
        "帮我开始进化",
        "/monitor",
        "请分析一下今天的A股",
        "帮我选股",
        "你好啊今天怎么样",  # 不应触发
    ]

    print("\n--- 触发检测 ---")
    for msg in test_messages:
        skill = auto.trigger.detect(msg)
        matched = "✅" if skill else "❌"
        print(f"{matched} '{msg[:30]}' -> {skill or '(无匹配)'}")

    # 测试完整执行
    print("\n--- 完整执行 ---")
    r = auto.process("/recall jiaolong")
    print(f"triggered: {r['triggered']}")
    print(f"skill: {r['skill']}")
    if r['result']:
        print(f"success: {r['result'].get('success')}")
        print(f"found: {r['result'].get('found', 'N/A')}")
