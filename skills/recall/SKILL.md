# recall Skill - 记忆召回

> 版本: v2.0 | 2026-04-02
> 触发词: `/recall`, `查一下记忆`, `记得什么`

---

## 功能

从jiaolong记忆系统召回相关记忆上下文。

## 语法

```
/recall <关键词>                    基础召回
/recall <关键词> recent <N>        最近N条相关记忆
/recall <关键词> category=<类别>   按类别过滤
/recent <N>                        最近N条记忆（不限关键词）
/recall category=<类别>            指定类别所有记忆
```

## 类别关键词

| 关键词 | 类别 | 说明 |
|--------|------|------|
| 决策 | decision | 技术/战略决策记录 |
| 偏好 | preference | steve的偏好和反馈 |
| 项目 | project | 进行中的项目 |
| 目标 | goal | 目标设定 |
| 背景 | context | 环境/系统背景 |
| 知识 | knowledge | 学习到的知识 |
| 行为 | behavior | 行为模式 |
| 反馈 | feedback | 用户反馈 |
| 投资 | investment | 投资/资源决策 |
| 技术 | technical | 技术栈/工具 |

## 示例

```
/recall jiaolong                      召回jiaolong相关记忆（最多10条）
/recall jiaolong recent 5             jiaolong相关 + 最近5条
/recall jiaolong category=project     jiaolong相关 + 项目类别
/recent 3                          最近3条记忆
/recall category=preference        所有偏好类记忆
```

## 依赖

- `evolution_framework/memory_recall.py` - 核心召回引擎
- `memory/memory_hot.json` - 热层记忆存储

## 输出格式

```
## 相关记忆（N条）

1. 📋 [project] (置信95% | 相关度7.0)
   jiaolong_SRE闭环自动化方案.xlsx 已生成...
   📅 2026-04-02
```
