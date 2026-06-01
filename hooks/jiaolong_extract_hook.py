# -*- coding: utf-8 -*-
"""
jiaolong → Claude Code Native Memory Extract Hook
> 版本: v6.0.0 | 2026-05-29
> 用途: Claude Code Stop hook - 从对话中提取记忆，写入原生 .md 记忆系统

进化点:
- 放弃 memory_hot.json，写入 ~/.claude/projects/{project}/memory/*.md
- 遵循 Claude Code 原生 frontmatter 格式
- 自动更新 MEMORY.md 索引
"""
from __future__ import annotations
import json
import sys
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# 路径配置
# ─────────────────────────────────────────────────────────────────────────────

HOME = Path.home()
CLAUDE_PROJECTS = HOME / ".claude" / "projects"


def _sanitize(text: str) -> str:
    """Remove lone surrogates that break UTF-8 JSON serialization."""
    return text.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")


def get_project_memory_dir(cwd: str) -> Path:
    """根据 cwd 推断 Claude Code 项目记忆目录"""
    # Claude Code 项目路径编码: C:\cc → C--cc
    if not cwd:
        # fallback: 用当前 cwd
        cwd = os.getcwd()

    # 将路径转换为 Claude Code 项目名
    # C:\cc → C--cc, C:\Users\steve\project → C--Users--steve--project
    project_name = cwd.replace(":\\", "--").replace("\\", "--").replace(":", "--")
    # 去掉尾部 --
    project_name = project_name.rstrip("-")

    memory_dir = CLAUDE_PROJECTS / project_name / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def get_memory_index(memory_dir: Path) -> Path:
    """获取 MEMORY.md 索引路径"""
    return memory_dir / "MEMORY.md"


# ─────────────────────────────────────────────────────────────────────────────
# 记忆分类
# ─────────────────────────────────────────────────────────────────────────────

# 分类关键词映射到 Claude Code 记忆类型
CLASSIFY_RULES = {
    "feedback": [
        "不要", "别", "禁止", "必须", "每次", "记住",
        "don't", "never", "must", "always", "remember",
        "反馈", "改进", "问题", "bug", "错误", "修复",
    ],
    "project": [
        "项目", "架构", "模块", "sprint", "版本", "部署",
        "project", "architecture", "module", "deploy", "release",
    ],
    "user": [
        "偏好", "喜欢", "习惯", "风格", "我是",
        "preference", "like", "prefer", "style", "i am",
    ],
    "reference": [
        "文档", "链接", "参考", "教程", "API",
        "docs", "link", "reference", "tutorial", "url",
    ],
}


def classify_content(content: str) -> str:
    """分类记忆内容，返回 Claude Code 记忆类型"""
    content_lower = content.lower()

    scores = {}
    for mem_type, keywords in CLASSIFY_RULES.items():
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            scores[mem_type] = score

    if scores:
        return max(scores, key=scores.get)
    return "reference"  # 默认为 reference


# ─────────────────────────────────────────────────────────────────────────────
# 记忆质量过滤
# ─────────────────────────────────────────────────────────────────────────────

def is_worth_remembering(content: str) -> bool:
    """判断内容是否值得记忆"""
    content = content.strip()

    # 太短
    if len(content) < 30:
        return False

    # 纯命令输出
    if content.startswith(("$", ">", "#", "PS", "C:\\")):
        return False

    # 纯代码块（没有中文说明）
    lines = content.split("\n")
    code_lines = sum(1 for l in lines if l.strip().startswith(("def ", "class ", "import ", "from ", "if ", "for ", "return ", "{", "}", "//")))
    if code_lines > len(lines) * 0.7 and not any('一' <= c <= '鿿' for c in content):
        return False

    # 纯错误日志
    if "Error" in content and "Traceback" in content and len(content) < 100:
        return False

    return True


def generate_slug(content: str, hook_data: dict = None) -> str:
    """从内容和 hook 数据生成简短的 kebab-case slug"""
    parts = []

    # 从 hook_data 提取关键信息
    if hook_data:
        tool_input = hook_data.get("tool_input", {})
        if isinstance(tool_input, dict):
            # 文件操作 → 用文件名
            fp = tool_input.get("file_path", tool_input.get("filePath", ""))
            if fp:
                fname = Path(fp).stem.lower()
                fname = re.sub(r'[^a-z0-9-]', '-', fname)
                if fname:
                    parts.append(fname)

            # Bash → 用命令前几个词
            cmd = tool_input.get("command", "")
            if cmd and not parts:
                words = cmd.split()[:3]
                cmd_slug = "-".join(w.lower() for w in words if len(w) > 1)
                cmd_slug = re.sub(r'[^a-z0-9-]', '-', cmd_slug)
                if cmd_slug:
                    parts.append(cmd_slug)

    # 从内容提取中文关键词
    if not parts:
        chinese = re.findall(r'[一-鿿]{2,}', content[:100])
        if chinese:
            parts.append("".join(chinese[:4]))

    # fallback: 英文关键词
    if not parts:
        words = re.findall(r'[a-zA-Z]{3,}', content[:100])
        if words:
            parts.append("-".join(w.lower() for w in words[:3]))

    slug = "-".join(parts) if parts else "memory"
    # 清理和限制长度
    slug = re.sub(r'-+', '-', slug).strip('-')[:40]
    return slug


# ─────────────────────────────────────────────────────────────────────────────
# 写入原生记忆
# ─────────────────────────────────────────────────────────────────────────────

def write_memory_file(memory_dir: Path, content: str, mem_type: str, slug: str) -> Path:
    """写入单个 .md 记忆文件"""
    # 确保 slug 唯一
    base_slug = slug
    counter = 1
    while (memory_dir / f"{slug}.md").exists():
        # 检查是否重复内容
        existing = (memory_dir / f"{slug}.md").read_text(encoding="utf-8")
        if content[:100] in existing:
            return None  # 重复，跳过
        slug = f"{base_slug}-{counter}"
        counter += 1

    filepath = memory_dir / f"{slug}.md"

    # 格式化描述 — 提取有意义的部分
    description = ""
    # 优先从 "内容:" 部分提取
    if "内容:" in content:
        desc_part = content.split("内容:", 1)[1].strip()
        description = desc_part.split("|")[0].strip()[:80]
    elif "文件:" in content:
        # 文件操作 → 用文件名
        fp = content.split("文件:", 1)[1].split("|")[0].strip()
        description = Path(fp).name
    elif "命令:" in content:
        cmd = content.split("命令:", 1)[1].split("|")[0].strip()
        description = cmd[:80]
    else:
        first_line = content.split("\n")[0].strip()
        description = first_line[:80] if first_line else content[:80]

    file_content = f"""---
name: {slug}
description: {description}
metadata:
  type: {mem_type}
---

{content}
"""
    filepath.write_text(file_content, encoding="utf-8")
    return filepath


def update_memory_index(memory_dir: Path, slug: str, description: str, mem_type: str):
    """更新 MEMORY.md 索引"""
    index_path = get_memory_index(memory_dir)

    # 读取现有索引
    existing_lines = []
    if index_path.exists():
        existing_lines = index_path.read_text(encoding="utf-8").splitlines()

    # 检查是否已存在
    entry = f"- [{description[:50]}]({slug}.md)"
    for line in existing_lines:
        if slug in line:
            return  # 已存在

    # 追加新条目
    if not existing_lines:
        existing_lines = [f"# Memory Index\n"]

    existing_lines.append(entry)
    index_path.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# 从 Hook 输入提取有意义内容
# ─────────────────────────────────────────────────────────────────────────────

def parse_hook_input(raw: str) -> dict:
    """Parse Claude Code hook JSON stdin."""
    try:
        data = json.loads(raw, strict=False)
        return {
            "session_id": data.get("session_id", ""),
            "tool_name": data.get("tool_name", ""),
            "cwd": data.get("cwd", ""),
            "tool_input": data.get("tool_input", {}),
            "hook_event_name": data.get("hook_event_name", ""),
            "stop_hook_active": data.get("stop_hook_active", False),
        }
    except (json.JSONDecodeError, TypeError):
        return {"raw_text": raw}


def extract_meaningful_content(hook_data: dict) -> str:
    """从 hook 数据中提取有意义的文本用于记忆存储。"""
    parts = []

    cwd = hook_data.get("cwd", "")
    if cwd:
        project = Path(cwd).name
        parts.append(f"项目: {project}")

    tool_name = hook_data.get("tool_name", "")
    if tool_name:
        parts.append(f"工具: {tool_name}")

    tool_input = hook_data.get("tool_input", {})
    if isinstance(tool_input, dict):
        # Write/Edit: 提取文件路径和内容摘要
        file_path = tool_input.get("file_path", tool_input.get("filePath", ""))
        if file_path:
            parts.append(f"文件: {file_path}")

        content = tool_input.get("content", "")
        if content and len(content) > 30:
            summary = content[:300].replace("\n", " ").strip()
            if len(content) > 300:
                summary += "..."
            parts.append(f"内容: {summary}")

        # Bash: 提取命令
        command = tool_input.get("command", "")
        if command:
            parts.append(f"命令: {command[:200]}")

        # 原始文本
        raw_text = hook_data.get("raw_text", "")
        if raw_text and len(raw_text) > 30:
            parts.append(raw_text[:500])

    return " | ".join(parts) if parts else ""


# ─────────────────────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # 读取 stdin with encoding fix for Windows
    content = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.buffer.read()
            content = raw.decode("utf-8", errors="replace").strip()
    except Exception:
        try:
            if not sys.stdin.isatty():
                content = _sanitize(sys.stdin.read().strip())
        except Exception:
            pass

    if not content:
        sys.exit(0)

    # 解析 hook JSON
    hook_data = parse_hook_input(content)
    cwd = hook_data.get("cwd", os.getcwd())

    # 提取有意义内容
    meaningful = extract_meaningful_content(hook_data)

    if not meaningful or len(meaningful) < 30:
        sys.exit(0)

    # 质量过滤
    if not is_worth_remembering(meaningful):
        sys.exit(0)

    # 分类
    mem_type = classify_content(meaningful)

    # 生成 slug
    slug = generate_slug(meaningful, hook_data)

    # 获取项目记忆目录
    memory_dir = get_project_memory_dir(cwd)

    # 写入记忆文件
    filepath = write_memory_file(memory_dir, meaningful, mem_type, slug)
    if filepath:
        # 更新索引 — 用文件中已格式化的 description
        desc_text = filepath.read_text(encoding="utf-8")
        desc_match = re.search(r'description:\s*(.+)', desc_text)
        description = desc_match.group(1).strip() if desc_match else slug
        update_memory_index(memory_dir, slug, description, mem_type)
        print(f"[jiaolong] 记忆已写入原生系统: {filepath.name} (type={mem_type})")

    sys.exit(0)


if __name__ == "__main__":
    main()
