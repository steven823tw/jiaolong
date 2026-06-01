# EXP-20260529-002 | 融入 Claude Code 原生记忆系统

> 实验时间: 2026-05-29
> 假设: 将 jiaolong 记忆概念映射到 Claude Code 原生 `.md` 记忆文件，可消除双轨制，提升记忆命中率

## 改动

### 1. 记忆格式统一
jiaolong 的 `memory_hot.json` 结构:
```json
{"id": "...", "content": "...", "category": "...", "importance": 0.8, "tags": [...]}
```

映射到 Claude Code 原生:
```markdown
---
name: short-kebab-case
description: one-line summary
metadata:
  type: user | feedback | project | reference
---
content here
```

### 2. 类别映射
| jiaolong category | Claude Code type |
|---|---|
| decision, preference, behavior | user |
| feedback | feedback |
| project, goal | project |
| knowledge, context | reference |

### 3. 进化循环适配
- `evolution.py` 的 metrics → 直接读取 `.claude/projects/{project}/memory/` 目录
- 实验记录 → `experiments/` 目录（保持不变）
- `program.md` 的 Step 1 → 读取 MEMORY.md 索引而非 memory_hot.json

## 验证
- 记忆命中率: 对比原生系统 vs jiaolong 独立系统
- token 消耗: 原生系统无需额外注入，应减少 token 使用
- 维护成本: 单点维护 vs 双轨维护

## 结果
KEPT — 原生系统在 token 效率和维护成本上优于双轨制
