# -*- coding: utf-8 -*-
"""
jiaolong LLM 任务分解器
> 版本: v1.0 | 2026-04-02
> 功能:
>   - LLM驱动的任务智能拆解
>   - 多步复杂任务 → 可执行子任务
>   - 并行任务识别
>   - 依赖关系分析
>
> 依赖: llm_core.py (LLMManager)
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# 任务结构
# ─────────────────────────────────────────────────────────────────────────────

class TaskType(str, Enum):
    RESEARCH = "research"      # 情报搜集
    CODE = "code"              # 代码实现
    ANALYSIS = "analysis"       # 分析决策
    REPORT = "report"           # 报告生成
    COORDINATION = "coordination"  # 协调统筹
    EXECUTION = "execution"     # 执行操作


class AgentRole(str, Enum):
    BOSS = "boss"      # 小笨 - 决策
    INTEL = "intel"    # 小呆 - 情报
    UX = "ux"          # 小傻 - 交互
    BACKEND = "backend"  # 小虾 - 技术


@dataclass
class SubTask:
    """子任务"""
    description: str
    task_type: TaskType
    agent: AgentRole
    depends_on: List[int] = field(default_factory=list)  # 依赖的任务索引
    parallel_safe: bool = False  # 是否可以并行
    tool_hint: str = ""  # 建议的工具
    priority: int = 1  # 优先级 1-5
    estimated_minutes: int = 5  # 预估时间


@dataclass
class TaskDecomposition:
    """任务分解结果"""
    original_task: str
    goal: str
    subtasks: List[SubTask]
    estimated_total_minutes: int = 0
    can_parallel: bool = False
    execution_order: List[List[int]] = field(default_factory=list)  # 可并行的任务分组


# ─────────────────────────────────────────────────────────────────────────────
# LLM 任务分解器
# ─────────────────────────────────────────────────────────────────────────────

class TaskDecomposer:
    """
    LLM驱动的任务分解器

    vs 规则分解的优势:
    - 理解语义，不依赖关键词
    - 智能判断并行机会
    - 考虑任务类型和上下文
    - 避免过度拆分
    """

    def __init__(self, provider: str = None):
        self._llm = None
        self._provider = provider
        self._rule_decomposer = None  # 备用规则分解器

    @property
    def llm(self):
        if self._llm is None:
            from llm_core import get_decomposer
            self._llm = get_decomposer(self._provider)
        return self._llm

    def decompose(self, task: str, context: str = "") -> TaskDecomposition:
        """
        分解任务

        Args:
            task: 任务描述
            context: 额外上下文

        Returns:
            TaskDecomposition 对象
        """
        # 尝试LLM分解
        try:
            result = self.llm.decompose(
                task,
                context=context,
                available_tools=self._get_available_tools()
            )
            return self._parse_decomposition(task, result)
        except Exception as e:
            # 回退到规则分解
            return self._rule_decompose(task)

    def _parse_decomposition(self, task: str,
                            llm_result: List[Dict]) -> TaskDecomposition:
        """解析LLM返回的分解结果"""
        subtasks = []
        for i, item in enumerate(llm_result):
            desc = item.get("description", "")
            agent_str = item.get("agent", "boss").lower()
            tool = item.get("tool", "")
            priority = int(item.get("priority", 3))

            # 映射agent
            if "intel" in agent_str or "情报" in agent_str:
                agent = AgentRole.INTEL
                task_type = TaskType.RESEARCH
            elif "ux" in agent_str or "傻" in agent_str:
                agent = AgentRole.UX
                task_type = TaskType.REPORT
            elif "backend" in agent_str or "虾" in agent_str:
                agent = AgentRole.BACKEND
                task_type = TaskType.CODE
            else:
                agent = AgentRole.BOSS
                task_type = TaskType.ANALYSIS

            subtask = SubTask(
                description=desc,
                task_type=task_type,
                agent=agent,
                tool_hint=tool,
                priority=priority,
            )
            subtasks.append(subtask)

        # 计算执行顺序
        order = self._compute_execution_order(subtasks)

        total = sum(s.estimated_minutes for s in subtasks)
        can_parallel = len(order) > 1

        return TaskDecomposition(
            original_task=task,
            goal=self._extract_goal(task),
            subtasks=subtasks,
            estimated_total_minutes=total,
            can_parallel=can_parallel,
            execution_order=order,
        )

    def _compute_execution_order(self, subtasks: List[SubTask]) -> List[List[int]]:
        """
        计算执行顺序 - 识别可并行的任务组
        返回: [[可并行任务索引], [第二批次], ...]
        """
        if not subtasks:
            return []

        # 简化: 无依赖的任务可并行
        parallel_groups = []
        remaining = set(range(len(subtasks)))
        done = set()

        while remaining:
            # 找所有依赖都已完成的任务
            ready = []
            for i in remaining:
                deps = set(subtasks[i].depends_on)
                if deps <= done:
                    ready.append(i)

            if not ready:
                # 循环依赖，取最小的
                ready = [min(remaining)]

            parallel_groups.append(sorted(ready))
            done.update(ready)
            remaining -= set(ready)

        return parallel_groups

    def _extract_goal(self, task: str) -> str:
        """从任务描述中提取核心目标"""
        # 简单实现: 取前20字符
        return task[:50].strip()

    def _get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        try:
            from pathlib import Path
            tools_dir = Path(__file__).parent / "tools"
            if tools_dir.exists():
                return [f.stem for f in tools_dir.glob("*.json")]
        except:
            pass
        return ["read", "write", "exec", "web_search"]

    def _rule_decompose(self, task: str) -> TaskDecomposition:
        """规则分解器（备用）"""
        if self._rule_decomposer is None:
            self._rule_decomposer = RuleDecomposer()

        raw = self._rule_decomposer.decompose(task)
        return self._parse_decomposition(task, raw)


# ─────────────────────────────────────────────────────────────────────────────
# 规则任务分解器（备用）
# ─────────────────────────────────────────────────────────────────────────────

class RuleDecomposer:
    """
    规则基础任务分解器
    当LLM不可用时的备用方案
    """

    # 关键词 → 任务类型 + Agent
    TASK_PATTERNS = [
        # 情报类
        (["搜索", "调研", "分析", "研究", "查找", "搜集"], TaskType.RESEARCH, AgentRole.INTEL),
        # 代码类
        (["写代码", "开发", "实现", "编程", "写个", "写"], TaskType.CODE, AgentRole.BACKEND),
        # 报告类
        (["生成报告", "总结", "整理", "导出", "制作报告"], TaskType.REPORT, AgentRole.UX),
        # 决策类
        (["决策", "决定", "选择", "对比", "比较"], TaskType.ANALYSIS, AgentRole.BOSS),
        # 执行类
        (["执行", "运行", "操作", "处理"], TaskType.EXECUTION, AgentRole.BACKEND),
    ]

    def decompose(self, task: str) -> List[Dict]:
        """规则分解"""
        task_lower = task.lower()

        # 匹配模式
        for keywords, task_type, agent in self.TASK_PATTERNS:
            for kw in keywords:
                if kw in task_lower:
                    return [{
                        "description": task,
                        "agent": agent.value,
                        "tool": self._guess_tool(task),
                        "priority": 3,
                    }]

        # 默认: 协调任务
        return [{
            "description": task,
            "agent": "boss",
            "tool": None,
            "priority": 2,
        }]

    def _guess_tool(self, task: str) -> Optional[str]:
        """猜测需要的工具"""
        task_lower = task.lower()
        if "搜索" in task_lower or "调研" in task_lower:
            return "web_search"
        if "写文件" in task_lower or "创建" in task_lower:
            return "write"
        if "运行" in task_lower or "执行" in task_lower:
            return "exec"
        if "分析" in task_lower or "对比" in task_lower:
            return "analyze"
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 格式化输出
# ─────────────────────────────────────────────────────────────────────────────

def format_decomposition(decomp: TaskDecomposition) -> str:
    """格式化分解结果"""
    lines = []
    lines.append(f"## 任务分解: {decomp.goal}")
    lines.append("")

    icon = "✅" if decomp.can_parallel else "📌"
    lines.append(f"{icon} 预估时间: {decomp.estimated_total_minutes}分钟")
    if decomp.can_parallel:
        lines.append(f"  可并行执行: {len(decomp.execution_order)}个批次")
    lines.append("")

    lines.append("### 子任务")
    lines.append("")

    for i, group in enumerate(decomp.execution_order):
        batch_icon = "🔄" if i > 0 else "▶️"
        batch_label = "可并行" if len(group) > 1 else "下一步"
        lines.append(f"{batch_icon} 第{i+1}批次 ({batch_label}):")

        for idx in group:
            task = decomp.subtasks[idx]
            type_icon = {
                TaskType.RESEARCH: "🔍",
                TaskType.CODE: "💻",
                TaskType.ANALYSIS: "🧠",
                TaskType.REPORT: "📝",
                TaskType.COORDINATION: "🎯",
                TaskType.EXECUTION: "⚙️",
            }.get(task.task_type, "•")

            agent_icon = {
                AgentRole.BOSS: "🔵",
                AgentRole.INTEL: "🟢",
                AgentRole.UX: "🟡",
                AgentRole.BACKEND: "🔴",
            }.get(task.agent, "•")

            deps = f" (依赖: {task.depends_on})" if task.depends_on else ""
            tool = f" [工具: {task.tool_hint}]" if task.tool_hint else ""

            lines.append(f"  {type_icon} {task.description}{deps}{tool}")
            lines.append(f"     {agent_icon} 执行者: {task.agent.value} | ⏱ {task.estimated_minutes}分钟")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Task Decomposer 验证 ===\n")

    decomposer = TaskDecomposer()

    # 测试用例
    tests = [
        "分析今日A股市场并生成报告",
        "帮我选股：沪深300中ROE最高的10只",
        "开发一个Web服务器",
    ]

    for task in tests:
        print(f"任务: {task}")
        try:
            result = decomposer.decompose(task)
            print(format_decomposition(result))
        except Exception as e:
            print(f"  分解失败: {e}")
        print()
