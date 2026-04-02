# -*- coding: utf-8 -*-
"""
jiaolong LLM 核心调用层
> 版本: v1.0 | 2026-04-02
> 功能:
>   1. 多Provider支持（OpenAI/Claude/MiniMax/本地）
>   2. 对话压缩Summarization
>   3. 任务智能分解
>   4. 记忆摘要生成
>
> 环境变量:
>   OPENAI_API_KEY, ANTHROPIC_API_KEY, MINIMAX_API_KEY
"""
from __future__ import annotations
import os, json, time
from typing import Any, Dict, List, Optional, Literal
from dataclasses import dataclass
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────────────────────

LLM_CONFIG = {
    "default_provider": "openai",  # openai / anthropic / minimax / local
    "openai": {
        "model": "gpt-4o-mini",
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "base_url": None,
        "max_tokens": 2000,
        "temperature": 0.3,
    },
    "anthropic": {
        "model": "claude-3-5-haiku-20241022",
        "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "max_tokens": 2000,
        "temperature": 0.3,
    },
    "minimax": {
        "model": "MiniMax-Text-01",
        "api_key": os.environ.get("MINIMAX_API_KEY", ""),
        "base_url": "https://api.minimax.chat/v1",
        "max_tokens": 2000,
        "temperature": 0.3,
    },
    "local": {
        "model": "llama3",
        "base_url": "http://localhost:11434",
        "max_tokens": 2000,
        "temperature": 0.3,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 消息格式
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LLMMessage:
    role: Literal["system", "user", "assistant"]
    content: str


# ─────────────────────────────────────────────────────────────────────────────
# LLM Provider接口
# ─────────────────────────────────────────────────────────────────────────────

class LLMProvider:
    """LLM Provider 基类"""

    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "")
        self.max_tokens = config.get("max_tokens", 2000)
        self.temperature = config.get("temperature", 0.3)

    def chat(self, messages: List[Dict], **kwargs) -> str:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI兼容Provider"""

    def chat(self, messages: List[Dict], **kwargs) -> str:
        try:
            import openai
        except ImportError:
            return self._fallback_chat(messages)

        api_key = self.config.get("api_key")
        if not api_key:
            return self._fallback_chat(messages)

        client = openai.OpenAI(
            api_key=api_key,
            base_url=self.config.get("base_url"),
        )

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
        )
        return response.choices[0].message.content


class MiniMaxProvider(LLMProvider):
    """MiniMax Provider"""

    def chat(self, messages: List[Dict], **kwargs) -> str:
        api_key = self.config.get("api_key")
        base_url = self.config.get("base_url", "https://api.minimax.chat/v1")

        if not api_key:
            return "[MiniMax API key not set]"

        try:
            import openai
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[MiniMax error: {e}]"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude Provider"""

    def chat(self, messages: List[Dict], **kwargs) -> str:
        api_key = self.config.get("api_key")
        if not api_key:
            return "[Anthropic API key not set]"

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            # 转换消息格式
            sys_msg = ""
            prompt_messages = []
            for m in messages:
                if m["role"] == "system":
                    sys_msg = m["content"]
                else:
                    prompt_messages.append(m)

            response = client.messages.create(
                model=self.model,
                system=sys_msg,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                messages=prompt_messages,
            )
            return response.content[0].text
        except Exception as e:
            return f"[Anthropic error: {e}]"


class LocalProvider(LLMProvider):
    """本地Ollama Provider"""

    def chat(self, messages: List[Dict], **kwargs) -> str:
        base_url = self.config.get("base_url", "http://localhost:11434")

        try:
            import openai
            client = openai.OpenAI(base_url=base_url, api_key="ollama")
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[Local LLM error: {e}]"


# ─────────────────────────────────────────────────────────────────────────────
# LLM Manager
# ─────────────────────────────────────────────────────────────────────────────

class LLMManager:
    """
    LLM管理器 - 统一接口
    支持多Provider自动切换
    """

    def __init__(self, provider: str = None):
        self.provider_name = provider or LLM_CONFIG["default_provider"]
        self._provider: Optional[LLMProvider] = None
        self._init_provider()

    def _init_provider(self):
        config = LLM_CONFIG.get(self.provider_name, {})
        if self.provider_name == "openai":
            self._provider = OpenAIProvider(config)
        elif self.provider_name == "minimax":
            self._provider = MiniMaxProvider(config)
        elif self.provider_name == "anthropic":
            self._provider = AnthropicProvider(config)
        elif self.provider_name == "local":
            self._provider = LocalProvider(config)
        else:
            self._provider = OpenAIProvider(LLM_CONFIG["openai"])

    def chat(self, messages: List[Dict], **kwargs) -> str:
        """发送对话，返回内容"""
        return self._provider.chat(messages, **kwargs)

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        """简版补全"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)

    @property
    def model(self) -> str:
        """当前使用的模型"""
        return self._provider.model if self._provider else "unknown"

    def available(self) -> bool:
        """检查Provider是否可用"""
        if not self._provider:
            return False
        test = self.chat([{"role": "user", "content": "hi"}], max_tokens=5)
        return not (test.startswith("[") or "not set" in test or "error" in test.lower())


# ─────────────────────────────────────────────────────────────────────────────
# 高层能力
# ─────────────────────────────────────────────────────────────────────────────

class LLMSummarizer:
    """
    LLM驱动的对话压缩
    将长对话历史压缩为摘要
    """

    def __init__(self, provider: str = None):
        self.llm = LLMManager(provider)

    def summarize_conversation(self, messages: List[Dict],
                             max_summary_chars: int = 500) -> str:
        """
        将对话历史压缩为摘要

        Args:
            messages: [{"role": ..., "content": ...}, ...]
            max_summary_chars: 摘要最大字符数

        Returns:
            压缩后的摘要字符串
        """
        if not messages:
            return ""

        # 如果消息很少，不需要压缩
        total_chars = sum(len(m.get("content", "")) for m in messages)
        if total_chars < 1000:
            return f"[原始对话 {len(messages)}条, {total_chars}字符]"

        # 构建压缩prompt
        prompt = self._build_summary_prompt(messages, max_summary_chars)
        system = "你是对话摘要专家。简洁提取关键信息，生成有意义的摘要。"

        summary = self.llm.complete(prompt, system=system, max_tokens=800)

        return summary.strip()

    def _build_summary_prompt(self, messages: List[Dict],
                              max_chars: int) -> str:
        """构建摘要prompt"""
        # 转换消息格式
        formatted = []
        for m in messages:
            role = {"assistant": "Assistant", "user": "User",
                   "system": "System"}.get(m["role"], m["role"])
            content = m.get("content", "")[:500]  # 每条截断
            formatted.append(f"{role}: {content}")

        conversation = "\n".join(formatted[-20:])  # 只取最后20条

        return f"""请将以下对话压缩为{max_chars}字符以内的摘要。

要求:
1. 保留关键话题、决策、结论
2. 保留用户的具体需求和问题
3. 保留重要的技术细节
4. 忽略寒暄和重复内容

对话:
{conversation}

摘要:"""


class LLMDecomposer:
    """
    LLM驱动的任务分解
    将复杂任务智能拆解为子任务
    """

    def __init__(self, provider: str = None):
        self.llm = LLMManager(provider)

    def decompose(self, task: str, context: str = "",
                  available_tools: List[str] = None) -> List[Dict]:
        """
        分解复杂任务

        Args:
            task: 用户任务描述
            context: 额外上下文
            available_tools: 可用工具列表

        Returns:
            [{"subtask": str, "tool": str, "agent": str, "priority": int}, ...]
        """
        tools_str = ""
        if available_tools:
            tools_str = "\n可用工具: " + ", ".join(available_tools[:20])

        prompt = f"""将以下任务分解为3-8个子任务。

任务: {task}
{tools_str}
{context}

要求:
- 每个子任务描述清晰、具体
- 指定适合的agent角色(boss/intel/ux/backend)
- 指定工具或技能（如果有）
- 按执行顺序排列

JSON格式输出:
{{"subtasks": [
  {{"description": "子任务描述", "agent": "角色", "tool": "工具", "priority": 1}},
  ...
]}}
"""

        system = """你是任务分解专家。分析复杂任务，拆解为可执行的子任务。
只输出JSON，不要其他内容。"""

        result = self.llm.complete(prompt, system=system, max_tokens=1000)

        # 解析JSON
        try:
            # 尝试提取JSON
            json_str = self._extract_json(result)
            data = json.loads(json_str)
            return data.get("subtasks", [])
        except json.JSONDecodeError:
            return [{"description": task, "agent": "boss",
                    "tool": None, "priority": 1}]

    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON"""
        # 尝试找 ```json ... ```
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return match.group(1)

        # 尝试找 {...}
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)

        return text


class MemorySummarizer:
    """
    记忆摘要生成器
    从会话中提取关键记忆写入memory_hot.json
    """

    def __init__(self, provider: str = None):
        self.llm = LLMManager(provider)

    def extract_memories(self, messages: List[Dict],
                        categories: List[str] = None) -> List[Dict]:
        """
        从对话消息中提取记忆

        Args:
            messages: 对话历史
            categories: 记忆类别偏好

        Returns:
            [{"content": str, "category": str, "confidence": float}, ...]
        """
        cat_list = categories or [
            "decision", "preference", "project", "goal",
            "context", "knowledge", "behavior"
        ]

        prompt = f"""从以下对话中提取值得记忆的信息。

类别说明:
- decision: 重要决策和选择
- preference: 用户偏好和习惯
- project: 项目进展和事件
- goal: 目标设定
- context: 环境背景
- knowledge: 学到的知识
- behavior: 行为模式

要求:
- 只提取确实重要的信息
- 每个记忆用简洁的一句话描述
- 给出置信度(0.5-1.0)
- 最多提取10条

JSON格式:
{{"memories": [
  {{"content": "记忆内容", "category": "类别", "confidence": 0.8}},
  ...
]}}

对话:
{self._format_messages(messages[-15:])}

记忆:"""

        system = "你是记忆提取专家。严格判断，只提取真正值得长期记忆的信息。"

        result = self.llm.complete(prompt, system=system, max_tokens=1200)

        try:
            json_str = self._extract_json(result)
            data = json.loads(json_str)
            return data.get("memories", [])
        except json.JSONDecodeError:
            return []

    def _format_messages(self, messages: List[Dict]) -> str:
        lines = []
        for m in messages:
            role = {"assistant": "A", "user": "U"}.get(m["role"], "?")
            content = m.get("content", "")[:300]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _extract_json(self, text: str) -> str:
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text


# ─────────────────────────────────────────────────────────────────────────────
# 全局实例
# ─────────────────────────────────────────────────────────────────────────────

_llm_manager = None
_summarizer = None
_decomposer = None
_memory_summarizer = None


def get_llm(provider: str = None) -> LLMManager:
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager(provider)
    return _llm_manager


def get_summarizer(provider: str = None) -> LLMSummarizer:
    global _summarizer
    if _summarizer is None:
        _summarizer = LLMSummarizer(provider)
    return _summarizer


def get_decomposer(provider: str = None) -> LLMDecomposer:
    global _decomposer
    if _decomposer is None:
        _decomposer = LLMDecomposer(provider)
    return _decomposer


def get_memory_summarizer(provider: str = None) -> MemorySummarizer:
    global _memory_summarizer
    if _memory_summarizer is None:
        _memory_summarizer = MemorySummarizer(provider)
    return _memory_summarizer


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== LLM Core 验证 ===")
    print()

    # 检查Provider
    llm = get_llm()
    print(f"Provider: {llm.provider_name}")
    print(f"Model: {llm.model}")
    print(f"Available: {llm.available()}")
    print()

    # 测试LLM对话
    print("[Test] LLM chat...")
    if llm.available():
        r = llm.complete("用一句话解释量子计算", max_tokens=100)
        print(f"Response: {r[:200]}")
    else:
        print("LLM not available (no API key)")

    # 测试Provider列表
    print()
    print("[Test] Provider list:")
    for name in ["openai", "minimax", "anthropic", "local"]:
        cfg = LLM_CONFIG.get(name, {})
        has_key = bool(cfg.get("api_key"))
        print(f"  {name}: {'OK' if has_key else 'no key'}")
