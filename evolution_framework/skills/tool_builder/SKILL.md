# SKILL: tool_builder
> 工具系统深度化（灵感来源: Claude Code Tool.ts + tools/）
> 版本: v1.0 | 2026-04-02

## 触发条件

- `/tool_builder <tool_name>` - 构建指定工具
- 自动发现缺失工具时触发

## 功能

参照 Claude Code 的工具系统设计，为小笨构建完整的工具模块。

## Claude Code 工具系统设计原则

每个工具包含三要素：

```typescript
interface Tool {
  name:           string       // 工具名称
  description:    string       // 功能描述
  input_schema:   ZodSchema   // 输入参数Schema（Zod验证）
  permission:     PermissionModel // 权限模型
  progress_state?: ProgressState // 进度状态（可选）
  execute:        (input) => Promise<Output> // 执行逻辑
}
```

## 工具优先级（P0 → P3）

### P0: 最高优先
| 工具 | 用途 | 难度 |
|------|------|------|
| TaskCreateTool | 创建任务/工单 | 低 |
| TaskUpdateTool | 更新任务状态 | 低 |
| WebSearchTool | 增强搜索（当前已有，需深化） | 低 |

### P1: 高优先
| 工具 | 用途 | 难度 |
|------|------|------|
| MCPTool | MCP协议集成 | 中 |
| NotebookEditTool | Jupyter编辑 | 中 |
| SkillTool | Skill执行 | 低 |

### P2: 中优先
| 工具 | 用途 | 难度 |
|------|------|------|
| AgentTool | 子Agent生成 | 高 |
| TeamCreateTool | 多Agent团队管理 | 高 |
| LSPTool | Language Server Protocol | 高 |

### P3: 长期
| 工具 | 用途 | 难度 |
|------|------|------|
| WorktreeTool | Git Worktree隔离 | 高 |
| CronCreateTool | 定时触发器 | 中 |
| SyntheticOutput | 结构化输出 | 中 |

## 工作流程

### Step 1: 读取 Tool.ts 参考
分析 Claude Code 的 Tool.ts 基类设计

### Step 2: 创建工具骨架
```
tools/<tool_name>/
├── index.ts       # 工具主文件（TypeScript风格，Python实现）
├── schema.py      # 输入Schema验证
├── permission.py # 权限模型
└── test.py       # 单元测试
```

### Step 3: 实现核心逻辑
- 输入验证（Schema）
- 权限检查
- 执行逻辑
- 进度报告

### Step 4: 注册到 tools registry
添加到 `prepare.py` 的 TOOL_REGISTRY

### Step 5: 编写测试
- 正常路径测试
- 异常路径测试
- 权限边界测试

## 输出格式

```
[tool_builder] TaskCreateTool
- 状态: ✅ 已实现
- 位置: tools/task_create/
- Schema: {task_name, description, priority}
- 权限: auto (自动放行)
- 测试: 5 passed
```

## 与 evolution.py 的关系

tool_builder 是 `evolution.py` 提升 tool_coverage 指标的核心手段。
