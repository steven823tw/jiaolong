# SKILL: extract_memories（v3 最终版）
> 自动记忆提取（灵感来源: Claude Code extractMemories/）
> 版本: v3.0 | 2026-04-02 | 基于AutoResearch实验验证

## 触发条件

**自动触发**: 每次会话结束时自动运行（可配置）
**手动触发**: `extract_memories` 或 `/extract_memories`

## 功能

从当前会话中自动提取值得记忆的事实，写入 `memory/memory_hot.json`。

### 核心技术

1. **触发检测（TriggerDetector）**: 5类关键词检测
   - decision（决策）
   - feedback（反馈）
   - project（项目）
   - context（上下文）
   - goal（目标）

2. **质量评分（QualityScorer）**: 5维评分
   - relevance（相关性 ×25%）
   - actionability（可操作性 ×25%）
   - timeliness（时效性 ×20%）
   - uniqueness（独特性 ×15%）
   - completeness（完整性 ×15%）

3. **三级判定**
   - PASS（≥0.70）：自动写入热记忆
   - DRAFT（0.50-0.70）：记录但不写入
   - REJECT（<0.50）：丢弃

4. **去重机制**：基于内容前30字符判断

## 使用方式

```bash
python extract_memories_omlx.py
```

```python
from extract_memories_omlx import run_extract

# Dry run（不写入）
report = run_extract(conversation_text, dry_run=True)

# 正式写入
report = run_extract(conversation_text, dry_run=False)
```

## 输出报告

```
[提取报告]
  触发: 6 次
  PASS: 3 | DRAFT: 4 | REJECT: 2
  跳过(重复): 5
  avg_quality: 0.83

[Top facts]
  [0.842] [context] [PASS] XTick数据格式说明
  [0.806] [goal] [PASS] jiaolong量化目标
```

## 与OMLX的关系

- 使用 `MemorySwapManager().hot` 读取当前热记忆（结构一致）
- 写入 `memory_hot.json`（与OMLX共享同一文件）
- 不依赖OMLX的 `add_fact`（直接读写文件）

## AutoResearch实验验证

| 实验 | 结果 | 说明 |
|------|-------|------|
| EXP-004 | KEPT | v1触发检测，9条提取 |
| EXP-005 | KEPT | v2质量评分，avg_q=0.725 |
| EXP-006 | KEPT | v3质量过滤，REJECT=3 |
| **EXP-007** | **KEPT** | **EM-4 OMLX集成 ✅ EM-5 Skill命令 ✅** |

## 局限与已知问题

1. **category_balance**: 当前16.7%（goal类过多，investment类过少）
2. **中文口语**: 短文本容易被判为DRAFT/REJECT
3. **路径类文本**: 含大量路径/代码的行容易被REJECT
4. **Trigger关键词**: 仍可能漏检（如纯表情/短回复）

## 改进方向

1. 引入LLM评估（替代规则匹配）
2. category均衡补充机制（自动补充弱类）
3. 路径/代码行特殊处理
4. 与jiaolong集团协作：让小呆做情报分析，小笨做决策
