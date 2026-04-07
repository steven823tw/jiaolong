# SKILL: quant_screen
> 版本: v1.0 | 2026-04-02
> 描述: 按量化因子筛选股票

## 触发关键词
- `/quant_screen`
- `quant_screen`

## 参数说明
- `turnover_rate`: 换手率下限(%) (类型: float)
- `top_n`: 返回数量 (类型: int)

## 执行步骤
1. 1. 连接XTick数据源
2. 2. 应用量化因子筛选
3. 3. 排序+返回TopN
4. 4. 记录到记忆

## 示例
- `/quant_screen turnover_rate=5 top_n=10` → 换手率>5%的Top10股票

## 实现
> 由 SkillBuilder v2 自动生成
