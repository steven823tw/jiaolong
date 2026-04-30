#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# jiaolong × Claude Code Cowork 一键部署脚本
# 版本: v5.0.0 | 2026-04-30
# ═══════════════════════════════════════════════════════════════════════════

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║  jiaolong × Claude Code Cowork 部署 v5.0.0          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 路径配置 ──────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$HOME"
JIAOLONG_DIR="$HOME_DIR/.claude/jiaolong"
SKILLS_DIR="$HOME_DIR/.claude/skills"
EVOLUTION_DIR="$JIAOLONG_DIR/evolution_framework"
MEMORY_DIR="$JIAOLONG_DIR/memory"
HOOKS_DIR="$JIAOLONG_DIR/hooks"

# ── Step 1: 创建目录结构 ──────────────────────────────────────────────────

echo "[1/6] 创建目录结构..."

mkdir -p "$JIAOLONG_DIR"
mkdir -p "$EVOLUTION_DIR"
mkdir -p "$MEMORY_DIR"
mkdir -p "$MEMORY_DIR/memory_warm"
mkdir -p "$MEMORY_DIR/memory_cold"
mkdir -p "$HOOKS_DIR"
mkdir -p "$EVOLUTION_DIR/skills"
mkdir -p "$EVOLUTION_DIR/tools"
mkdir -p "$EVOLUTION_DIR/experiments"
mkdir -p "$EVOLUTION_DIR/coordinator"
mkdir -p "$EVOLUTION_DIR/services"
mkdir -p "$EVOLUTION_DIR/hooks"

echo "  ✅ 目录结构已创建"

# ── Step 2: 复制 evolution_framework ──────────────────────────────────────

echo "[2/6] 复制 evolution_framework..."

if [ -d "$SCRIPT_DIR/evolution_framework" ]; then
    cp -r "$SCRIPT_DIR/evolution_framework/"* "$EVOLUTION_DIR/" 2>/dev/null || true
    echo "  ✅ evolution_framework 已复制"
else
    echo "  ⚠️  未找到 evolution_framework 目录，跳过"
fi

# 复制入口脚本
if [ -f "$SCRIPT_DIR/script.py" ]; then
    cp "$SCRIPT_DIR/script.py" "$JIAOLONG_DIR/"
fi

# 复制配置文件
for f in cowork.plugin.json EVOLUTION_VERSION.json package.json; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        cp "$SCRIPT_DIR/$f" "$JIAOLONG_DIR/"
    fi
done

# ── Step 3: 复制 hooks ───────────────────────────────────────────────────

echo "[3/6] 复制 hooks..."

if [ -d "$SCRIPT_DIR/hooks" ]; then
    cp "$SCRIPT_DIR/hooks/"*.py "$HOOKS_DIR/" 2>/dev/null || true
    echo "  ✅ hooks 已复制"
fi

# ── Step 4: 初始化记忆文件 ────────────────────────────────────────────────

echo "[4/6] 初始化记忆文件..."

if [ ! -f "$MEMORY_DIR/memory_hot.json" ]; then
    cat > "$MEMORY_DIR/memory_hot.json" << 'MEMEOF'
{
  "facts": [],
  "version": "1.0"
}
MEMEOF
    echo "  ✅ memory_hot.json 已初始化"
else
    FACT_COUNT=$(python3 -c "import json; d=json.load(open('$MEMORY_DIR/memory_hot.json')); print(len(d.get('facts',d) if isinstance(d,dict) else d))" 2>/dev/null || echo "?")
    echo "  ℹ️  memory_hot.json 已存在 ($FACT_COUNT 条记忆)"
fi

# ── Step 5: 更新 Skills SKILL.md ──────────────────────────────────────────

echo "[5/6] 更新 Skills 路径引用..."

# 更新所有 jiaolong skills 的 SKILL.md，添加 Python 路径指引
for skill_dir in "$SKILLS_DIR"/jiaolong-*/; do
    if [ -d "$skill_dir" ]; then
        skill_name=$(basename "$skill_dir")
        skill_file="$skill_dir/SKILL.md"
        if [ -f "$skill_file" ]; then
            # 替换 .openclaw 路径为 .claude/jiaolong
            if grep -q "openclaw" "$skill_file" 2>/dev/null; then
                sed -i 's|\.openclaw|\.claude/jiaolong|g' "$skill_file"
            fi
        fi
    fi
done

echo "  ✅ Skills 路径已更新"

# ── Step 6: 配置 Hooks ───────────────────────────────────────────────────

echo "[6/6] 配置 Claude Code Hooks..."

SETTINGS_FILE="$HOME_DIR/.claude/settings.json"

# 检查是否已有 hooks 配置
if [ -f "$SETTINGS_FILE" ]; then
    if grep -q '"hooks"' "$SETTINGS_FILE" 2>/dev/null; then
        echo "  ℹ️  Hooks 已配置，跳过"
    else
        # 添加 hooks 配置（保留现有内容）
        python3 -c "
import json
with open('$SETTINGS_FILE', 'r', encoding='utf-8') as f:
    data = json.load(f)
data['hooks'] = {
    'Stop': [
        {
            'matcher': '',
            'hooks': [
                {
                    'type': 'command',
                    'command': 'python $HOOKS_DIR/jiaolong_extract_hook.py'
                }
            ]
        }
    ]
}
with open('$SETTINGS_FILE', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
" 2>/dev/null && echo "  ✅ Hooks 已添加到 settings.json" || echo "  ⚠️  请手动配置 hooks"
    fi
fi

# ── 完成 ──────────────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  部署完成！                                         ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  工作区: $JIAOLONG_DIR"
echo "║  记忆:   $MEMORY_DIR"
echo "║  Skills: $SKILLS_DIR/jiaolong-*"
echo "║  Hooks:  $HOOKS_DIR"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  验证: python $EVOLUTION_DIR/jarvis_cli.py status"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# 验证
echo "=== 验证 ==="
export PATH="$HOME/.local/bin:$PATH"
python3 "$EVOLUTION_DIR/jarvis_cli.py" status 2>/dev/null || echo "⚠️  验证需要 Python3，请确保已安装"

echo ""
echo "重启 Claude Code 以加载新的 hooks 配置。"
