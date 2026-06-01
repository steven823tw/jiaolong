# jiaolong AI 助手框架
> **版本**: v6.1.0 | **日期**: 2026-06-01
> Claude Code 的能力放大器 — 记忆召回 + Skills 触发 + 并行执行 + 代码规则

## 核心能力

| 能力 | 说明 |
|------|------|
| 🧠 **语义记忆召回** | 从原生 `.md` 记忆系统自动注入相关历史 |
| ⚡ **Skills 自动触发** | 关键词识别 → 自动执行 16 个 Skills |
| 🔄 **并行任务执行** | ThreadPoolExecutor + 依赖链 |
| 📋 **代码规则引擎** | 8 条 clean-code 规则自动检查 |
| 🔍 **博弈审查** | 对抗性代码审查方法论 |

## 架构

```
Claude Code
    ├── Native Memory (~/.claude/projects/C--cc/memory/*.md)
    ├── Hooks (extract-hook + recall-hook)
    ├── Skills Layer (16 个)
    │     ├── recall / remember / evolve / research
    │     ├── monitor / simplify / dream / status_report
    │     ├── code_review_debate / extract_memories
    │     └── team_analyze / tool_builder / experiment_logger
    └── Core Modules
          ├── memory_recall.py    → 原生 .md 记忆召回
          ├── skill_trigger.py    → 关键词触发引擎
          ├── parallel_executor.py → 并行执行 + 依赖链
          ├── rules_engine.py     → Python 代码规则检查
          └── cowork_integration.py → 集成 Facade
```

## 快速使用

```
/recall jiaolong          → 召回相关记忆
/remember                 → 检查记忆状态
/monitor                  → 系统状态检查
/review report.html       → 博弈式代码审查
"开始进化"                 → 触发进化实验
```

## 记忆系统 (v6.0+)

记忆存储在 Claude Code 原生 `.md` 格式：
```
~/.claude/projects/C--cc/memory/
├── MEMORY.md              # 索引
└── *.md                   # 单条记忆 (frontmatter + 正文)
    ├── name: 记忆名称
    ├── type: user|feedback|project|reference
    └── description: 描述
```

## 依赖

- Python 3.12+
- Claude Code (原生记忆 + Hooks)
- （可选）OpenAI / Anthropic API Key

## 来源

- **版本**: v6.1.0
- **测试**: 97 tests passing
- **实验**: 12 个 (全部 RETAINED)
- **定位**: Claude Code 的能力放大器，不是替代品
