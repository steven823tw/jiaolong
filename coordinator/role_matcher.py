# -*- coding: utf-8 -*-
"""
jiaolong协调器 - Task-CO-2: 角色-技能匹配
> 版本: v1.0 | 2026-04-02
> 用途: jiaolong集团4角色自动匹配
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class AgentRole(str, Enum):
    """jiaolong集团Agent角色"""
    小笨 = "boss"
    小呆 = "intel"
    小傻 = "ux"
    小虾 = "backend"


ROLE_META = {
    AgentRole.小笨: {
        "name": "小笨",
        "codename": "boss",
        "title": "jiaolong老板",
        "description": "统筹协调，综合决策",
        "strengths": ["决策", "规划", "协调", "总结", "判断"],
        "tools": ["task_create", "team_create", "cron_create"],
        "max_load": 5,  # 最大并行任务数
    },
    AgentRole.小呆: {
        "name": "小呆",
        "codename": "intel",
        "title": "情报官",
        "description": "情报搜集，多源验证",
        "strengths": ["搜索", "分析", "验证", "报告", "数据"],
        "tools": ["mcp_call", "read_file", "agent_spawn"],
        "max_load": 8,
    },
    AgentRole.小傻: {
        "name": "小傻",
        "codename": "ux",
        "title": "交互大牛",
        "description": "UI/UX前端，界面设计",
        "strengths": ["设计", "前端", "React", "可视化", "报告"],
        "tools": ["notebook_edit", "task_update"],
        "max_load": 6,
    },
    AgentRole.小虾: {
        "name": "小虾",
        "codename": "backend",
        "title": "技术大牛",
        "description": "架构后端，API设计",
        "strengths": ["架构", "Python", "API", "系统", "代码"],
        "tools": ["task_create", "agent_spawn", "team_create"],
        "max_load": 6,
    },
}


class RoleMatcher:
    """
    角色-技能匹配器
    根据任务类型自动分配最合适的Agent角色
    """

    # 任务关键词 -> 角色权重
    TASK_KEYWORDS = {
        "boss": [
            "决策", "判断", "选择", "审批", "确认", "评估",
            "规划", "计划", "总结", "汇总", "整合",
            "优先", "目标", "战略", "方向",
        ],
        "intel": [
            "分析", "研究", "搜集", "搜索", "查找", "调查",
            "监控", "追踪", "查询", "对比", "预测",
            "情报", "报告", "数据", "指标", "排行", "热点",
            "行情", "股市", "板块", "选股",
        ],
        "ux": [
            "画", "界面", "UI", "UX", "设计", "展示",
            "前端", "图表", "Dashboard", "面板",
            "可视化", "报表", "Markdown", "报告",
            "生成", "创建",
        ],
        "backend": [
            "后端", "API", "接口", "服务", "架构",
            "数据库", "存储", "数据流", "管道",
            "系统", "集成", "SDK", "MCP", "工具",
            "代码", "Python", "脚本", "自动化",
        ],
    }

    def match(self, task_description: str) -> Tuple[str, float, str]:
        """
        匹配最合适的角色

        Returns:
            (role, confidence, reasoning)
        """
        task_lower = task_description.lower()

        # 计算每个角色的匹配分
        scores = {}
        for role, keywords in self.TASK_KEYWORDS.items():
            score = sum(2 for kw in keywords if kw in task_lower)
            # 精确词匹配权重更高
            for kw in keywords:
                if kw in task_lower:
                    score += 1
            scores[role] = score

        # 最高分
        best_role = max(scores, key=scores.get)
        best_score = scores[best_role]

        # 归一化confidence
        max_possible = len(self.TASK_KEYWORDS[best_role]) * 3
        confidence = min(best_score / max_possible * 0.95, 0.98) if max_possible else 0.5

        role_names = {"boss": "小笨", "intel": "小呆", "ux": "小傻", "backend": "小虾"}
        reasoning = f"分配给{role_names.get(best_role, best_role)}（score={best_score}）"

        return best_role, confidence, reasoning

    def match_multi(self, task_description: str, max_roles: int = 2) -> List[Tuple[str, float]]:
        """
        返回多个可能匹配的角色（用于团队任务分配）

        Returns:
            [(role, confidence), ...]
        """
        task_lower = task_description.lower()
        scores = {}

        for role, keywords in self.TASK_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            scores[role] = score

        ranked = sorted(scores.items(), key=lambda x: -x[1])[:max_roles]
        return [(role, conf) for role, conf in ranked]

    def get_role_info(self, role: str) -> dict:
        """获取角色信息"""
        try:
            role_enum = AgentRole(role)
        except ValueError:
            return {}
        return ROLE_META.get(role_enum, {})

    def list_all_roles(self) -> List[dict]:
        """列出所有角色"""
        return [
            {
                "role": role.value,
                "name": meta["name"],
                "title": meta["title"],
                "description": meta["description"],
                "strengths": meta["strengths"],
                "tools": meta["tools"],
                "max_load": meta["max_load"],
            }
            for role, meta in ROLE_META.items()
        ]

    def check_load(self, role: str, current_load: int) -> Tuple[bool, str]:
        """
        检查角色负载是否允许新任务

        Returns:
            (can_accept, message)
        """
        role_enum = AgentRole(role)
        meta = ROLE_META.get(role_enum, {})
        max_load = meta.get("max_load", 5)

        if current_load >= max_load:
            return False, f"{meta.get('name','?')} 负载已满（{current_load}/{max_load}），建议分配给其他角色"
        return True, f"{meta.get('name','?')} 可用（负载 {current_load}/{max_load}）"


class TaskToRoleAssigner:
    """
    任务树 -> 角色分配器
    给定一个任务树，自动分配Agent角色
    """

    def __init__(self):
        self.matcher = RoleMatcher()

    def assign(self, task_tree) -> dict:
        """
        为任务树的每个任务分配角色

        Returns:
            {task_id: {role, confidence, reasoning}, ...}
        """
        assignments = {}

        for task_id, node in task_tree.nodes.items():
            if node.agent_role:
                # 已有角色，直接使用
                role, conf, reason = node.agent_role, 0.95, "已指定"
            else:
                role, conf, reason = self.matcher.match(node.description)

            node.agent_role = role
            assignments[task_id] = {
                "role": role,
                "confidence": conf,
                "reasoning": reason,
                "status": "assigned",
            }

        return assignments


if __name__ == "__main__":
    print("=== RoleMatcher 验证 ===")

    matcher = RoleMatcher()

    test_cases = [
        "搜集今日A股热点板块数据",
        "分析量化选股策略并生成回测报告",
        "构建jiaolong自进化框架的Python代码",
        "决策：选择哪个量化策略",
        "生成COCO 2.0的界面设计图",
    ]

    for task in test_cases:
        role, conf, reason = matcher.match(task)
        print(f"\n任务: {task}")
        print(f"  -> {role} (conf={conf:.2f}) {reason}")

    print("\n=== TaskToRoleAssigner 验证 ===")

    from decomposer import TaskDecomposer
    decomposer = TaskDecomposer()
    tree = decomposer.decompose("分析今日A股热点板块并生成报告")
    assigner = TaskToRoleAssigner()
    result = assigner.assign(tree)

    for tid, info in result.items():
        node = tree.nodes[tid]
        print(f"  {tid}: [{info['role']}] {node.description[:35]}")
