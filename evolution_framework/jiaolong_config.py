# -*- coding: utf-8 -*-
"""
jiaolong 统一配置模块 (cowork 适配版)
> 版本: v6.1.0 | 2026-06-01
> 所有路径从这里读取，支持环境变量覆盖
> v6.0: 记忆系统迁移到 Claude Code 原生 .md 格式
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
    默认: C:/cc/jiaolong-cowork (当前项目)
    """
    env = os.environ.get("JIAOLONG_WORKSPACE")
    if env:
        return Path(env)
    return Path("C:/cc/jiaolong-cowork")


def get_evolution_dir() -> Path:
    """获取 evolution_framework 目录"""
    return get_workspace() / "evolution_framework"


def get_memory_dir() -> Path:
    """获取记忆存储目录 (legacy, 原生系统使用 get_native_memory_dir)"""
    return get_workspace() / "memory"


def get_native_memory_dir(cwd: str = None) -> Path:
    """
    获取 Claude Code 原生记忆目录
    v6.0: 记忆系统迁移到原生 .md 格式
    路径格式: ~/.claude/projects/{C--cc}/memory/
    """
    if not cwd:
        cwd = "C:\\cc"
    project_name = cwd.replace(":\\", "--").replace("\\", "--").replace(":", "--")
    project_name = project_name.rstrip("-")
    return get_home() / ".claude" / "projects" / project_name / "memory"


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
# 初始化：确保目录存在
# ─────────────────────────────────────────────────────────────────────────────

def ensure_dirs():
    """创建所有必要的目录"""
    dirs = [
        get_workspace(),
        get_evolution_dir(),
        get_skills_dir(),
        get_experiments_dir(),
        get_native_memory_dir(),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# 兼容层：供旧代码快速迁移
# ─────────────────────────────────────────────────────────────────────────────

# 旧代码可以直接 import WORKSPACE 代替硬编码
WORKSPACE = get_workspace()


if __name__ == "__main__":
    print(f"Workspace:        {get_workspace()}")
    print(f"Evolution:        {get_evolution_dir()}")
    print(f"Memory (legacy):  {get_memory_dir()}")
    print(f"Memory (native):  {get_native_memory_dir()}")
    print(f"Skills:           {get_skills_dir()}")
    ensure_dirs()
    print("\n✅ 所有目录已初始化")
