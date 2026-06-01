# 蛟龙复盘 — 2026-05-29

## 当前状态诊断

### 框架层面
| 维度 | 状态 | 问题 |
|------|------|------|
| 版本 | v4.1.0 (2026-04-02) | 近2个月未迭代 |
| Skills | 14个 (代码中) / 10个 (索引) | 索引不一致 |
| Hooks | 2个 (配置中) | 指向 `~/.claude/jiaolong/` 而非活跃 workspace |
| 记忆系统 | 框架存在 | `memory_hot.json` 不存在 |
| 实验 | 0个 | 进化循环从未运行 |
| Daemon | 未启动 | 无后台任务 |

### Claude Code 原生记忆（实际活跃）
| 维度 | 状态 |
|------|------|
| 记忆条目 | 8条 (MEMORY.md 索引) |
| 类型分布 | feedback:4, project:2, architecture:1 |
| 缺失 | user, reference 类型为 0 |
| 覆盖 | Inspection V2 项目完善, jiaolong 项目薄弱 |

### 核心断裂点

1. **记忆双轨制**: jiaolong 有自己的 `memory_hot.json` + `memory_evolution.py`，但 Claude Code 用的是 `~/.claude/projects/{project}/memory/*.md`。两者互不相通。

2. **Hook 指向错误**: `settings.json` 中的 hooks 配置指向 `~/.claude/jiaolong/hooks/`，但当前活跃项目是 `C:\cc\`。jiaolong 的自动记忆注入和 Skill 触发实际上没有生效。

3. **进化循环空转**: `program.md` 定义了完整的 AutoResearch 循环，`evolution.py` 有 metrics 框架，但从未执行过一次实验。`metrics_state.json` 的数据停留在 2026-04-02 的种子数据。

4. **Skills 悬空**: `skills_index.json` 列出 10 个 skills，但路径指向 `C:\Users\steve\.claude\jiaolong\`，而非当前 workspace 的 `jiaolong-cowork/evolution_framework/skills/`。

## 进化方案

### Phase 1: 接入原生记忆系统 (立即)
- 将 jiaolong 的记忆概念映射到 Claude Code 的 `.md` 记忆文件
- 用 `metadata.type` 区分记忆类型（user/feedback/project/reference）
- 放弃 `memory_hot.json` 路线，统一到原生系统

### Phase 2: 激活进化循环 (本次)
- 在当前 workspace 运行首次实验
- 验证记忆召回 → 实验 → 评估的闭环
- 记录到 `experiments/` 目录

### Phase 3: Hooks 重定向 (需用户确认)
- 将 hooks 配置指向当前 workspace
- 或将 jiaolong 框架复制到 `~/.claude/` 全局目录

---

**结论**: jiaolong 框架有完整的设计（记忆/进化/Skills/协调器），但与 Claude Code 的实际运行环境脱节。进化方向是**融入原生系统**而非**并行运行**。
