# -*- coding: utf-8 -*-
"""
jiaolong 代码规则自动检查 Hook
> 版本: v5.0.0 | 2026-04-30
> 用途: Claude Code Stop hook - 代码写入后自动检查
"""
from __future__ import annotations
import json, sys, os, re
from pathlib import Path

HOME = Path.home()
JIAOLONG_DIR = HOME / ".claude" / "jiaolong"
EVOLUTION_DIR = JIAOLONG_DIR / "evolution_framework"
sys.path.insert(0, str(EVOLUTION_DIR))

def check_file(filepath: str) -> list:
    try:
        from rules_engine import PythonLinter
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        linter = PythonLinter(content, filepath)
        return linter.check_all()
    except ImportError:
        return simple_check(filepath)
    except Exception as e:
        return [{"rule": "system", "level": "error", "message": f"检查失败: {e}"}]

def simple_check(filepath: str) -> list:
    violations = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return violations
    for i, line in enumerate(lines, 1):
        if len(line.rstrip()) > 120:
            violations.append({"rule": "line-length", "level": "warning", "message": f"第 {i} 行超过 120 字符", "line": i})
        if re.search(r'\b(TODO|FIXME|HACK|XXX)\b', line):
            violations.append({"rule": "todo-fixme", "level": "info", "message": f"第 {i} 行包含 TODO/FIXME 标记", "line": i})
    return violations

def main():
    content = ""
    try:
        if not sys.stdin.isatty():
            content = sys.stdin.read().strip()
    except Exception:
        pass
    if not content:
        sys.exit(0)
    filepath = ""
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            filepath = data.get("tool_input", {}).get("file_path", "")
            if not filepath:
                filepath = data.get("file_path", "")
    except (json.JSONDecodeError, TypeError):
        filepath = content
    if not filepath or not filepath.endswith(".py"):
        sys.exit(0)
    if not os.path.exists(filepath):
        sys.exit(0)
    violations = check_file(filepath)
    if violations:
        print(f"\n[jiaolong rules] {os.path.basename(filepath)} 规则检查:")
        for v in violations:
            level = v.get("level", "info").upper()
            line = v.get("line", "")
            rule = v.get("rule", "")
            msg = v.get("message", "")
            prefix = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "💡"}.get(level, "•")
            line_info = f" (行 {line})" if line else ""
            print(f"  {prefix} [{rule}]{line_info} {msg}")
        if any(v.get("level") == "error" for v in violations):
            sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()