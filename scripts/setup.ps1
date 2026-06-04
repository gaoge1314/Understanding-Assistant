<#
 .SYNOPSIS
  知识卡包整合包初始化脚本
  创建所需的目录结构并安装 Python 依赖

 .DESCRIPTION
  在首次克隆/下载整合包后运行此脚本，它会：
  1. 创建 input/ 目录结构（用户放置学习资料）
  2. 创建 output/ 目录结构（运行生成结果）
  3. 安装 scripts/requirements.txt 中的 Python 依赖
#>

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot

Write-Host "=== 知识卡包 初始化开始 ===" -ForegroundColor Cyan
Write-Host ""

# === 1. 创建目录结构 ===
$Directories = @(
    "input\参考资料",
    "input\大纲",
    "output\markdown",
    "output\json",
    "output\knowledge",
    "output\processed"
)

Write-Host "[1/3] 创建目录结构..." -ForegroundColor Yellow
foreach ($Dir in $Directories) {
    $Path = Join-Path $RootDir $Dir
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Host "  创建: $Dir"
    } else {
        Write-Host "  已存在: $Dir"
    }
}
Write-Host ""

# === 2. 安装 Python 依赖 ===
$RequirementsPath = Join-Path $RootDir "scripts\requirements.txt"
if (Test-Path $RequirementsPath) {
    Write-Host "[2/3] 安装 Python 依赖..." -ForegroundColor Yellow

    # 检查 pip 是否可用
    $pip = Get-Command "pip" -ErrorAction SilentlyContinue
    if (-not $pip) {
        $pip = Get-Command "pip3" -ErrorAction SilentlyContinue
    }

    if ($pip) {
        Write-Host "  找到 pip: $($pip.Source)"
        & $pip.Source install -r $RequirementsPath
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Python 依赖安装完成" -ForegroundColor Green
        } else {
            Write-Host "  依赖安装可能失败，请手动执行: pip install -r scripts\requirements.txt" -ForegroundColor Red
        }
    } else {
        Write-Host "  未找到 pip，请手动安装 Python 后执行:" -ForegroundColor Red
        Write-Host "  pip install -r scripts\requirements.txt"
    }
} else {
    Write-Host "[2/3] 未找到 requirements.txt，跳过依赖安装" -ForegroundColor Yellow
}
Write-Host ""

# === 3. 完成 ===
Write-Host "[3/3] 初始化完成！" -ForegroundColor Cyan
Write-Host ""
Write-Host "目录结构已就绪：" -ForegroundColor Green
Write-Host "  input/参考资料/   ← 放教材、课堂笔记、录音转文字等"
Write-Host "  input/大纲/       ← 放考点大纲文件"
Write-Host "  output/           ← 运行结果自动生成到这里"
Write-Host ""
Write-Host "使用方法：" -ForegroundColor Cyan
Write-Host "  1. 将学习资料放入 input/参考资料/ 目录"
Write-Host "  2. 在 Trae IDE 中触发 understanding-memory skill"
Write-Host "  3. 按提示操作即可生成知识卡包"
Write-Host ""
Write-Host "注意：本整合包依赖 Trae IDE 自带的 pdf skill 来解析 PDF/DOCX 文件。" -ForegroundColor Yellow
Write-Host "      首次使用请确保已安装 pdf skill。" -ForegroundColor Yellow