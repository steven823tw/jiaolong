# -*- coding: utf-8 -*-
"""
jiaolong Skills - 自创建Skill合集
> 版本: v1.0 | 2026-04-02
> 批量创建高频Skills
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

WORKSPACE = Path(r"C:\Users\steve\.openclaw\workspace")
SKILLS_DIR = WORKSPACE / "evolution_framework" / "skills"


class SkillManifest:
    """Skill清单 - 定义所有要创建的Skill"""

    SKILLS = [
        {
            "name": "simplify",
            "title": "简化任务",
            "description": "将复杂任务分解为简单子任务",
            "trigger": ["/simplify", "简化"],
            "category": "coordination",
            "params": [
                {"name": "task", "type": "str", "description": "复杂任务描述"}
            ],
            "steps": [
                "1. 分析任务复杂度",
                "2. 拆解为3-8个子任务",
                "3. 确定依赖关系",
                "4. 输出任务树"
            ],
            "examples": [
                {"cmd": "/simplify 分析A股", "result": "拆解为情报搜集→分析→报告3步"}
            ]
        },
        {
            "name": "research",
            "title": "深度研究",
            "description": "对任意主题进行深度搜索和分析",
            "trigger": ["/research", "研究", "调研"],
            "category": "intel",
            "params": [
                {"name": "topic", "type": "str", "description": "研究主题"},
                {"name": "depth", "type": "str", "description": "深度(high/medium/low)", "default": "medium"}
            ],
            "steps": [
                "1. 多源搜索(topic)",
                "2. 交叉验证信息",
                "3. 生成结构化报告",
                "4. 标注置信度"
            ],
            "examples": [
                {"cmd": "/research XTick API", "result": "输出XTick完整分析报告"}
            ]
        },
        {
            "name": "remember",
            "title": "记忆检查",
            "description": "检查相关记忆并提供上下文",
            "trigger": ["/remember", "记得", "查一下记忆"],
            "category": "memory",
            "params": [
                {"name": "query", "type": "str", "description": "查询关键词"}
            ],
            "steps": [
                "1. 搜索memory_hot.json",
                "2. 检查OMLX温冷层",
                "3. 汇总相关事实",
                "4. 提供上下文"
            ],
            "examples": [
                {"cmd": "/remember jiaolong", "result": "返回jiaolong集团相关记忆"}
            ]
        },
        {
            "name": "dream",
            "title": "记忆整合",
            "description": "定期整理记忆，去重+分类+补充",
            "trigger": ["/dream", "整合记忆", "整理记忆"],
            "category": "memory",
            "params": [
                {"name": "days", "type": "int", "description": "整理最近N天记忆", "default": 7}
            ],
            "steps": [
                "1. 读取最近N天会话",
                "2. 提取新事实",
                "3. 去重合并",
                "4. 更新category分布"
            ],
            "examples": [
                {"cmd": "/dream 7", "result": "整理近7天记忆"}
            ]
        },
        {
            "name": "monitor",
            "title": "主动监控",
            "description": "检查项目状态并告警",
            "trigger": ["/monitor", "状态", "检查"],
            "category": "ops",
            "params": [
                {"name": "target", "type": "str", "description": "监控目标", "default": "all"}
            ],
            "steps": [
                "1. 检查COCO服务器",
                "2. 检查量化进程",
                "3. 检查定时任务",
                "4. 输出状态报告"
            ],
            "examples": [
                {"cmd": "/monitor", "result": "COCO✅ 量化✅ 任务✅"}
            ]
        },
        {
            "name": "evolve",
            "title": "自进化",
            "description": "运行AutoResearch实验循环",
            "trigger": ["/evolve", "进化", "实验"],
            "category": "evolution",
            "params": [
                {"name": "focus", "type": "str", "description": "进化方向", "default": "auto"}
            ],
            "steps": [
                "1. 读取当前状态",
                "2. 提出改进假设",
                "3. 小范围验证",
                "4. 评估+决定保留/丢弃"
            ],
            "examples": [
                {"cmd": "/evolve tools", "result": "运行tools方向进化实验"}
            ]
        },
        {
            "name": "quant_screen",
            "title": "量化选股",
            "description": "按量化因子筛选股票",
            "trigger": ["/quant_screen", "选股", "筛选"],
            "category": "quant",
            "params": [
                {"name": "turnover_rate", "type": "float", "description": "换手率下限(%)", "default": 3},
                {"name": "top_n", "type": "int", "description": "返回数量", "default": 20}
            ],
            "steps": [
                "1. 连接XTick数据源",
                "2. 应用量化因子筛选",
                "3. 排序+返回TopN",
                "4. 记录到记忆"
            ],
            "examples": [
                {"cmd": "/quant_screen turnover_rate=5 top_n=10", "result": "换手率>5%的Top10股票"}
            ]
        },
        {
            "name": "team_analyze",
            "title": "团队分析",
            "description": "创建jiaolong团队分析复杂任务",
            "trigger": ["/team_analyze", "团队分析"],
            "category": "coordination",
            "params": [
                {"name": "goal", "type": "str", "description": "分析目标"}
            ],
            "steps": [
                "1. 拆解任务",
                "2. 分配角色(小笨/小呆/小傻/小虾)",
                "3. 并行执行",
                "4. 汇总结果"
            ],
            "examples": [
                {"cmd": "/team_analyze A股今日热点", "result": "4Agent协作完成分析"}
            ]
        },
        {
            "name": "extract_memories",
            "title": "记忆提取",
            "description": "从当前会话自动提取记忆",
            "trigger": ["/extract_memories", "提取记忆"],
            "category": "memory",
            "params": [],
            "steps": [
                "1. 读取今日会话",
                "2. 触发检测",
                "3. 质量评分",
                "4. 去重+写入"
            ],
            "examples": [
                {"cmd": "/extract_memories", "result": "提取报告"}
            ]
        },
        {
            "name": "status_report",
            "title": "状态报告",
            "description": "生成完整状态报告",
            "trigger": ["/status_report", "报告", "状态报告"],
            "category": "ops",
            "params": [
                {"name": "detail", "type": "bool", "description": "详细模式", "default": False}
            ],
            "steps": [
                "1. 记忆系统状态",
                "2. 项目进度",
                "3. 服务器状态",
                "4. 生成报告"
            ],
            "examples": [
                {"cmd": "/status_report", "result": "今日完整状态报告"}
            ]
        },
    ]


def create_skill(skill_def: dict, dry_run: bool = False) -> dict:
    """创建单个Skill"""
    from .search_skills import SkillBuilder

    if dry_run:
        return {"skill": skill_def["name"], "dry_run": True}

    builder = SkillBuilder()
    result = builder.create(
        name=skill_def["name"],
        description=skill_def["description"],
        params=skill_def.get("params", []),
        steps=skill_def.get("steps", []),
        examples=skill_def.get("examples", []),
    )
    return result


def create_all_skills(dry_run: bool = False) -> dict:
    """批量创建所有Skill"""
    results = []
    for skill_def in SkillManifest.SKILLS:
        result = create_skill(skill_def, dry_run=dry_run)
        results.append(result)

    return {
        "total": len(results),
        "dry_run": dry_run,
        "created": [r for r in results if not dry_run and r.get("created")],
        "results": results,
    }


if __name__ == "__main__":
    print("=== 批量创建Skills ===")
    result = create_all_skills(dry_run=True)
    print(f"将创建: {result['total']} 个Skills")
    for r in result["results"]:
        print(f"  - {r['skill']}")

    print("\n=== 实际创建 ===")
    result2 = create_all_skills(dry_run=False)
    print(f"创建成功: {len(result2['created'])}")
