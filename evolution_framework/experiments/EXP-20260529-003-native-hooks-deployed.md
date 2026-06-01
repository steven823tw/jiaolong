# EXP-20260529-003 | 原生记忆 Hooks 部署

> 实验时间: 2026-05-29
> 假设: 将 jiaolong hooks 重写为写入 Claude Code 原生记忆系统，可消除双轨制

## 改动

### 1. `jiaolong_extract_hook.py` (v6.0.0)
- **之前**: 写入 `~/.claude/jiaolong/memory/memory_hot.json` (JSON facts)
- **之后**: 写入 `~/.claude/projects/{project}/memory/*.md` (原生 frontmatter 格式)
- 新增: `get_project_memory_dir()` 根据 cwd 推断项目记忆目录
- 新增: `write_memory_file()` 写入单个 `.md` 文件
- 新增: `update_memory_index()` 更新 `MEMORY.md` 索引
- 改进: `generate_slug()` 从文件名/命令/中文关键词生成有意义的 slug
- 改进: `description` 优先从 "内容:" 部分提取，而非原始元数据

### 2. `jiaolong_memory_hook.py` (v6.0.0)
- **之前**: 从 `memory_hot.json` 搜索
- **之后**: 从 `~/.claude/projects/{project}/memory/*.md` 读取
- 新增: `load_native_memories()` 解析 frontmatter + body
- 改进: 评分算法加入类别权重 (feedback=1.5, user=1.3, project=1.2)
- 输出: `<system-reminder>` 格式，符合 Claude Code 系统提示风格

### 3. `settings.json`
- 新增: `jiaolong_memory_hook.py` 到 Stop hooks
- 现在 Stop 事件触发两个 hook: extract → recall

## 验证

| 测试 | 结果 |
|------|------|
| Extract hook 写入原生 .md | ✅ slug=engine, type=feedback |
| MEMORY.md 索引自动更新 | ✅ 条目正确追加 |
| 重复内容检测 | ✅ 跳过已存在记忆 |
| Recall hook 读取原生记忆 | ✅ 关键词匹配 + 类别权重 |
| Windows 编码兼容 | ✅ surrogatepass + replace |

## 结果
KEPT — 双轨制消除，记忆统一到原生系统
