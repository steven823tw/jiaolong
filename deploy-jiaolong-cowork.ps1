# ═══════════════════════════════════════════════════════════════════════════
# jiaolong × Claude Code Cowork 一键部署脚本 (PowerShell)
# 版本: v5.0.0 | 2026-04-30
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  jiaolong × Claude Code Cowork 部署 v5.0.0          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── 路径配置 ──────────────────────────────────────────────────────────────

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$homeDir = $env:USERPROFILE
$jiaolongDir = Join-Path $homeDir ".claude" "jiaolong"
$skillsDir = Join-Path $homeDir ".claude" "skills"
$evolutionDir = Join-Path $jiaolongDir "evolution_framework"
$memoryDir = Join-Path $jiaolongDir "memory"
$hooksDir = Join-Path $jiaolongDir "hooks"

# ── Step 1: 创建目录结构 ──────────────────────────────────────────────────

Write-Host "[1/6] 创建目录结构..." -ForegroundColor Yellow

$dirs = @(
    $jiaolongDir,
    $evolutionDir,
    $memoryDir,
    (Join-Path $memoryDir "memory_warm"),
    (Join-Path $memoryDir "memory_cold"),
    $hooksDir,
    (Join-Path $evolutionDir "skills"),
    (Join-Path $evolutionDir "tools"),
    (Join-Path $evolutionDir "experiments"),
    (Join-Path $evolutionDir "coordinator"),
    (Join-Path $evolutionDir "services"),
    (Join-Path $evolutionDir "hooks")
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host "  ✅ 目录结构已创建" -ForegroundColor Green

# ── Step 2: 复制 evolution_framework ──────────────────────────────────────

Write-Host "[2/6] 复制 evolution_framework..." -ForegroundColor Yellow

$evolutionSource = Join-Path $scriptDir "evolution_framework"
if (Test-Path $evolutionSource) {
    Copy-Item -Path "$evolutionSource\*" -Destination $evolutionDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  ✅ evolution_framework 已复制" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  未找到 evolution_framework 目录，跳过" -ForegroundColor Yellow
}

# 复制入口脚本和配置
$filesToCopy = @("script.py", "cowork.plugin.json", "EVOLUTION_VERSION.json", "package.json")
foreach ($f in $filesToCopy) {
    $src = Join-Path $scriptDir $f
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $jiaolongDir -Force
    }
}

# ── Step 3: 复制 hooks ───────────────────────────────────────────────────

Write-Host "[3/6] 复制 hooks..." -ForegroundColor Yellow

$hooksSource = Join-Path $scriptDir "hooks"
if (Test-Path $hooksSource) {
    Copy-Item -Path "$hooksSource\*.py" -Destination $hooksDir -Force -ErrorAction SilentlyContinue
    Write-Host "  ✅ hooks 已复制" -ForegroundColor Green
}

# ── Step 4: 初始化记忆文件 ────────────────────────────────────────────────

Write-Host "[4/6] 初始化记忆文件..." -ForegroundColor Yellow

$memoryHot = Join-Path $memoryDir "memory_hot.json"
if (-not (Test-Path $memoryHot)) {
    @{
        facts = @()
        version = "1.0"
    } | ConvertTo-Json | Set-Content -Path $memoryHot -Encoding UTF8
    Write-Host "  ✅ memory_hot.json 已初始化" -ForegroundColor Green
} else {
    Write-Host "  ℹ️  memory_hot.json 已存在" -ForegroundColor Cyan
}

# ── Step 5: 更新 Skills SKILL.md ──────────────────────────────────────────

Write-Host "[5/6] 更新 Skills 路径引用..." -ForegroundColor Yellow

$skillDirs = Get-ChildItem -Path $skillsDir -Directory -Filter "jiaolong-*" -ErrorAction SilentlyContinue
foreach ($skillDir in $skillDirs) {
    $skillFile = Join-Path $skillDir.FullName "SKILL.md"
    if (Test-Path $skillFile) {
        $content = Get-Content -Path $skillFile -Raw -Encoding UTF8
        if ($content -match "openclaw") {
            $content = $content -replace "\.openclaw", ".claude\jiaolong"
            Set-Content -Path $skillFile -Value $content -Encoding UTF8
        }
    }
}

Write-Host "  ✅ Skills 路径已更新" -ForegroundColor Green

# ── Step 6: 配置 Hooks ───────────────────────────────────────────────────

Write-Host "[6/6] 配置 Claude Code Hooks..." -ForegroundColor Yellow

$settingsFile = Join-Path $homeDir ".claude" "settings.json"
if (Test-Path $settingsFile) {
    $settings = Get-Content -Path $settingsFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $settings.hooks) {
        $hookPath = "python " + (Join-Path $hooksDir "jiaolong_extract_hook.py").Replace("\", "/")
        $settings | Add-Member -NotePropertyName "hooks" -NotePropertyValue @{
            Stop = @(
                @{
                    matcher = ""
                    hooks = @(
                        @{
                            type = "command"
                            command = $hookPath
                        }
                    )
                }
            )
        }
        $settings | ConvertTo-Json -Depth 10 | Set-Content -Path $settingsFile -Encoding UTF8
        Write-Host "  ✅ Hooks 已添加到 settings.json" -ForegroundColor Green
    } else {
        Write-Host "  ℹ️  Hooks 已配置，跳过" -ForegroundColor Cyan
    }
} else {
    Write-Host "  ⚠️  settings.json 不存在，请手动配置" -ForegroundColor Yellow
}

# ── 完成 ──────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  部署完成！                                         ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  工作区: $jiaolongDir" -ForegroundColor White
Write-Host "║  记忆:   $memoryDir" -ForegroundColor White
Write-Host "║  Skills: $skillsDir\jiaolong-*" -ForegroundColor White
Write-Host "║  Hooks:  $hooksDir" -ForegroundColor White
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 验证
Write-Host "=== 验证 ===" -ForegroundColor Cyan
$pythonExe = "python"
if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonExe = "python3"
}

$jarvisCli = Join-Path $evolutionDir "jarvis_cli.py"
if (Test-Path $jarvisCli) {
    & $pythonExe $jarvisCli status 2>&1
} else {
    Write-Host "⚠️  jarvis_cli.py 未找到" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "重启 Claude Code 以加载新的 hooks 配置。" -ForegroundColor Yellow
