# -*- coding: utf-8 -*-
"""
jiaolong长期记忆智能演进
> 版本: v1.0 | 2026-04-02
> 功能:
>   - OMLX冷热存储智能交换
>   - 基于访问频率和重要性动态升降级
>   - 自动老化 + 智能归档
>   - 记忆访问模式学习
>
> 对应: Claude Code memory system
"""
from __future__ import annotations
import json, time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────────────────────

MEMORY_CONFIG = {
    "hot_max": 2000,          # 热层最大容量
    "warm_max": 10000,         # 温层最大容量
    "hot_ttl_days": 7,        # 热层TTL
    "warm_ttl_days": 30,      # 温层TTL
    "access_threshold": 3,     # 晋升阈值（7天内访问次数）
    "importance_threshold": 0.8,  # 重要性阈值（高重要性不下沉）
    "auto_swap_interval_hours": 6,  # 自动交换间隔
}


# ─────────────────────────────────────────────────────────────────────────────
# 记忆条目
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    category: str
    importance: float  # 0.0 - 1.0
    created_at: str
    updated_at: str
    access_count: int = 0       # 总访问次数
    last_access: str = ""       # 最后访问时间
    recent_accesses: List[str] = field(default_factory=list)  # 最近N次访问时间
    layer: str = "hot"          # hot / warm / cold
    tags: List[str] = field(default_factory=list)
    source: str = ""            # 来源：conversation/manual/extract

    def access(self):
        """记录一次访问"""
        now = datetime.now().isoformat()
        self.last_access = now
        self.access_count += 1
        self.recent_accesses.append(now)
        # 只保留最近7次
        self.recent_accesses = self.recent_accesses[-7:]

    def should_promote(self) -> bool:
        """是否应该晋升（热→温需要降级，温→热需要晋升）"""
        if self.layer != "hot":
            return False
        # 7天内访问>=阈值
        recent = self._recent_access_count(7)
        return recent >= MEMORY_CONFIG["access_threshold"]

    def should_demote(self) -> bool:
        """是否应该降级"""
        if self.layer != "hot":
            return False
        # 太久没访问
        if not self.last_access:
            return False
        try:
            last = datetime.fromisoformat(self.last_access)
            days_since = (datetime.now() - last).days
            if days_since > MEMORY_CONFIG["hot_ttl_days"]:
                # 高重要性保护
                if self.importance >= MEMORY_CONFIG["importance_threshold"]:
                    return False
                return True
        except:
            pass
        return False

    def _recent_access_count(self, days: int) -> int:
        """最近N天访问次数"""
        if not self.last_access:
            return 0
        try:
            cutoff = datetime.now() - timedelta(days=days)
            count = 0
            for ts_str in self.recent_accesses:
                ts = datetime.fromisoformat(ts_str)
                if ts >= cutoff:
                    count += 1
            return count
        except:
            return 0


# ─────────────────────────────────────────────────────────────────────────────
# 智能记忆管理器
# ─────────────────────────────────────────────────────────────────────────────

class SmartMemoryManager:
    """
    智能记忆管理器

    能力:
    1. 三层存储（hot/warm/cold）
    2. 自动晋升/降级
    3. 基于重要性的分层
    4. 访问模式学习
    """

    def __init__(self,
                 hot_file: str = None,
                 warm_dir: str = None,
                 cold_dir: str = None):
        ws = Path(r"C:\Users\steve\.openclaw\workspace")
        self.hot_file = Path(hot_file or ws / "memory" / "memory_hot.json")
        self.warm_dir = Path(warm_dir or ws / "memory" / "memory_warm")
        self.cold_dir = Path(cold_dir or ws / "memory" / "memory_cold")

        # 确保目录存在
        self.hot_file.parent.mkdir(parents=True, exist_ok=True)
        self.warm_dir.mkdir(parents=True, exist_ok=True)
        self.cold_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存
        self._hot_cache: Dict[str, MemoryEntry] = {}
        self._last_swap: Optional[datetime] = None
        self._swap_interval = timedelta(
            hours=MEMORY_CONFIG["auto_swap_interval_hours"]
        )

        self._load_hot()

    def _load_hot(self):
        """加载热层记忆"""
        if not self.hot_file.exists():
            return

        try:
            data = json.loads(self.hot_file.read_text(encoding="utf-8"))
            facts = data if isinstance(data, list) else data.get("facts", [])

            for f in facts:
                entry = MemoryEntry(
                    id=f.get("id", ""),
                    content=f.get("content", ""),
                    category=f.get("category", "?"),
                    importance=f.get("importance", 0.5),
                    created_at=f.get("createdAt", ""),
                    updated_at=f.get("updatedAt", ""),
                    access_count=f.get("accessCount", 0),
                    last_access=f.get("lastAccess", ""),
                    recent_accesses=f.get("recentAccesses", []),
                    layer=f.get("layer", "hot"),
                    tags=f.get("tags", []),
                    source=f.get("source", ""),
                )
                self._hot_cache[entry.id] = entry
        except Exception as e:
            pass

    def _save_hot(self):
        """保存热层记忆"""
        facts = []
        for entry in self._hot_cache.values():
            facts.append({
                "id": entry.id,
                "content": entry.content,
                "category": entry.category,
                "importance": entry.importance,
                "createdAt": entry.created_at,
                "updatedAt": entry.updated_at,
                "accessCount": entry.access_count,
                "lastAccess": entry.last_access,
                "recentAccesses": entry.recent_accesses,
                "layer": entry.layer,
                "tags": entry.tags,
                "source": entry.source,
            })

        data = {
            "facts": facts,
            "updatedAt": datetime.now().isoformat(),
            "count": len(facts),
        }

        self.hot_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def access(self, fact_id: str) -> Optional[MemoryEntry]:
        """
        记录一次记忆访问
        触发晋升/降级检查
        """
        entry = self._hot_cache.get(fact_id)
        if not entry:
            return None

        entry.access()

        # 检查是否应该晋升/降级
        if entry.should_promote():
            self._promote(entry)
        elif entry.should_demote():
            self._demote(entry)

        # 检查是否需要自动交换
        self._maybe_auto_swap()

        return entry

    def add(self, content: str, category: str,
            importance: float = 0.5,
            tags: List[str] = None,
            source: str = "manual") -> MemoryEntry:
        """添加新记忆"""
        import uuid
        now = datetime.now().isoformat()

        entry = MemoryEntry(
            id=str(uuid.uuid4())[:8],
            content=content,
            category=category,
            importance=importance,
            created_at=now,
            updated_at=now,
            layer="hot",
            tags=tags or [],
            source=source,
        )

        self._hot_cache[entry.id] = entry

        # 如果热层满了，触发交换
        if len(self._hot_cache) > MEMORY_CONFIG["hot_max"]:
            self._evict_to_warm()

        self._save_hot()
        return entry

    def _promote(self, entry: MemoryEntry):
        """晋升 - 热→温（不应该发生，但保留）"""
        entry.layer = "warm"

    def _demote(self, entry: MemoryEntry):
        """降级 - 热→温"""
        entry.layer = "warm"
        self._save_hot_to_warm(entry)

    def _save_hot_to_warm(self, entry: MemoryEntry):
        """保存降级记忆到温层"""
        month = datetime.now().strftime("%Y-%m")
        warm_file = self.warm_dir / f"{month}.json"

        data = []
        if warm_file.exists():
            try:
                data = json.loads(warm_file.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    data = []
            except:
                data = []

        data.append({
            "id": entry.id,
            "content": entry.content,
            "category": entry.category,
            "importance": entry.importance,
            "createdAt": entry.created_at,
            "updatedAt": datetime.now().isoformat(),
            "layer": "warm",
            "tags": entry.tags,
            "source": entry.source,
        })

        warm_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 从热层移除
        self._hot_cache.pop(entry.id, None)

    def _evict_to_warm(self):
        """热层满了，驱逐最冷的记忆到温层"""
        if not self._hot_cache:
            return

        # 按访问时间和重要性排序
        candidates = sorted(
            self._hot_cache.values(),
            key=lambda e: (e._recent_access_count(7), e.importance),
        )

        # 驱逐最冷的10%
        evict_count = max(1, len(self._hot_cache) // 10)
        for entry in candidates[:evict_count]:
            self._demote(entry)

    def _maybe_auto_swap(self):
        """检查是否需要自动交换"""
        now = datetime.now()
        if self._last_swap and now - self._last_swap < self._swap_interval:
            return

        self._auto_swap()
        self._last_swap = now

    def _auto_swap(self):
        """
        自动交换：
        1. 检查热层TTL，过期降级
        2. 检查温层晋升机会
        3. 更新索引
        """
        to_demote = []
        to_promote = []

        now = datetime.now()

        # 热层: 检查降级
        for entry in list(self._hot_cache.values()):
            if entry.layer != "hot":
                continue
            if not entry.last_access:
                continue
            try:
                last = datetime.fromisoformat(entry.last_access)
                days = (now - last).days
                if days > MEMORY_CONFIG["hot_ttl_days"]:
                    if entry.importance < MEMORY_CONFIG["importance_threshold"]:
                        to_demote.append(entry)
            except:
                pass

        # 执行降级
        for entry in to_demote:
            self._demote(entry)

        # 检查温层是否有可晋升的
        self._check_warm_promotions()

    def _check_warm_promotions(self):
        """检查温层是否有记忆应该晋升到热层"""
        # 读取温层最新月份
        if not self._warm_dir_has_files():
            return

        # 简化: 只检查最近一周的温层
        month = datetime.now().strftime("%Y-%m")
        warm_file = self.warm_dir / f"{month}.json"

        if not warm_file.exists():
            return

        try:
            data = json.loads(warm_file.read_text(encoding="utf-8"))
            to_promote = []

            for f in data:
                recent = f.get("recentAccesses", [])
                # 一周内访问>=阈值
                if len(recent) >= MEMORY_CONFIG["access_threshold"]:
                    to_promote.append(f)

            # 晋升到热层
            for f in to_promote:
                if len(self._hot_cache) >= MEMORY_CONFIG["hot_max"]:
                    break
                entry = MemoryEntry(
                    id=f["id"],
                    content=f["content"],
                    category=f.get("category", "?"),
                    importance=f.get("importance", 0.5),
                    created_at=f.get("createdAt", ""),
                    updated_at=f.get("updatedAt", ""),
                    access_count=f.get("accessCount", 0),
                    last_access=f.get("lastAccess", ""),
                    recent_accesses=f.get("recentAccesses", []),
                    layer="hot",
                    tags=f.get("tags", []),
                    source=f.get("source", ""),
                )
                self._hot_cache[entry.id] = entry

            # 从温层移除
            if to_promote:
                data = [f for f in data if f["id"] not in [e.id for e in [MemoryEntry(**f) for f in to_promote]]]
                warm_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        except Exception:
            pass

    def _warm_dir_has_files(self) -> bool:
        return bool(list(self.warm_dir.glob("*.json")))

    def stats(self) -> dict:
        """获取记忆统计"""
        hot_count = len(self._hot_cache)

        warm_count = 0
        cold_count = 0

        try:
            for wf in self.warm_dir.glob("*.json"):
                data = json.loads(wf.read_text(encoding="utf-8"))
                warm_count += len(data) if isinstance(data, list) else 0
        except:
            pass

        try:
            for cf in self.cold_dir.glob("*.json"):
                data = json.loads(cf.read_text(encoding="utf-8"))
                cold_count += len(data) if isinstance(data, list) else 0
        except:
            pass

        return {
            "hot": hot_count,
            "warm": warm_count,
            "cold": cold_count,
            "total": hot_count + warm_count + cold_count,
            "hot_capacity": MEMORY_CONFIG["hot_max"],
            "last_swap": self._last_swap.isoformat() if self._last_swap else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Smart Memory Manager 验证 ===\n")

    manager = SmartMemoryManager()
    stats = manager.stats()

    print(f"记忆统计:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n[OK] Smart Memory Manager ready")
