# -*- coding: utf-8 -*-
"""
jiaolong Skills 统一输出格式化器
> 版本: v1.0 | 2026-04-02
> 用途: 所有Skill返回统一markdown格式
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# 标准响应结构
# ─────────────────────────────────────────────────────────────────────────────

def ok(skill: str, data: Any = None, summary: str = "",
       hints: List[str] = None, **extra) -> dict:
    """
    成功响应
    """
    return {
        "success": True,
        "skill": skill,
        "data": data,
        "summary": summary,
        "hints": hints or [],
        "output": _format_success(skill, data, summary, hints),
        **extra
    }


def err(skill: str, error: str, hint: str = "") -> dict:
    """
    错误响应
    """
    return {
        "success": False,
        "skill": skill,
        "error": error,
        "hint": hint,
        "output": _format_error(skill, error, hint)
    }


# ─────────────────────────────────────────────────────────────────────────────
# 格式化模板
# ─────────────────────────────────────────────────────────────────────────────

def _format_success(skill: str, data: Any, summary: str,
                    hints: List[str], **extra) -> str:
    """格式化成功输出"""
    lines = [f"## [{skill}] 执行结果"]
    lines.append("")
    lines.append("**状态**: ✅ 成功")
    lines.append(f"**时间**: {datetime.now().strftime('%H:%M:%S')}")
    lines.append("")

    if summary:
        lines.append(f"**摘要**: {summary}")
        lines.append("")

    if data:
        data_str = _format_data(data)
        lines.append("**数据**:")
        lines.append("```")
        lines.append(data_str)
        lines.append("```")
        lines.append("")

    if hints:
        lines.append("**建议**:")
        for h in hints:
            lines.append(f"- {h}")
        lines.append("")

    return "\n".join(lines)


def _format_error(skill: str, error: str, hint: str) -> str:
    """格式化错误输出"""
    lines = [f"## [{skill}] 执行结果"]
    lines.append("")
    lines.append("**状态**: ❌ 失败")
    lines.append(f"**时间**: {datetime.now().strftime('%H:%M:%S')}")
    lines.append("")
    lines.append(f"**错误**: {error}")
    if hint:
        lines.append("")
        lines.append(f"**建议**: {hint}")
    lines.append("")
    return "\n".join(lines)


def _format_data(data: Any, indent: int = 0) -> str:
    """格式化数据对象"""
    prefix = "  " * indent
    if isinstance(data, dict):
        lines = []
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}{k}:")
                lines.append(_format_data(v, indent + 1))
            else:
                lines.append(f"{prefix}{k}: {v}")
        return "\n".join(lines)
    elif isinstance(data, list):
        if not data:
            return f"{prefix}(empty)"
        return "\n".join(f"{prefix}- {item}" for item in data[:10])
    else:
        return f"{prefix}{data}"


# ─────────────────────────────────────────────────────────────────────────────
# 统一Skill执行装饰器
# ─────────────────────────────────────────────────────────────────────────────

def skill_main(skill_name: str, required_params: List[str] = None):
    """
    Skill主函数装饰器，统一错误处理和输出格式化

    用法:
        @skill_main("recall", required_params=["query"])
        def _run(query: str = "", **kwargs) -> dict:
            # 实际逻辑
            return ok(skill_name, data={...}, summary="找到3条记忆")
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # 检查必要参数
                if required_params:
                    for p in required_params:
                        if p not in kwargs or kwargs[p] is None:
                            return err(skill_name,
                                       f"缺少必要参数: {p}",
                                       f"用法: /{skill_name} {' '.join(required_params)}")

                # 执行
                result = func(*args, **kwargs)

                # 如果返回的是ok/err，直接返回
                if isinstance(result, dict) and ("output" in result or "error" in result):
                    return result

                # 否则包装
                return ok(skill_name, data=result)

            except Exception as e:
                return err(skill_name, str(e),
                           hint="检查参数格式或查看日志")

        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# 表格格式化
# ─────────────────────────────────────────────────────────────────────────────

def format_table(headers: List[str], rows: List[List[Any]],
                 title: str = "") -> str:
    """
    格式化表格输出

    用法:
        print(format_table(
            ["名称", "分数"],
            [["jiaolong", 95], ["COCO", 88]],
            title="记忆评分"
        ))
    """
    lines = []
    if title:
        lines.append(f"**{title}**")
        lines.append("")

    # 计算列宽
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # 表头
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append(" | ".join("-" * w for w in col_widths))

    # 数据行
    for row in rows:
        row_line = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        lines.append(row_line)

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 列表格式化
# ─────────────────────────────────────────────────────────────────────────────

def format_list(items: List[str], title: str = "",
                numbered: bool = False, emoji: str = "•") -> str:
    """
    格式化列表输出
    """
    lines = []
    if title:
        lines.append(f"**{title}**")
        lines.append("")

    for i, item in enumerate(items, 1):
        prefix = f"{i}." if numbered else emoji
        lines.append(f"  {prefix} {item}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI 验证
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Skill 输出格式化器验证 ===\n")

    # 测试 ok
    r = ok("recall", data={"found": 10, "items": ["jiaolong", "量化"]},
           summary="找到10条相关记忆",
           hints=["试试 /recall jiaolong recent 5"])
    print(r["output"])

    # 测试 err
    r = err("recall", "缺少参数: query", "用法: /recall <关键词>")
    print(r["output"])

    # 测试 format_table
    print(format_table(
        ["Skill", "触发词", "状态"],
        [["recall", "/recall", "✅"],
         ["evolve", "/evolve", "✅"],
         ["quant_screen", "/quant_screen", "⬜"]],
        title="Skills 状态"
    ))
