#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
jiaolong记忆召回 - Hook入口
> 版本: v1.0 | 2026-04-02
> 被 OpenClaw hook 调用，在每次消息前注入记忆上下文
"""
from __future__ import annotations
import sys, json, os, re

sys.path.insert(0, r'C:\Users\steve\.openclaw\workspace\evolution_framework')

# ─────────────────────────────────────────────────────────────────────────────
# 外部可配置的路径（兼容OpenClaw workspace hooks调用）
# ─────────────────────────────────────────────────────────────────────────────

def get_workspace() -> str:
    """获取workspace路径"""
    return os.environ.get(
        "JIAOLONG_WORKSPACE",
        r"C:\Users\steve\.openclaw\workspace"
    )


def get_memory_file() -> str:
    """获取memory_hot.json路径"""
    ws = get_workspace()
    return os.path.join(ws, "memory", "memory_hot.json")


# ─────────────────────────────────────────────────────────────────────────────
# 核心：构建记忆上下文
# ─────────────────────────────────────────────────────────────────────────────

def build_memory_context(message: str, max_memories: int = 5) -> str:
    """
    从用户消息中提取关键词，召回相关记忆，返回格式化的上下文字符串
    """
    if not message or len(message.strip()) < 2:
        return ""

    # 排除命令消息
    if message.strip().startswith('/'):
        return ""

    try:
        from memory_recall import MemoryInjector
        injector = MemoryInjector(top_k=max_memories)
        context = injector.build_context_prompt(message, max_memories=max_memories)
        return context
    except Exception as e:
        return f"\n\n[记忆召回错误: {e}]\n"


# ─────────────────────────────────────────────────────────────────────────────
# CLI入口（被TypeScript hook调用）
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 从stdin读取JSON: {"message": "...", "max_memories": 5}
    try:
        data = json.load(sys.stdin)
        message = data.get("message", "")
        max_memories = data.get("max_memories", 5)

        context = build_memory_context(message, max_memories)

        # 输出JSON给TypeScript解析
        result = {
            "success": True,
            "context": context,
            "has_memory": len(context.strip()) > 0,
        }
        print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        error_result = {"success": False, "error": str(e), "context": ""}
        print(json.dumps(error_result, ensure_ascii=False))
