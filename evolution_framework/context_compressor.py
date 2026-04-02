# -*- coding: utf-8 -*-
"""
jiaolong LLM Context 压缩器
> 版本: v1.0 | 2026-04-02
> 功能:
>   - LLM级对话压缩（vs规则压缩）
>   - 智能摘要 + 关键信息保留
>   - 多轮对话压缩为紧凑上下文
>
> 依赖: llm_core.py (LLMManager)
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


# ─────────────────────────────────────────────────────────────────────────────
# 对话消息结构
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Message:
    role: str  # user / assistant / system
    content: str
    timestamp: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# LLM Context 压缩器
# ─────────────────────────────────────────────────────────────────────────────

class LLMContextCompressor:
    """
    LLM驱动的上下文压缩器

    能力:
    1. 对话历史 → 智能摘要
    2. 保留关键决策/结论/偏好
    3. 多轮会话压缩为单次摘要
    4. 支持增量压缩（新消息追加到已有摘要）
    """

    def __init__(self, provider: str = None):
        self._llm = None
        self._provider = provider
        self._summary_cache: Dict[str, str] = {}  # session_id -> summary

    @property
    def llm(self):
        if self._llm is None:
            from llm_core import get_summarizer
            self._llm = get_summarizer(self._provider)
        return self._llm

    def compress(self, messages: List[Message],
                 strategy: str = "smart",
                 max_output_chars: int = 1500) -> str:
        """
        压缩对话历史

        Args:
            messages: 消息列表
            strategy: "smart" / "aggressive" / "preserve_all"
            max_output_chars: 最大输出字符数

        Returns:
            压缩后的上下文字符串
        """
        if not messages:
            return ""

        if len(messages) <= 4:
            return self._format_short(messages)

        if strategy == "preserve_all":
            return self._format_full(messages)

        if strategy == "aggressive":
            return self._compress_aggressive(messages, max_output_chars)

        # smart: LLM压缩
        return self._compress_smart(messages, max_output_chars)

    def _format_short(self, messages: List[Message]) -> str:
        """格式短对话"""
        lines = []
        for m in messages:
            role_icon = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(m.role, "?")
            lines.append(f"{role_icon} {m.content}")
        return "\n".join(lines)

    def _format_full(self, messages: List[Message]) -> str:
        """格式完整对话"""
        return self._format_short(messages)

    def _compress_smart(self, messages: List[Message],
                        max_chars: int) -> str:
        """LLM智能压缩"""
        # 转换格式
        msg_dicts = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

        summary = self.llm.summarize_conversation(
            msg_dicts,
            max_summary_chars=max_chars // 2  # 摘要占一半
        )

        # 保留最后1-2条消息（最新上下文）
        recent = messages[-2:]
        recent_lines = [f"📌 最近: {m.content[:200]}" for m in recent]

        return summary + "\n\n" + "\n".join(recent_lines)

    def _compress_aggressive(self, messages: List[Message],
                            max_chars: int) -> str:
        """激进压缩 - 只保留摘要"""
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        return self.llm.summarize_conversation(
            msg_dicts,
            max_summary_chars=max_chars
        )

    def compress_incremental(self, old_summary: str,
                           new_messages: List[Message],
                           max_chars: int = 1000) -> str:
        """
        增量压缩 - 新消息追加到已有摘要

        Args:
            old_summary: 之前的摘要
            new_messages: 新消息
            max_chars: 最大输出

        Returns:
            更新后的摘要
        """
        if not new_messages:
            return old_summary

        from llm_core import get_llm

        llm = get_llm(self._provider)
        prompt = f"""将新消息整合到已有摘要中。

已有摘要:
{old_summary}

新消息:
{self._format_short(new_messages[-5:])}

要求:
1. 更新摘要，整合新信息
2. 保留关键结论和决策
3. 标记新的重要发现
4. 不超过{max_chars}字符

更新后的摘要:"""

        result = llm.complete(prompt, max_tokens=max_chars)
        return result.strip()

    def get_cache(self, session_id: str) -> Optional[str]:
        return self._summary_cache.get(session_id)

    def set_cache(self, session_id: str, summary: str):
        self._summary_cache[session_id] = summary

    def clear_cache(self, session_id: str = None):
        if session_id:
            self._summary_cache.pop(session_id, None)
        else:
            self._summary_cache.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 规则压缩器（备用）
# ─────────────────────────────────────────────────────────────────────────────

class RuleBasedCompressor:
    """
    规则基础压缩器（备用/LLM不可用时）
    基于关键词和消息评分
    """

    def __init__(self):
        self.keep_patterns = [
            r"决策", r"决定", r"选[A]", r"就用",
            r"错了", r"不对", r"重来",
            r"成功了", r"完成了", r"可以了",
            r"/new", r"/reset", r"/stop",
            r"\[决策\]", r"\[重要\]", r"!!!",
        ]
        self.noise_patterns = [
            r"好的", r"嗯", r"收到", r"了解",
            r"谢谢", r"好的好的", r"好的嗯",
        ]

    def compress(self, messages: List[Message],
                 max_messages: int = 20) -> List[Message]:
        """规则压缩：保留重要消息，删除噪音"""
        if len(messages) <= max_messages:
            return messages

        scored = []
        for m in messages:
            score = self._score_message(m)
            scored.append((score, m))

        # 按分数排序，保留top消息
        scored.sort(key=lambda x: -x[0])
        kept = [m for _, m in scored[:max_messages]]

        # 按原顺序重排
        kept.sort(key=lambda m: messages.index(m))
        return kept

    def _score_message(self, m: Message) -> float:
        score = 0.0
        content = m.content.lower()

        # 关键词加分
        for pattern in self.keep_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score += 1.0

        # 噪音减分
        for pattern in self.noise_patterns:
            if re.search(pattern, content):
                score -= 0.5

        # 长消息加分（通常更有价值）
        if len(content) > 50:
            score += 0.5

        # 工具调用加分
        if "[tool" in content or "```" in content:
            score += 0.5

        return score


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Context Compressor 验证 ===")

    # 测试规则压缩
    compressor = RuleBasedCompressor()

    test_messages = [
        Message("user", "好的"),
        Message("assistant", "收到！"),
        Message("user", "开始做jiaolong进化"),
        Message("assistant", "[决策] 确定使用蓝信作为通知渠道"),
        Message("user", "帮我选股"),
        Message("assistant", "选股完成！结果: 贵州茅台, 宁德时代"),
        Message("user", "谢谢"),
    ]

    compressed = compressor.compress(test_messages, max_messages=4)
    print(f"压缩: {len(test_messages)} -> {len(compressed)}")
    for m in compressed:
        print(f"  {m.role}: {m.content[:50]}")

    print("\n[OK] Context Compressor ready")
