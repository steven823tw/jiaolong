# -*- coding: utf-8 -*-
"""
jiaolong Cowork Memory Extract Hook
> 版本: v5.0.0 | 2026-04-30
> 用途: Claude Code Stop hook - 每次对话结束时提取并保存新记忆
"""
from __future__ import annotations
import json, sys, os, hashlib
from pathlib import Path
from datetime import datetime

HOME = Path.home()
JIAOLONG_DIR = HOME / ".claude" / "jiaolong"
MEMORY_DIR = JIAOLONG_DIR / "memory"
MEMORY_HOT = MEMORY_DIR / "memory_hot.json"

def ensure_dirs():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def load_memories() -> dict:
    if not MEMORY_HOT.exists():
        return {"facts": [], "version": "1.0"}
    try:
        with open(MEMORY_HOT, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"facts": data, "version": "1.0"}
        return data
    except Exception:
        return {"facts": [], "version": "1.0"}

def save_memories(data: dict):
    ensure_dirs()
    with open(MEMORY_HOT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def classify_content(content: str) -> str:
    content_lower = content.lower()
    if any(w in content_lower for w in ["决定", "选择", "decision", "choose"]):
        return "decision"
    if any(w in content_lower for w in ["偏好", "喜欢", "preference", "like"]):
        return "preference"
    if any(w in content_lower for w in ["项目", "project", "repo"]):
        return "project"
    if any(w in content_lower for w in ["目标", "goal", "target"]):
        return "goal"
    if any(w in content_lower for w in ["学习", "知识", "learn", "knowledge"]):
        return "knowledge"
    if any(w in content_lower for w in ["bug", "错误", "fix", "修复"]):
        return "technical"
    return "context"

def is_worth_remembering(content: str) -> bool:
    if len(content.strip()) < 20:
        return False
    if content.strip().startswith(("$", ">", "#", "PS")):
        return False
    if content.count("\n") > 5 and not any('\u4e00' <= c <= '\u9fff' for c in content):
        return False
    return True

def add_memory(content: str, category: str = None, source: str = "auto_extract"):
    if not is_worth_remembering(content):
        return False
    data = load_memories()
    facts = data.get("facts", [])
    content_lower = content.lower().strip()
    for fact in facts:
        existing = fact.get("content", "").lower().strip()
        if existing and (existing in content_lower or content_lower in existing):
            return False
    fact_id = hashlib.md5((content[:50] + datetime.now().isoformat()).encode()).hexdigest()[:12]
    new_fact = {
        "id": fact_id, "content": content[:500],
        "category": category or classify_content(content),
        "source": source, "createdAt": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(), "accessCount": 0, "confidence": 0.7,
    }
    facts.append(new_fact)
    if len(facts) > 2000:
        facts = facts[-2000:]
    data["facts"] = facts
    data["last_updated"] = datetime.now().isoformat()
    save_memories(data)
    return True

def main():
    ensure_dirs()
    content = ""
    try:
        if not sys.stdin.isatty():
            content = sys.stdin.read().strip()
    except Exception:
        pass
    if not content:
        sys.exit(0)
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    saved = 0
    for para in paragraphs:
        if add_memory(para):
            saved += 1
    if saved > 0:
        print(f"[jiaolong] 保存了 {saved} 条新记忆")
    sys.exit(0)

if __name__ == "__main__":
    main()