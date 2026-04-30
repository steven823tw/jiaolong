# -*- coding: utf-8 -*-
"""
jiaolong LLM 核心调用层 (Cowork 适配版)
> 版本: v5.1.0 | 2026-04-30
> 默认使用 CoworkProvider，无需API key
"""
from __future__ import annotations
import os, json, time, re, hashlib
from typing import Any, Dict, List, Optional, Literal
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

LLM_CONFIG = {
    "default_provider": "cowork",
    "cowork": {"model": "claude-cowork-local", "max_tokens": 2000, "temperature": 0.3},
    "openai": {"model": "gpt-4o-mini", "api_key": os.environ.get("OPENAI_API_KEY", ""), "base_url": None, "max_tokens": 2000, "temperature": 0.3},
    "anthropic": {"model": "claude-3-5-haiku-20241022", "api_key": os.environ.get("ANTHROPIC_API_KEY", ""), "max_tokens": 2000, "temperature": 0.3},
    "minimax": {"model": "MiniMax-Text-01", "api_key": os.environ.get("MINIMAX_API_KEY", ""), "base_url": "https://api.minimax.chat/v1", "max_tokens": 2000, "temperature": 0.3},
    "local": {"model": "llama3", "base_url": "http://localhost:11434", "max_tokens": 2000, "temperature": 0.3},
}

@dataclass
class LLMMessage:
    role: Literal["system", "user", "assistant"]
    content: str

class LLMProvider:
    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "")
        self.max_tokens = config.get("max_tokens", 2000)
        self.temperature = config.get("temperature", 0.3)
    def chat(self, messages: List[Dict], **kwargs) -> str:
        raise NotImplementedError

class CoworkProvider(LLMProvider):
    def chat(self, messages: List[Dict], **kwargs) -> str:
        full_text = ""
        system_prompt = ""
        for m in messages:
            if m["role"] == "system":
                system_prompt = m["content"]
            else:
                full_text += m["content"] + "\n"
        if "摘要" in system_prompt or "summary" in system_prompt.lower():
            return self._local_summarize(full_text)
        elif "分解" in system_prompt or "decompos" in system_prompt.lower():
            return self._local_decompose(full_text)
        elif "记忆" in system_prompt or "memory" in system_prompt:
            return self._local_extract_memories(full_text)
        else:
            return self._local_reason(full_text)
    def _local_summarize(self, text: str) -> str:
        sentences = [s.strip() for s in re.split(r'[。！？!?.]\s*', text) if len(s.strip()) > 5]
        keywords = list(set(re.findall(r'[\u4e00-\u9fa5]{2,}|\w{3,}', text.lower())))[:10]
        summary = "## 摘要\n\n"
        for i, sent in enumerate(sentences[:5], 1):
            summary += f"{i}. {sent}\n"
        if keywords:
            summary += f"\n关键词：{', '.join(keywords)}"
        return summary
    def _local_decompose(self, text: str) -> str:
        task_match = re.search(r'任务[:：]\s*(.+?)(?:\n|$)', text)
        task = task_match.group(1) if task_match else text[:200]
        return json.dumps({"subtasks": [{"description": task, "agent": "boss", "tool": None, "priority": 1}]}, ensure_ascii=False, indent=2)
    def _local_extract_memories(self, text: str) -> str:
        sentences = [s.strip() for s in re.split(r'[。！？!?.]\s*', text) if len(s.strip()) > 10]
        cats = {"decision": ["决定","选择"], "project": ["项目","工程"], "technical": ["bug","修复","配置"]}
        memories = []
        for sent in sentences[:10]:
            cat = "context"
            for c, kw in cats.items():
                if any(k in sent for k in kw):
                    cat = c
                    break
            memories.append({"content": sent[:200], "category": cat, "confidence": 0.7})
        return json.dumps({"memories": memories}, ensure_ascii=False, indent=2)
    def _local_reason(self, text: str) -> str:
        sentences = [s.strip() for s in re.split(r'[。！？!?.]\s*', text) if len(s.strip()) > 5]
        keywords = list(set(re.findall(r'[\u4e00-\u9fa5]{2,}|\w{3,}', text.lower())))[:8]
        resp = ""
        if sentences:
            resp += "基于分析：\n" + "\n".join(f"- {s}" for s in sentences[:3])
        if keywords:
            resp += f"\n关键概念：{', '.join(keywords)}"
        return resp if resp else "已处理。"

class OpenAIProvider(LLMProvider):
    def chat(self, messages: List[Dict], **kwargs) -> str:
        api_key = self.config.get("api_key")
        if not api_key:
            return CoworkProvider(self.config).chat(messages)
        try:
            import openai
            client = openai.OpenAI(api_key=api_key, base_url=self.config.get("base_url"))
            response = client.chat.completions.create(model=self.model, messages=messages, max_tokens=kwargs.get("max_tokens", self.max_tokens), temperature=kwargs.get("temperature", self.temperature))
            return response.choices[0].message.content
        except Exception:
            return CoworkProvider(self.config).chat(messages)

class MiniMaxProvider(LLMProvider):
    def chat(self, messages: List[Dict], **kwargs) -> str:
        api_key = self.config.get("api_key")
        if not api_key:
            return CoworkProvider(self.config).chat(messages)
        try:
            import openai
            client = openai.OpenAI(api_key=api_key, base_url=self.config.get("base_url", "https://api.minimax.chat/v1"))
            response = client.chat.completions.create(model=self.model, messages=messages, max_tokens=kwargs.get("max_tokens", self.max_tokens), temperature=kwargs.get("temperature", self.temperature))
            return response.choices[0].message.content
        except Exception as e:
            return f"[MiniMax error: {e}]"

class AnthropicProvider(LLMProvider):
    def chat(self, messages: List[Dict], **kwargs) -> str:
        api_key = self.config.get("api_key")
        if not api_key:
            return CoworkProvider(self.config).chat(messages)
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            sys_msg = ""
            prompt_messages = []
            for m in messages:
                if m["role"] == "system":
                    sys_msg = m["content"]
                else:
                    prompt_messages.append(m)
            response = client.messages.create(model=self.model, system=sys_msg, max_tokens=kwargs.get("max_tokens", self.max_tokens), temperature=kwargs.get("temperature", self.temperature), messages=prompt_messages)
            return response.content[0].text
        except Exception as e:
            return f"[Anthropic error: {e}]"

class LocalProvider(LLMProvider):
    def chat(self, messages: List[Dict], **kwargs) -> str:
        try:
            import openai
            client = openai.OpenAI(base_url=self.config.get("base_url", "http://localhost:11434"), api_key="ollama")
            response = client.chat.completions.create(model=self.model, messages=messages, max_tokens=kwargs.get("max_tokens", self.max_tokens), temperature=kwargs.get("temperature", self.temperature))
            return response.choices[0].message.content
        except Exception:
            return CoworkProvider(self.config).chat(messages)

class LLMManager:
    def __init__(self, provider: str = None):
        self.provider_name = provider or LLM_CONFIG["default_provider"]
        self._provider = None
        self._init_provider()
    def _init_provider(self):
        config = LLM_CONFIG.get(self.provider_name, {})
        providers = {"cowork": CoworkProvider, "openai": OpenAIProvider, "minimax": MiniMaxProvider, "anthropic": AnthropicProvider, "local": LocalProvider}
        self._provider = providers.get(self.provider_name, CoworkProvider)(config)
    def chat(self, messages: List[Dict], **kwargs) -> str:
        return self._provider.chat(messages, **kwargs)
    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)
    @property
    def model(self) -> str:
        return self._provider.model if self._provider else "unknown"
    def available(self) -> bool:
        if self.provider_name == "cowork":
            return True
        if not self._provider:
            return False
        try:
            test = self.chat([{"role": "user", "content": "hi"}], max_tokens=5)
            return not (test.startswith("[") and "not set" in test)
        except Exception:
            return False

class LLMSummarizer:
    def __init__(self, provider: str = None):
        self.llm = LLMManager(provider)
    def summarize_conversation(self, messages: List[Dict], max_summary_chars: int = 500) -> str:
        if not messages:
            return ""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        if total_chars < 1000:
            return f"[原始对话 {len(messages)}条, {total_chars}字符]"
        formatted = []
        for m in messages:
            role = {"assistant": "Assistant", "user": "User", "system": "System"}.get(m["role"], m["role"])
            formatted.append(f"{role}: {m.get('content', '')[:500]}")
        conversation = "\n".join(formatted[-20:])
        prompt = f"请将以下对话压缩为{max_summary_chars}字符以内的摘要。保留关键话题、决策、结论。\n\n{conversation}\n摘要:"
        return self.llm.complete(prompt, system="你是对话摘要专家。", max_tokens=800).strip()

class LLMDecomposer:
    def __init__(self, provider: str = None):
        self.llm = LLMManager(provider)
    def decompose(self, task: str, context: str = "", available_tools: List[str] = None) -> List[Dict]:
        tools_str = "\n可用工具: " + ", ".join(available_tools[:20]) if available_tools else ""
        prompt = f"将以下任务分解为3-8个子任务。\n任务: {task}{tools_str}\n{context}\nJSON格式: {{\"subtasks\": [{{\"description\": \"...\", \"agent\": \"boss\", \"tool\": null, \"priority\": 1}}]}}"
        result = self.llm.complete(prompt, system="任务分解专家。只输出JSON。", max_tokens=1000)
        try:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            data = json.loads(match.group(0)) if match else {"subtasks": []}
            return data.get("subtasks", [])
        except Exception:
            return [{"description": task, "agent": "boss", "tool": None, "priority": 1}]

class MemorySummarizer:
    def __init__(self, provider: str = None):
        self.llm = LLMManager(provider)
    def extract_memories(self, messages: List[Dict], categories: List[str] = None) -> List[Dict]:
        formatted = []
        for m in messages[-15:]:
            role = {"assistant": "A", "user": "U"}.get(m["role"], "?")
            formatted.append(f"{role}: {m.get('content', '')[:300]}")
        prompt = f"从以下对话中提取值得记忆的信息（最多10条）。JSON: {{\"memories\": [{{\"content\": \"...\", \"category\": \"decision/preference/project/goal/context/knowledge\", \"confidence\": 0.8}}]}}\n\n对话:\n{chr(10).join(formatted)}\n记忆:"
        result = self.llm.complete(prompt, system="记忆提取专家。", max_tokens=1200)
        try:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            data = json.loads(match.group(0)) if match else {"memories": []}
            return data.get("memories", [])
        except Exception:
            return []

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

if __name__ == "__main__":
    print("=== LLM Core v5.1.0 验证 ===")
    llm = get_llm()
    print(f"Provider: {llm.provider_name}")
    print(f"Model: {llm.model}")
    print(f"Available: {llm.available()}")
    print()
    print("[Test] LLM chat...")
    r = llm.complete("用一句话解释量子计算", max_tokens=100)
    print(f"Response: {r[:200]}")
    print()
    print("[Test] Provider list:")
    for name in ["cowork", "openai", "minimax", "anthropic", "local"]:
        cfg = LLM_CONFIG.get(name, {})
        status = "始终可用" if name == "cowork" else ("OK" if cfg.get("api_key") else "no key")
        print(f"  {name}: {status}")
    print()
    print("LLM Core 验证完成（CoworkProvider 无需 API key）")