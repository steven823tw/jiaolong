# -*- coding: utf-8 -*-
"""
jiaolong Context Compression 服务
> 版本: v1.0 | 2026-04-02
> 对应: Claude Code services/compact/
> 用途: 智能压缩对话历史，防止context overflow
> 参考: deer-flow2 context management
"""
from __future__ import annotations
import json, re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
# 消息重要性评分器
# ─────────────────────────────────────────────────────────────────────────────

class MessageImportance:
    """
    消息重要性评分
    决定哪些消息应该保留/压缩/丢弃
    """

    # 高权重关键词（重要，必须保留）
    HIGH_WEIGHT_KW = {
        "decision": 1.5,   # 决策类
        "结论": 1.5,
        "确定": 1.4,
        "就按": 1.4,
        "方案": 1.3,
        "目标": 1.3,
        "优先级": 1.3,
        "完成": 1.2,
        "成功": 1.2,
        "失败": 1.2,
        "错误": 1.2,
        "token": 1.4,
        "API": 1.3,
        "路径": 1.2,
        "实证": 1.3,
        "验证": 1.2,
    }

    # 低权重关键词（可丢弃）
    LOW_WEIGHT_KW = {
        "好的": 0.3,
        "可以": 0.3,
        "收到": 0.3,
        "明白": 0.3,
        "嗯": 0.2,
        "哦": 0.2,
        "好吧": 0.2,
        "好吧": 0.2,
    }

    @classmethod
    def score(cls, role: str, content: str) -> float:
        """
        评分 0.0-1.0
        - role: user/assistant/system
        - content: 消息内容
        """
        score = 0.5  # 基础分

        # 角色权重
        if role == "user":
            score += 0.15
        elif role == "system":
            score += 0.10

        # 高权重关键词
        content_lower = content.lower()
        for kw, weight in cls.HIGH_WEIGHT_KW.items():
            if kw in content_lower:
                score += weight * 0.1

        # 低权重关键词
        for kw, weight in cls.LOW_WEIGHT_KW.items():
            if kw in content_lower:
                score -= weight * 0.1

        # 长度影响
        if len(content) < 10:
            score -= 0.2
        elif len(content) > 200:
            score += 0.1

        # 代码块（技术内容）
        if "```" in content:
            score += 0.1

        # 数字/日期（具体事实）
        if re.search(r"\d{4}-\d{2}-\d{2}", content):
            score += 0.1
        if re.search(r"\d+%", content):
            score += 0.1

        return max(0.0, min(1.0, score))

    @classmethod
    def classify(cls, role: str, content: str) -> str:
        """分类: critical / important / normal / noise"""
        s = cls.score(role, content)
        if s >= 0.8:
            return "critical"
        elif s >= 0.65:
            return "important"
        elif s >= 0.45:
            return "normal"
        else:
            return "noise"


# ─────────────────────────────────────────────────────────────────────────────
# 对话压缩器
# ─────────────────────────────────────────────────────────────────────────────

class ConversationChunk:
    """对话片段"""
    def __init__(self, messages: List[dict]):
        self.messages = messages
        self.importance = self._calc_importance()

    def _calc_importance(self) -> float:
        if not self.messages:
            return 0.0
        return sum(MessageImportance.score(m.get("role",""), m.get("content","")) for m in self.messages) / len(self.messages)

    def to_summary(self) -> str:
        """生成片段摘要"""
        if not self.messages:
            return ""
        first = self.messages[0]
        last = self.messages[-1]
        topics = self._extract_topics()
        return f"[{len(self.messages)}条消息] {topics}"

    def _extract_topics(self) -> str:
        """提取主题关键词"""
        all_content = " ".join(m.get("content", "") for m in self.messages)
        # 简单关键词提取
        important_words = re.findall(r"[\u4e00-\u9fa5]{2,}(?:分析|任务|工具|系统|模块|文件|策略|报告)", all_content)
        seen = set()
        unique = []
        for w in important_words:
            if w not in seen:
                seen.add(w)
                unique.append(w)
        return ", ".join(unique[:3]) if unique else "一般对话"


class ConversationCompressor:
    """
    对话历史压缩器
    智能决定保留/压缩/丢弃哪些消息
    """

    # 压缩模式
    MODE_SUMMARY = "summary"      # 生成摘要替换
    MODE_DROP = "drop"           # 直接丢弃
    MODE_MERGE = "merge"         # 合并多条

    # 每条消息平均token（估算）
    AVG_TOKENS_PER_MSG = 50

    def __init__(self, max_tokens: int = 80000):
        self.max_tokens = max_tokens

    def compress(self, messages: List[dict],
                  target_tokens: int = None,
                  mode: str = "smart") -> Tuple[List[dict], dict]:
        """
        压缩对话历史

        Args:
            messages: 原始消息列表
            target_tokens: 目标token数（默认保留50%）
            mode: summary/drop/smart

        Returns:
            (压缩后消息, 压缩报告)
        """
        target = target_tokens or self.max_tokens // 2
        original_count = len(messages)
        original_tokens = len(messages) * self.AVG_TOKENS_PER_MSG

        if original_tokens <= target:
            # 不需要压缩
            return messages, {
                "original_count": original_count,
                "compressed_count": original_count,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "compression_ratio": 1.0,
                "dropped": 0,
                "summarized": 0,
            }

        # 1. 评分并分类所有消息
        scored = []
        for i, msg in enumerate(messages):
            role = msg.get("role", "")
            content = msg.get("content", "")
            importance = MessageImportance.score(role, content)
            classification = MessageImportance.classify(role, content)
            scored.append({
                "index": i,
                "msg": msg,
                "importance": importance,
                "classification": classification,
            })

        # 2. 按重要性排序，分组
        critical = [s for s in scored if s["classification"] == "critical"]
        important = [s for s in scored if s["classification"] == "important"]
        normal = [s for s in scored if s["classification"] == "normal"]
        noise = [s for s in scored if s["classification"] == "noise"]

        # 3. Smart模式：优先保留critical+important
        compressed = []
        stats = {"critical": 0, "important": 0, "normal": 0, "noise": 0, "summarized_chunks": 0}
        current_tokens = 0

        # 先加critical
        for s in critical:
            if current_tokens >= target:
                break
            compressed.append(s["msg"])
            current_tokens += self.AVG_TOKENS_PER_MSG
            stats["critical"] += 1

        # 再加important
        for s in important:
            if current_tokens >= target:
                break
            compressed.append(s["msg"])
            current_tokens += self.AVG_TOKENS_PER_MSG
            stats["important"] += 1

        # 4. 处理normal：分组生成摘要
        remaining_target = target - current_tokens
        normal_count = len(normal)
        if normal_count > 0 and remaining_target > 0:
            if mode == "summary" or (mode == "smart" and current_tokens < target * 0.8):
                # 分组摘要
                chunk_size = max(3, normal_count // 5)
                for i in range(0, normal_count, chunk_size):
                    chunk_msgs = [s["msg"] for s in normal[i:i+chunk_size]]
                    chunk = ConversationChunk(chunk_msgs)
                    summary_msg = {
                        "role": "system",
                        "content": f"[记忆压缩] {chunk.to_summary()}",
                        "_compressed": True,
                        "_original_count": len(chunk_msgs),
                    }
                    if current_tokens + 30 < target:  # 摘要约30token
                        compressed.append(summary_msg)
                        current_tokens += 30
                        stats["summarized_chunks"] += 1
            else:
                # 直接保留部分
                keep_count = int(remaining_target / self.AVG_TOKENS_PER_MSG)
                keep_count = min(keep_count, normal_count)
                for s in normal[:keep_count]:
                    compressed.append(s["msg"])
                    current_tokens += self.AVG_TOKENS_PER_MSG
                    stats["normal"] += keep_count

        # 5. 丢弃noise
        stats["noise"] = len(noise)

        # 6. 保持顺序（按原始index排序）
        compressed.sort(key=lambda m: messages.index(m) if m in messages else -1)

        # 7. 生成报告
        compressed_count = len(compressed)
        compressed_tokens = compressed_count * self.AVG_TOKENS_PER_MSG
        compression_ratio = compressed_tokens / original_tokens if original_tokens else 1.0

        report = {
            "original_count": original_count,
            "compressed_count": compressed_count,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_ratio": round(compression_ratio, 3),
            "dropped": original_count - compressed_count,
            "summarized_chunks": stats["summarized_chunks"],
            "stats": stats,
        }

        return compressed, report

    def chunk_messages(self, messages: List[dict],
                       chunk_size: int = 20) -> List[ConversationChunk]:
        """将消息分块"""
        chunks = []
        for i in range(0, len(messages), chunk_size):
            chunk_msgs = messages[i:i+chunk_size]
            chunks.append(ConversationChunk(chunk_msgs))
        return chunks


# ─────────────────────────────────────────────────────────────────────────────
# 上下文窗口管理器
# ─────────────────────────────────────────────────────────────────────────────

class ContextWindowManager:
    """
    上下文窗口管理器
    自动监控和压缩，保持上下文在限制内
    """

    def __init__(self, max_tokens: int = 80000, warning_threshold: float = 0.80):
        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
        self.compressor = ConversationCompressor(max_tokens)

    def check(self, messages: List[dict]) -> dict:
        """检查当前上下文使用情况"""
        total_tokens = len(messages) * ConversationCompressor.AVG_TOKENS_PER_MSG
        usage = total_tokens / self.max_tokens if self.max_tokens else 0

        warnings = []
        if usage >= 1.0:
            warnings.append("CRITICAL: 上下文超出限制，需要立即压缩")
        elif usage >= self.warning_threshold:
            warnings.append(f"WARNING: 上下文使用 {usage:.0%}，建议压缩")

        return {
            "total_messages": len(messages),
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "usage_percent": round(usage * 100, 1),
            "needs_compression": usage >= self.warning_threshold,
            "warnings": warnings,
        }

    def auto_compress(self, messages: List[dict]) -> Tuple[List[dict], dict]:
        """自动压缩"""
        return self.compressor.compress(messages, mode="smart")


# ─────────────────────────────────────────────────────────────────────────────
# CLI / 工具接口
# ─────────────────────────────────────────────────────────────────────────────

def compress_conversation(messages: List[dict],
                          max_tokens: int = 80000,
                          mode: str = "smart") -> dict:
    """
    压缩对话（CLI入口）
    """
    compressor = ConversationCompressor(max_tokens)
    compressed, report = compressor.compress(messages, mode=mode)
    return {
        "compressed_messages": compressed,
        "report": report,
    }


if __name__ == "__main__":
    print("=== ConversationCompressor 验证 ===")

    # 模拟对话
    test_messages = [
        {"role": "system", "content": "你是一个AI助手"},
        {"role": "user", "content": "好的"},
        {"role": "user", "content": "开始分析A股"},
        {"role": "assistant", "content": "好的，开始分析A股。今日大盘低开..."},
        {"role": "user", "content": "企微改为蓝信，ansible改为脚本编排"},
        {"role": "assistant", "content": "收到修改！企微 -> 蓝信，Ansible -> 脚本编排。"},
        {"role": "system", "content": "[决策] 确定使用蓝信作为通知渠道"},
        {"role": "user", "content": "嗯"},
        {"role": "assistant", "content": "开始构建jiaolong自进化框架！"},
        {"role": "user", "content": "GO!!!"},
        {"role": "assistant", "content": "开始第一个AutoResearch实验！"},
        {"role": "user", "content": "可以"},
    ]

    # 评分验证
    print("\n--- 消息重要性评分 ---")
    for msg in test_messages:
        role = msg["role"]
        content = msg["content"]
        s = MessageImportance.score(role, content)
        c = MessageImportance.classify(role, content)
        print(f"  [{c:9s} {s:.2f}] {role}: {content[:30]}")

    # 压缩验证
    print("\n--- 压缩测试 ---")
    compressor = ConversationCompressor(max_tokens=300)
    compressed, report = compressor.compress(test_messages, mode="smart")
    print(f"原始: {report['original_count']}条 | 压缩后: {report['compressed_count']}条")
    print(f"压缩率: {report['compression_ratio']:.1%} | 丢弃: {report['dropped']}条")
    print(f"stats: {report['stats']}")

    # 窗口检查
    print("\n--- 窗口管理 ---")
    mgr = ContextWindowManager(max_tokens=400)
    check = mgr.check(test_messages)
    print(f"使用率: {check['usage_percent']}% | 需要压缩: {check['needs_compression']}")
    print(f"警告: {check['warnings']}")
