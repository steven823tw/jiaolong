# jiaolong AI 助手框架 — 安装与使用指南

> 版本 v4.1.0 | 2026-04-02

---

## 安装

### 前置要求

- Python 3.8+
- OpenClaw 已安装并运行

### 步骤 1：复制框架文件

将 `evolution_framework/` 整个目录复制到你的 OpenClaw workspace：

```
your-workspace/
└── evolution_framework/
    ├── openclaw_integration.py  (核心集成)
    ├── skill_trigger.py         (Skills自动触发)
    ├── memory_recall.py         (记忆召回)
    ├── parallel_executor.py      (并行执行)
    ├── rules_engine.py          (代码规则)
    ├── jarvis_cli.py           (命令行)
    ├── jarvis_daemon.py        (守护服务)
    ├── skill_output.py         (输出格式化)
    ├── llm_core.py             (LLM管理)
    ├── context_compressor.py   (对话压缩)
    ├── task_decomposer.py      (任务分解)
    ├── memory_evolution.py     (记忆演进)
    ├── coordinator/            (协调器)
    ├── services/              (compact + daemon)
    └── skills/                 (13个Skills)
```

### 步骤 2：启用 OpenClaw Hooks

在 `openclaw.json` 中添加：

```json
{
  "hooks": {
    "internal": {
      "enabled": true,
      "load": {
        "workspaceDir": "path/to/your/workspace/hooks"
      }
    }
  }
}
```

将 `hooks/` 目录（包含 `jiaolong-memory/` 和 `jiaolong-skill-trigger/`）复制到 workspace。

### 步骤 3：验证安装

```bash
cd your-workspace
python evolution_framework/jarvis_cli.py status
```

应该看到：
```
jiaolong框架状态: 运行中
Skills数量: 14
记忆召回: 启用
```

---

## 使用

### 命令行

```bash
# 查看状态
python evolution_framework/jarvis_cli.py status

# 记忆召回
python evolution_framework/jarvis_cli.py recall jiaolong
python evolution_framework/jarvis_cli.py recall 量化

# 查看Skills
python evolution_framework/jarvis_cli.py skills

# 查看Agent角色
python evolution_framework/jarvis_cli.py agents

# 代码规则检查
python evolution_framework/jarvis_cli.py check your_file.py
```

### 在对话中使用

```
/recall jiaolong              → 召回jiaolong相关记忆
/recent 5               → 最近5条记忆
/recall category=project → 按类别筛选

/jiaolong status            → 框架状态
/jiaolong info             → 详细信息
/jiaolong modules           → 核心模块
/jiaolong skills            → Skills列表
```

### Skills 自动触发

在对话中直接说：

| 说 | 触发 |
|---|------|
| "帮我选股" | quant_screen |
| "开始进化" | evolve |
| "/monitor" | monitor |
| "记得jiaolong是什么" | recall |

---

## 配置

### 可选：API Keys（用于 LLM 能力）

```bash
# Linux/Mac
export OPENAI_API_KEY=sk-xxx
export ANTHROPIC_API_KEY=sk-ant-xxx

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-xxx"
$env:ANTHROPIC_API_KEY="sk-ant-xxx"
```

### Daemon 守护

```bash
# 安装开机自启（Windows Task Scheduler）
python evolution_framework/jarvis_daemon.py install

# 查看状态
python evolution_framework/jarvis_daemon.py status

# 前台运行
python evolution_framework/jarvis_daemon.py run

# 卸载
python evolution_framework/jarvis_daemon.py uninstall
```

---

## 架构

```
OpenClaw
  ├── Hooks
  │     ├── jiaolong-memory         → 记忆召回注入
  │     └── jiaolong-skill-trigger   → Skills自动触发
  │
  ├── Core Modules (Python)
  │     ├── openclaw_integration     → 统一入口
  │     ├── memory_recall           → 语义召回
  │     ├── skill_trigger           → 触发引擎
  │     ├── parallel_executor        → 并行执行
  │     ├── rules_engine             → clean-code规则
  │     └── llm_core                 → LLM能力
  │
  └── Services
        ├── compact.py              → Context压缩
        └── daemon.py               → 定时守护
```

---

## 故障排除

| 问题 | 解决 |
|------|------|
| `Module not found` | 确保 `evolution_framework/` 在 workspace 根目录 |
| Hook 不生效 | 检查 `openclaw.json` 中 `hooks.internal.enabled: true` |
| 记忆召回返回空 | 检查 `memory/memory_hot.json` 是否存在 |
| Daemon 无法启动 | 用 `python jarvis_daemon.py test` 测试 |

---

## 发布信息

- **版本**: v4.1.0
- **日期**: 2026-04-02
- **测试**: 97/97 项全部通过
- **许可证**: MIT

---

## 获取更新

```bash
# 如果通过 git 管理
git pull

# 重新运行验证
python evolution_framework/jarvis_cli.py status
```
