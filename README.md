# 🐉 蛟龙 (Jiaolong) — OpenClaw 智能进化框架

> v0.4.5 | 适配 OpenClaw 2026.4.5 | Plugin SDK 兼容

## 概述

蛟龙是 OpenClaw 的智能进化框架，赋予 AI 助手**记忆、自动化和自我进化**能力。

## 核心模块

| 模块 | 功能 |
|------|------|
| **Skill 触发引擎** | 自动检测消息中的 Skill 触发词 |
| **记忆注入系统** | 每次对话前注入相关记忆上下文 |
| **进化框架** | Agent 自主学习和能力进化 |
| **三脑协调器** | 大脑(主控) + 小脑1(执行) + 小脑2(情报) 任务协调 |
| **规则引擎** | 自动化规则执行与决策 |
| **记忆进化** | 长期记忆的自主优化与沉淀 |

## 架构

```
jiaolong/
├── hooks/                      # OpenClaw Hooks
│   ├── jiaolong-skill-trigger/ # Skill 触发 hook
│   └── jiaolong-memory/        # 记忆注入 hook
├── coordinator/                # 三脑协调器
│   ├── decomposer.py           # 任务拆解
│   ├── role_matcher.py         # 角色匹配
│   ├── state_sync.py           # 状态同步
│   └── messaging.py            # 消息路由
├── services/                   # 核心服务
├── experiments/                # 实验性功能
├── skill_trigger.py            # Skill 触发引擎
├── memory_evolution.py         # 记忆进化模块
├── evolution.py                # 主进化循环
├── memory_recall.py            # 记忆召回
├── llm_core.py                 # LLM 核心接口
├── rules_engine.py             # 规则引擎
├── context_compressor.py       # 上下文压缩
├── openclaw_integration.py     # OpenClaw 集成层
├── jarvis_cli.py               # Jarvis CLI
└── jarvis_daemon.py            # Jarvis 后台进程
```

## 版本历史

- **v0.4.5** — 适配 OpenClaw 4.5，Plugin SDK 迁移，13个版本跨度升级
- **v0.3.23** — 初始版本（OpenClaw 3.23-2）

## 安装

```bash
git clone https://github.com/steven823tw/jiaolong.git
cd jiaolong
cp -r hooks/* ~/.openclaw/workspace/hooks/
cp -r * ~/.openclaw/workspace/evolution_framework/
```

## License

Private — 仅供内部使用
