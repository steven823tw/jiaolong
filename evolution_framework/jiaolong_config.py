# -*- coding: utf-8 -*-
"""
jiaolong 统一配置模块 (cowork 适配版)
> 版本: v5.0.0 | 2026-04-30
> 所有路径从这里读取，支持环境变量覆盖
"""
from __future__ import annotations
import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# 核心路径配置
# 优先级: 环境变量 > 默认值
# ─────────────────────────────────────────────────────────────────────────────

def get_home() -> Path:
    """获取用户主目录"""
    return Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))


def get_workspace() -> Path:
    """
    获取 jiaolong 工作区根目录
    环境变量: JIAOLONG_WORKSPACE
    默认: ~/.claude/jiaolong
    """
    env = os.environ.get("JIAOLONG_WORKSPACE")
    if env:
        return Path(env)
    return get_home() / ".claude" / "jiaolong"


def get_evolution_dir() -> Path:
    """获取 evolution_framework 目录"""
    return get_workspace() / "evolution_framework"


def get_memory_dir() -> Path:
    """获取记忆存储目录"""
    return get_workspace() / "memory"


def get_skills_dir() -> Path:
    """获取 skills 目录"""
    return get_workspace() / "skills"


def get_tools_dir() -> Path:
    """获取 tools 目录"""
    return get_evolution_dir() / "tools"


def get_experiments_dir() -> Path:
    """获取实验日志目录"""
    return get_evolution_dir() / "experiments"


# ─────────────────────────────────────────────────────────────────────────────
# 常用文件路径
# ─────────────────────────────────────────────────────────────────────────────

MEMORY_HOT = property(lambda self: get_memory_dir() / "memory_hot.json")


def memory_hot_path() -> Path:
    return get_memory_dir() / "memory_hot.json"


def memory_index_path() -> Path:
    return get_memory_dir() / "memory_index.json"


def memory_warm_dir() -> Path:
    return get_memory_dir() / "memory_warm"


def memory_cold_dir() -> Path:
    return get_memory_dir() / "memory_cold"


# ─────────────────────────────────────────────────────────────────────────────
# 初始化：确保目录存在
# ─────────────────────────────────────────────────────────────────────────────

def ensure_dirs():
    """创建所有必要的目录"""
    dirs = [
        get_workspace(),
        get_evolution_dir(),
        get_memory_dir(),
        get_skills_dir(),
        get_memory_dir() / "memory_warm",
        get_memory_dir() / "memory_cold",
        get_experiments_dir(),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def init_memory():
    """初始化空的记忆文件（如果不存在）"""
    hot = memory_hot_path()
    if not hot.exists():
        hot.parent.mkdir(parents=True, exist_ok=True)
        import json
        hot.write_text(
            json.dumps({"facts": [], "version": "1.0"}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 兼容层：供旧代码快速迁移
# ─────────────────────────────────────────────────────────────────────────────

# 旧代码可以直接 import WORKSPACE 代替硬编码
WORKSPACE = get_workspace()


if __name__ == "__main__":
    print(f"Workspace:    {get_workspace()}")
    print(f"Evolution:    {get_evolution_dir()}")
    print(f"Memory:       {get_memory_dir()}")
    print(f"Skills:       {get_skills_dir()}")
    print(f"Memory Hot:   {memory_hot_path()}")
    ensure_dirs()
    init_memory()
    print("\n✅ 所有目录已初始化")
