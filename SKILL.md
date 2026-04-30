# jiaolong AI 助手框架 v4.1.0

> **让 AI 助手拥有记忆、自动化和自我进化能力**

---

## 安装（3步）

### 第1步：复制框架

将 `jiaolong/` 整个目录复制到你的 Claude Code Cowork workspace：

```
your-workspace/
└── jiaolong/
    ├── evolution_framework/   ← 14个核心模块
    ├── skills/               ← 14个Skills（含入口Skill）
    ├── memory/              ← 记忆存储
    ├── SKILL.md
    ├── BRIEFING.md
    └── README.md
```

### 第2步：安装 Hooks（可选但推荐）

```bash
# 复制 hooks 目录到 workspace
# 将jiaolong/evolution_framework/hooks/ 下的两个hook目录
# 复制到你的 Claude Code Cowork workspace hooks/ 目录

# 然后在 Claude Code hooks 中添加：
{
  "hooks": {
    "internal": {
      "enabled": true,
      "load": {
        "workspaceDir": "你的workspace路径/hooks"
      }
    }
  }
}
```

Hooks 内容：
- `jiaolong-memory/` — 每次消息自动注入相关记忆
- `jiaolong-skill-trigger/` — 自动检测Skill触发词

### 第3步：验证

```bash
cd jiaolong
python evolution_framework/jarvis_cli.py status
```

---

## 核心能力

| 能力 | 说明 |
|------|------|
| 🧠 语义记忆召回 | 每次对话自动注入相关历史 |
| ⚡ Skills 自动触发 | 关键词即触发 |
| 🔄 并行任务执行 | 多线程效率 +60% |
| 📋 clean-code 规则 | 8条规则自动检查 |
| 🤖 LLM 能力层 | 对话压缩/任务分解/记忆提取 |
| ⏰ Daemon 守护 | 定时调度+进程管理 |

---

## 使用

### 命令行
```bash
python evolution_framework/jarvis_cli.py status     # 状态
python evolution_framework/jarvis_cli.py skills    # Skills列表
python evolution_framework/jarvis_cli.py recall jiaolong  # 记忆召回
python evolution_framework/jarvis_cli.py check your_file.py  # 代码规则
```

### 对话中
```
/jiaolong status       → 框架状态
/jiaolong info        → 详细信息
/recent 5         → 最近5条记忆
"帮我选股"         → 自动触发 quant_screen
"开始进化"         → 自动触发 evolve
```

---

## 架构

```
jiaolong/
├── evolution_framework/
│   ├── cowork_integration  ← 集成核心
│   ├── skill_trigger         ← 自动触发引擎
│   ├── memory_recall         ← 语义召回
│   ├── parallel_executor     ← 并行执行
│   ├── rules_engine          ← clean-code规则
│   ├── jarvis_cli           ← 命令行
│   ├── jarvis_daemon        ← 守护服务
│   ├── llm_core            ← LLM管理
│   ├── context_compressor    ← 对话压缩
│   ├── task_decomposer       ← 任务分解
│   ├── memory_evolution      ← 记忆演进
│   ├── coordinator/           ← 协调器
│   ├── services/            ← compact + daemon
│   └── skills/              ← 13个Skills
│
├── skills/                   ← 入口Skill
│   ├── script.py
│   ├── SKILL.md
│   └── BRIEFING.md
│
└── memory/                   ← 记忆存储
    └── memory_hot.json
```

---

## 局限性

- Hooks 需要手动安装到 Claude Code Cowork workspace hooks 目录
- `before_tool_call` Hook 需要 Claude Code Cowork Plugin API
- LLM 功能需要配置 API Key（可选）

---

## 版本

- **版本**: v4.1.0
- **日期**: 2026-04-02
- **测试**: 97/97 项全部通过

---

## 许可证

MIT License
