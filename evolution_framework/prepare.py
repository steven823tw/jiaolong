# -*- coding: utf-8 -*-
"""
jiaolong自进化框架 - prepare.py
> 固定基础设施（参照 Karpathy AutoResearch）
> 版本: v1.0 | 2026-04-02

本文件特点：
- 固定不变，不参与实验
- 提供所有实验依赖的基础设施
- 包括：记忆访问、指标采集、会话历史、工具注册、输出格式化

灵感来源：
- Karpathy AutoResearch: prepare.py = 数据准备 + 运行时工具
- Claude Code: extractMemories 自动记忆提取
"""

import os
import sys
import json
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# ─────────────────────────────────────────────────────────────────────────────
# 路径配置（固定）
# ─────────────────────────────────────────────────────────────────────────────
import os
WORKSPACE = Path(os.environ.get("JIAOLONG_WORKSPACE", str(Path.home() / ".claude" / "jiaolong")))
MEMORY_DIR    = WORKSPACE / "memory"
SKILLS_DIR    = WORKSPACE / "skills"
MEMORY_HOT    = MEMORY_DIR / "memory_hot.json"
MEMORY_INDEX  = MEMORY_DIR / "memory_index.json"
EVOLUTION_DIR = WORKSPACE / "evolution_framework"

# ─────────────────────────────────────────────────────────────────────────────
# 1. 记忆系统访问（OMLX 冷热记忆）
# ─────────────────────────────────────────────────────────────────────────────

class MemoryStore:
    """OMLX 记忆存储访问接口"""

    def __init__(self):
        self.hot_path    = MEMORY_HOT
        self.index_path  = MEMORY_INDEX
        self.warm_dir   = MEMORY_DIR / "memory_warm"
        self.cold_dir   = MEMORY_DIR / "memory_cold"

    def read_hot(self) -> List[Any]:
        """读取热记忆"""
        try:
            with open(self.hot_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # 正确提取 facts 数组
                return data.get("facts", [])
        except Exception:
            pass
        return []

    def write_hot(self, items: List[Any]) -> bool:
        """写入热记忆"""
        try:
            self.hot_path.parent.mkdir(parents=True, exist_ok=True)
            # 保持原有的 {"facts": [...], "version": ...} 结构
            with open(self.hot_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict):
                existing["facts"] = items
                data_to_write = existing
            else:
                data_to_write = {"facts": items, "version": "1.0"}
            with open(self.hot_path, "w", encoding="utf-8") as f:
                json.dump(data_to_write, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def touch_item(self, fact_id: str) -> bool:
        """标记记忆条目被访问（触发热层晋升检查）"""
        items = self.read_hot()
        for i, item in enumerate(items):
            if isinstance(item, dict) and (item.get("id") == fact_id or item.get("fact_id") == fact_id):
                items[i]["updated"] = datetime.now().isoformat()
                items[i]["access_count"] = item.get("access_count", 0) + 1
                self.write_hot(items)
                return True
        return False

    def search_hot(self, query: str, top_k: int = 5) -> List[Any]:
        """
        搜索热记忆
        简化版：关键词匹配
        未来可升级为向量相似度搜索
        """
        items = self.read_hot()
        query_lower = query.lower()
        scored = []
        for item in items:
            text = json.dumps(item, ensure_ascii=False).lower()
            # 简单评分：命中次数
            score = 1
            if isinstance(item, dict):
                score = item.get("access_count", 1)
            if query_lower in text:
                scored.append((score, item))
        # 按评分降序
        scored.sort(reverse=True)
        return [item for _, item in scored[:top_k]]

    def add_fact(self, fact: Dict) -> bool:
        """
        添加新事实到热记忆
        fact 格式: {"id": "...", "type": "user|feedback|project|reference",
                    "content": "...", "updated": "ISO时间", "access_count": 1}
        """
        items = self.read_hot()
        # 生成ID
        if "id" not in fact:
            fact["id"] = hashlib.md5(
                (fact.get("content","") + datetime.now().isoformat()).encode()
            ).hexdigest()[:12]
        fact["updated"] = datetime.now().isoformat()
        fact["access_count"] = 1
        items.append(fact)
        # 限制容量 2000 条
        if len(items) > 2000:
            items = items[-2000:]
        return self.write_hot(items)

    def get_stats(self) -> Dict:
        """获取记忆统计"""
        items = self.read_hot()
        now = datetime.now()
        cutoff = now - timedelta(days=7)
        recent = 0
        total = 0
        for item in items:
            total += 1
            last_accessed = ""
            if isinstance(item, dict):
                last_accessed = item.get("lastAccessed","") or item.get("updated","")
            elif isinstance(item, str):
                last_accessed = item
            if last_accessed:
                try:
                    dt = datetime.fromisoformat(last_accessed.replace("Z",""))
                    if dt >= cutoff:
                        recent += 1
                except:
                    pass
        return {
            "total_items": total,
            "recent_items": recent,
            "hit_rate": recent / max(total, 1),
        }

# ─────────────────────────────────────────────────────────────────────────────
# 2. 会话历史访问
# ─────────────────────────────────────────────────────────────────────────────

class SessionHistory:
    """会话历史访问接口"""

    def __init__(self):
        self.workspace = WORKSPACE

    def recent_sessions(self, limit: int = 5) -> List[Dict]:
        """
        读取最近的会话摘要
        简化版：从 MEMORY.md 提取最近会话记录
        """
        memory_file = self.workspace / "MEMORY.md"
        if not memory_file.exists():
            return []
        # 解析 MEMORY.md 中的会话记录（简化）
        try:
            content = memory_file.read_text(encoding="utf-8")
            # 提取最近 N 条历史快照
            sessions = []
            lines = content.split("\n")
            for line in lines:
                if "### 20" in line and "-" in line:  # 匹配日期行
                    sessions.append({"date": line.strip("# ").strip()})
            return sessions[-limit:]
        except Exception:
            return []

    def session_content(self, session_id: str) -> str:
        """
        读取指定会话内容
        未来可通过 OpenClaw API 获取完整历史
        """
        return ""  # 暂不实现

# ─────────────────────────────────────────────────────────────────────────────
# 3. 指标采集（Metrics）
# ─────────────────────────────────────────────────────────────────────────────

METRICS_DEFINITIONS = {
    "memory_hit_rate": {
        "name": "记忆命中率",
        "target": 0.80,
        "description": "7天内相同问题命中热记忆的比例",
        "measure": "recent_items / total_items in memory_hot.json",
    },
    "tool_coverage": {
        "name": "工具完善度",
        "target": 0.70,
        "description": "已实现工具占高频场景所需工具的比例",
        "measure": "implemented_tools / required_tools",
    },
    "l2_l3_ratio": {
        "name": "L2+L3自动化率",
        "target": 0.80,
        "description": "SRE场景中L2/L3等级占比",
        "measure": "(L2+L3 count) / total scenes",
    },
    "collaboration_score": {
        "name": "协作效率",
        "target": 0.80,
        "description": "三脑协作均衡度",
        "measure": "完整三脑定义 + 协作流程",
    },
    "skill_count": {
        "name": "Skill数量",
        "target": 20,
        "description": "已创建的Skill数量",
        "measure": "count of SKILL.md files",
    },
    "context_compression": {
        "name": "上下文压缩率",
        "target": 0.95,
        "description": "上下文压缩后关键信息保留率",
        "measure": "compressed_info / original_info",
    },
}

class MetricsCollector:
    """指标采集器"""

    def __init__(self):
        self.memory = MemoryStore()
        self.sessions = SessionHistory()

    def collect_all(self) -> Dict[str, float]:
        """采集所有指标"""
        m = self.memory
        stats = m.get_stats()

        result = {
            "memory_hit_rate": round(stats["hit_rate"], 4),
            "tool_coverage":   0.20,   # 暂定
            "l2_l3_ratio":     0.35,   # 暂定
            "collaboration_score": 0.50,  # 暂定
            "skill_count":      self._count_skills(),
            "context_compression": 0.00,  # 暂无
        }
        return result

    def _count_skills(self) -> int:
        """统计Skill数量"""
        count = 0
        for p in SKILLS_DIR.rglob("SKILL.md"):
            count += 1
        return count

    def report(self) -> str:
        """生成指标报告"""
        metrics = self.collect_all()
        lines = ["## 指标报告", f"**时间**: {datetime.now().isoformat()}", ""]
        lines.append("| 指标 | 当前 | 目标 | 达成率 |")
        lines.append("|------|------|------|--------|")
        for key, info in METRICS_DEFINITIONS.items():
            cur = metrics.get(key, 0)
            tgt = info["target"]
            if key == "skill_count":
                pct = cur / tgt if tgt > 0 else 0
                lines.append(f"| {info['name']} | {int(cur)} | {int(tgt)} | {pct:.0%} |")
            else:
                pct = cur / tgt if tgt > 0 else 0
                lines.append(f"| {info['name']} | {cur:.1%} | {tgt:.1%} | {pct:.0%} |")
        return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# 4. 工具注册表（Tool Registry）
# ─────────────────────────────────────────────────────────────────────────────

TOOL_REGISTRY = [
    # 基础工具（已实现）
    {"name": "read",        "category": "file",   "status": "implemented"},
    {"name": "write",       "category": "file",   "status": "implemented"},
    {"name": "edit",        "category": "file",   "status": "implemented"},
    {"name": "exec",        "category": "system",  "status": "implemented"},
    {"name": "web_search",  "category": "search",  "status": "implemented"},
    {"name": "web_fetch",   "category": "search",  "status": "implemented"},
    {"name": "memory_search","category": "memory", "status": "implemented"},
    {"name": "memory_get",  "category": "memory",  "status": "implemented"},
    # 高频缺失工具（待实现）
    {"name": "TaskCreateTool",   "category": "task",     "status": "missing"},
    {"name": "TaskUpdateTool",   "category": "task",     "status": "missing"},
    {"name": "MCPTool",          "category": "mcp",      "status": "missing"},
    {"name": "LSPTool",          "category": "lsp",      "status": "missing"},
    {"name": "NotebookEditTool", "category": "notebook",  "status": "missing"},
    {"name": "SyntheticOutput",  "category": "output",    "status": "missing"},
    # Claude Code 特色工具
    {"name": "SkillTool",        "category": "skill",    "status": "partial"},
    {"name": "AgentTool",         "category": "agent",   "status": "partial"},
    {"name": "TeamCreateTool",   "category": "team",    "status": "missing"},
    {"name": "WorktreeTool",      "category": "git",     "status": "missing"},
    {"name": "CronCreateTool",   "category": "schedule", "status": "partial"},
]

class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self.tools = TOOL_REGISTRY

    def get_status(self) -> Dict:
        total = len(self.tools)
        implemented = sum(1 for t in self.tools if t["status"] == "implemented")
        missing    = sum(1 for t in self.tools if t["status"] == "missing")
        partial    = sum(1 for t in self.tools if t["status"] == "partial")
        coverage   = implemented / total if total > 0 else 0
        return {
            "total":        total,
            "implemented":  implemented,
            "missing":      missing,
            "partial":      partial,
            "coverage":     round(coverage, 3),
        }

    def missing_tools(self, category: Optional[str] = None) -> List[Dict]:
        """列出缺失的工具"""
        tools = [t for t in self.tools if t["status"] == "missing"]
        if category:
            tools = [t for t in tools if t["category"] == category]
        return tools

    def report(self) -> str:
        status = self.get_status()
        missing = self.missing_tools()
        lines = ["## 工具注册表状态", ""]
        lines.append(f"- 总工具数: {status['total']}")
        lines.append(f"- 已实现: {status['implemented']} ({status['coverage']:.0%})")
        lines.append(f"- 部分实现: {status['partial']}")
        lines.append(f"- 缺失: {status['missing']}")
        lines.append("")
        lines.append("### 缺失工具（按优先级）")
        for t in missing:
            lines.append(f"- [{t['category']}] {t['name']}")
        return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# 5. 实验日志读取
# ─────────────────────────────────────────────────────────────────────────────

class ExperimentLog:
    """实验日志读取"""

    def __init__(self):
        self.log_file = EVOLUTION_DIR / "experiments" / "experiment_log.md"

    def recent(self, limit: int = 10) -> List[Dict]:
        """读取最近的实验记录"""
        if not self.log_file.exists():
            return []
        try:
            content = self.log_file.read_text(encoding="utf-8")
            lines = content.split("\n")
            records = []
            for line in lines[-limit:]:
                if line.startswith("| EXP-"):
                    parts = [p.strip() for p in line.split("|")[1:]]
                    if len(parts) >= 5:
                        records.append({
                            "id":       parts[0],
                            "time":     parts[1],
                            "hypothesis": parts[2],
                            "verdict":  parts[3],
                            "reason":   parts[4],
                        })
            return records
        except Exception:
            return []

    def summary(self) -> str:
        """生成实验汇总"""
        records = self.recent(limit=20)
        if not records:
            return "暂无实验记录"
        kept     = sum(1 for r in records if "KEPT" in r.get("verdict",""))
        discarded = sum(1 for r in records if "DISCARDED" in r.get("verdict",""))
        failed   = sum(1 for r in records if "FAILED" in r.get("verdict",""))
        lines = [
            "## 实验汇总",
            f"**总实验**: {len(records)}",
            f"**保留**: {kept} ({kept/len(records):.0%})",
            f"**丢弃**: {discarded} ({discarded/len(records):.0%})",
            f"**失败**: {failed}",
            "",
            "### 最近实验",
            "| ID | 时间 | 结果 | 原因 |",
            "|----|------|------|------|",
        ]
        for r in records[-5:]:
            emoji = {"KEPT":"✅","DISCARDED":"❌","FAILED":"💥"}.get(r.get("verdict",""),"")
            lines.append(f"| {r['id']} | {r['time'][:10]} | {emoji} | {r.get('reason','')[:30]} |")
        return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# 6. 输出格式化
# ─────────────────────────────────────────────────────────────────────────────

def format_header(title: str) -> str:
    return f"\n{'='*60}\n{title}\n{'='*60}"

def format_dict(d: Dict, indent: int = 2) -> str:
    lines = []
    for k, v in d.items():
        if isinstance(v, float):
            lines.append(f"{' '*indent}{k}: {v:.4f}")
        else:
            lines.append(f"{' '*indent}{k}: {v}")
    return "\n".join(lines)

def format_list(items: List, bullet: str = "-") -> str:
    return "\n".join(f"{bullet} {i}" for i in items)

# ─────────────────────────────────────────────────────────────────────────────
# 7. CLI 入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(format_header("jiaolong自进化框架 - 基础设施 (prepare.py)"))

    mem = MemoryStore()
    mtc = MetricsCollector()
    reg = ToolRegistry()
    exp = ExperimentLog()

    print(format_header("记忆系统状态"))
    print(format_dict(mem.get_stats()))

    print(format_header("指标采集"))
    print(mtc.report())

    print(format_header("工具注册表"))
    print(reg.report())

    print(format_header("实验日志"))
    print(exp.summary())

    print(format_header("缺失工具-P0优先级"))
    for t in reg.missing_tools()[:5]:
        print(f"  {t['category']:10s} {t['name']}")


# ═════════════════════════════════════════════════════════════════════════════
# NEW MEMORY METRICS (EXP-20260402-002)
# 替换旧的 memory_hit_rate 指标体系
# ═════════════════════════════════════════════════════════════════════════════

def new_fact_coverage() -> float:
    """
    新事实覆盖率
    = 过去24小时创建的事实数
    目标: > 5 条/天（表示记忆系统跟得上会话节奏）
    """
    hot_data = read_hot()
    facts = hot_data.get("facts", [])
    now = datetime.now()
    cutoff = now - timedelta(hours=24)
    recent = 0
    for f in facts:
        created = f.get("createdAt", "")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z",""))
                if dt >= cutoff:
                    recent += 1
            except:
                pass
    return float(recent)

def category_balance() -> float:
    """
    分类均衡度
    = 1 - (各类别最大差异 / 最大类别数量)
    目标: > 0.7
    """
    hot_data = read_hot()
    facts = hot_data.get("facts", [])
    cats = {}
    for f in facts:
        c = f.get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1
    if not cats:
        return 0.0
    vals = list(cats.values())
    max_val = max(vals)
    min_val = min(vals)
    return 1 - (max_val - min_val) / max_val

def fact_lifespan() -> float:
    """
    事实平均寿命（天）
    """
    hot_data = read_hot()
    facts = hot_data.get("facts", [])
    if not facts:
        return 0.0
    now = datetime.now()
    total_days = 0
    for f in facts:
        created = f.get("createdAt", "")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z",""))
                total_days += (now - dt).total_seconds() / 86400
            except:
                pass
    return total_days / len(facts)

def context_recall() -> float:
    """
    上下文召回率
    = 有访问记录的事实 / 总事实数
    目标: > 0.5
    """
    hot_data = read_hot()
    facts = hot_data.get("facts", [])
    if not facts:
        return 0.0
    accessed = sum(1 for f in facts if f.get("accessCount", 0) > 0)
    return accessed / len(facts)

