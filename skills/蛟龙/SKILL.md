# jiaolong AI 助手框架
> **版本**: v4.1.0 | **日期**: 2026-04-02
> 一套让 AI 助手拥有记忆、自动化和自我进化能力的增强框架

---

## jiaolong是什么？

jiaolong是运行在 OpenClaw 之上的** AI 增强框架**，为 OpenClaw 添加了：

| 能力 | 说明 |
|------|------|
| 🧠 **语义记忆召回** | 每次对话自动注入相关历史记忆 |
| ⚡ **Skills自动触发** | 关键词自动识别并执行对应技能 |
| 🔄 **并行任务执行** | 多任务同时执行，效率提升60%+ |
| 📋 **代码规则引擎** | 集成 clean-code 标准的自动检查 |
| 🤖 **LLM能力层** | 对话压缩 / 任务分解 / 记忆提取 |
| 🔄 **智能记忆演进** | 三层存储自动升降级 |
| ⏰ **Daemon守护服务** | 定时任务 + 进程管理 |

---

## 安装

### 前置要求

- Python 3.8+
- OpenClaw 已安装并运行
- （可选）OpenAI / Anthropic / MiniMax API Key（用于LLM功能）

### 步骤

```bash
# 1. 克隆或复制整个 evolution_framework 目录到你的 OpenClaw workspace
# 确保目录结构如下：
# workspace/
# └── evolution_framework/
#     ├── openclaw_integration.py
#     ├── skill_trigger.py
#     ├── memory_recall.py
#     ├── parallel_executor.py
#     ├── rules_engine.py
#     ├── jarvis_cli.py
#     ├── jarvis_daemon.py
#     ├── skill_output.py
#     ├── llm_core.py
#     ├── context_compressor.py
#     ├── task_decomposer.py
#     ├── memory_evolution.py
#     ├── coordinator/
#     ├── services/
#     └── skills/

# 2. 启用 OpenClaw Hooks（在 openclaw.json 中配置）
# 找到 hooks.internal.load.workspaceDir 指向 hooks/ 目录

# 3. 验证安装
python evolution_framework/jarvis_cli.py status
```

---

## 快速开始

### 1. 记忆召回
```
/recall jiaolong              → 召回jiaolong相关记忆
/recent 5                 → 最近5条记忆
/recall category=project  → 按类别筛选
```

### 2. Skills自动触发
```
"帮我选股"   → 自动触发 quant_screen
"开始进化"   → 自动触发 evolve
"/monitor"  → 自动触发 monitor
```

### 3. 并行执行
```python
from evolution_framework import jiaolong

jiaolong.parallel_submit("搜集数据", "parallel_search",
                         {"query": "jiaolong"}, agent="intel")
jiaolong.parallel_run_all()  # 3任务并行执行
```

### 4. 代码规则检查
```python
from evolution_framework import jiaolong

# 手动检查
result = jiaolong.check_content_rules(code, "my_file.py")
# 返回违规列表和修复建议
```

### 5. Daemon守护
```bash
python evolution_framework/jarvis_daemon.py status   # 查看状态
python evolution_framework/jarvis_daemon.py install   # 安装开机自启
python evolution_framework/jarvis_daemon.py run       # 前台运行
```

---

## 核心模块

| 模块 | 版本 | 说明 |
|------|------|------|
| `openclaw_integration.py` | v1.1 | 集成核心，统一接口 |
| `skill_trigger.py` | v1.0 | Skills自动触发引擎 |
| `memory_recall.py` | v1.0 | 语义记忆召回 |
| `parallel_executor.py` | v2.0 | 任务依赖链并行 |
| `rules_engine.py` | v2.0 | clean-code规则检查 |
| `jarvis_cli.py` | v1.0 | 命令行工具 |
| `jarvis_daemon.py` | v1.0 | 定时守护服务 |
| `skill_output.py` | v1.0 | 统一输出格式化 |
| `llm_core.py` | v1.0 | 多Provider LLM管理 |
| `context_compressor.py` | v1.0 | LLM对话压缩 |
| `task_decomposer.py` | v1.0 | LLM任务分解 |
| `memory_evolution.py` | v1.0 | 三层记忆演进 |

---

## Skills 列表

| Skill | 触发词 | 功能 |
|-------|--------|------|
| `recall` | /recall, 查一下记忆 | 记忆召回 |
| `remember` | /remember | 记忆检查 |
| `monitor` | /monitor | 主动监控 |
| `evolve` | /evolve, 开始进化 | 自进化实验 |
| `research` | /research, 分析 | 深度研究 |
| `simplify` | /simplify, 简化 | 任务简化 |
| `quant_screen` | /quant_screen, 选股 | 量化选股 |
| `dream` | /dream, 整合记忆 | 记忆整理 |
| `status_report` | /status_report | 状态报告 |
| `team_analyze` | /team_analyze | 多Agent协作 |
| `extract_memories` | /extract_memories | 记忆提取 |
| `tool_builder` | /tool_builder | 工具构建 |
| `experiment_logger` | /log_experiment | 实验记录 |

---

## 配置

### 环境变量（可选）

```bash
# LLM API Keys（用于LLM能力层）
export OPENAI_API_KEY=sk-xxx
export ANTHROPIC_API_KEY=sk-ant-xxx
export MINIMAX_API_KEY=xxx

# Workspace路径（一般不需要改）
export JIAOLONG_WORKSPACE=C:\Users\steve\.openclaw\workspace
```

### 记忆文件

```
workspace/memory/
├── memory_hot.json      # 热层记忆（当前使用）
├── memory_warm/         # 温层归档
└── memory_cold/         # 冷层归档
```

---

## 架构

```
OpenClaw
    │
    ├──┬─ Hooks (message:preprocessed)
    │       ├── jiaolong-memory        → 记忆召回注入
    │       └── jiaolong-skill-trigger → Skills自动触发
    │
    ├──┬─ Skills Layer
    │       └── 14个Skills（recall/evolve/monitor/...）
    │
    ├──┬─ Core Modules
    │       ├── memory_recall.py       → 语义召回
    │       ├── skill_trigger.py       → 触发引擎
    │       ├── parallel_executor.py   → 并行执行
    │       ├── rules_engine.py        → 代码规则
    │       ├── llm_core.py            → LLM能力
    │       └── memory_evolution.py    → 记忆演进
    │
    └──┬─ Services
            ├── compact.py    → Context压缩
            └── daemon.py     → 后台守护
```

---

## 与 OpenClaw 原生的关系

jiaolong**不是**替代 OpenClaw，而是**放大** OpenClaw 的能力：

| 维度 | OpenClaw原生 | +jiaolong后 |
|------|------------|---------|
| 记忆 | Session级 | 长期+语义搜索 |
| Skills | 手动触发 | 关键词自动触发 |
| 任务执行 | 串行 | 多线程并行 |
| 代码质量 | 无 | clean-code标准自动检查 |
| 后台任务 | 无 | 定时调度+Daemon |

---

## 局限性

- `before_tool_call` Hook 需要 OpenClaw Plugin API
- 真实多Agent subagent 受 OpenClaw 平台限制
- LLM功能需要配置 API Key
- 部分 Skills 为 stub 状态（功能待完善）

---

## 许可证

MIT License - 开源共享

---

## 来源

jiaolong由 steve 创建，基于 Claude Code 差距分析持续进化。

- **项目**: jiaolong AI 助手框架
- **版本**: v4.1.0
- **日期**: 2026-04-02
- **定位**: OpenClaw 的能力放大器
