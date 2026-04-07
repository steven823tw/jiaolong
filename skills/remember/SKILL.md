# SKILL: remember
> 版本: v1.0 | 2026-04-02
> 描述: 检查相关记忆并提供上下文

## 触发关键词
- `/remember`
- `remember`

## 参数说明
- `query`: 查询关键词 (类型: str)

## 执行步骤
1. 1. 搜索memory_hot.json
2. 2. 检查OMLX温冷层
3. 3. 汇总相关事实
4. 4. 提供上下文

## 示例
- `/remember jiaolong` → 返回jiaolong集团相关记忆

## 实现
> 由 SkillBuilder v2 自动生成
