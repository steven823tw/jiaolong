# SKILL: experiment_logger
> 实验日志管理与知识沉淀
> 版本: v1.0 | 2026-04-02

## 触发条件

- `/log_experiment` - 记录当前实验
- `/log_experiment show` - 显示最近实验
- `/log_experiment summary` - 生成汇总报告
- `/log_experiment export` - 导出实验知识库

## 功能

管理jiaolong自进化框架的所有实验日志，实现**失败经验的复用**。

## 核心价值

AutoResearch 的核心洞察之一：**失败的实验同样有价值**

```
成功的实验 → 保留，能力提升
失败的实验 → 记录原因 → 避免重复踩坑
```

## 实验知识库结构

```
experiments/
├── experiment_log.md     # 主日志（追加型）
├── knowledge_base.md     # 知识沉淀（分类整理）
└── EXP-YYYYMMDD-NNN/   # 单个实验
    ├── proposal.md       # 原始假设
    ├── changes.md        # 具体改动
    ├── test_result.md    # 测试结果
    ├── evaluation.md     # 指标评估
    └── verdict.md        # 结论

knowledge_base/
├── what_works.md        # 有效的做法
├── what_fails.md        # 失败的教训
├── metric_insights.md    # 指标洞察
└── tool_patterns.md     # 工具设计模式
```

## 知识沉淀规则

### KEPT 实验 → 提炼有效做法
```markdown
## 有效的做法
### 记忆提取
- 当会话中出现明确决策时，提取为 project 类型记忆
- 7天内访问2次以上的条目值得保留热层
```

### DISCARDED 实验 → 提炼失败教训
```markdown
## 失败的教训
### 记忆提取
- ❌ 不要在短对话（<3轮）中提取记忆（噪音太多）
- ❌ 不要依赖模糊的"可能有用"判断（命中率反而下降）
```

## 知识库更新频率

| 触发 | 更新内容 |
|------|---------|
| 每次实验后 | 追加到 experiment_log.md |
| 每周日 | 提炼到 knowledge_base/*.md |
| 每月末 | 生成月度进化报告 |

## 使用示例

```
用户: /log_experiment show

jiaolong实验日志 (最近10条)

| ID | 时间 | 假设 | 结果 | 原因 |
|----|------|------|------|------|
| EXP-20260402-001 | 04-02 08:30 | auto extract记忆 | ✅ KEPT | +26.7% |
| EXP-20260402-002 | 04-02 08:35 | 增加TaskTool | ❌ DISCARDED | 无显著提升 |
| EXP-20260402-003 | 04-02 08:40 | 优化协作流程 | ✅ KEPT | 均衡度+15% |

---

用户: /log_experiment summary

jiaolong自进化月度报告 (2026-04)

总实验: 23
保留率: 65% (15/23)
丢弃率: 30% (7/23)
失败率:  5% (1/23)

主要改进:
- memory_hit_rate: 0.30 → 0.65 (+117%)
- skill_count: 3 → 8 (+167%)

主要教训:
- 不要在短对话中提取记忆
- 工具优先级比数量更重要
```

## 与 evolve skill 的关系

experiment_logger 是进化过程的**记录层**，
evolve skill 是进化过程的**执行层**，
两者共同构成完整的 AutoResearch Loop。

## 导出格式

支持导出为：
- Markdown（知识库）
- JSON（供程序读取）
- CSV（供数据分析）
