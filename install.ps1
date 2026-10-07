# ==============================================================================
# Antigravity Feishu Bot Windows 安装脚本 (PowerShell)
# 支持环境: Windows 10 / Windows 11 / Windows Server (PowerShell 5.1+ & Core 7+)
# ==============================================================================

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [ValidateSet("install", "update", "uninstall")]
    [string]$Action = "install",

    [Alias("y")]
    [switch]$Yes,

    [Alias("f")]
    [switch]$ForceEnv,

    [string]$AppId = "",
    [string]$AppSecret = "",
    [string]$Model = "gemini-3.8-flash-high",
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"

# 设置控制台输出编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RepoUrl = "https://github.com/agentscope-gh/agy-feishu.git"
$FolderName = "agy-feishu"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "    Antigravity Feishu Bot Windows 安装向导" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

function Confirm-Prompt([string]$Message, [bool]$DefaultYes=$true) {
    if ($Yes) { return $true }
    $suffix = if ($DefaultYes) { "[Y/n]" } else { "[y/N]" }
    $response = Read-Host "$Message $suffix"
    if ([string]::IsNullOrWhiteSpace($response)) {
        return $DefaultYes
    }
    return ($response -match "^[Yy]$")
}

# --- Action: Update ---
if ($Action -eq "update") {
    Write-Host "⬇️ 正在拉取远程代码仓库..." -ForegroundColor Yellow
    & git pull origin main
    
    $pythonExe = "python.exe"
    if (Test-Path "venv\Scripts\python.exe") {
        $pythonExe = ".\venv\Scripts\python.exe"
    }

    Write-Host "📦 正在更新 Python 依赖..." -ForegroundColor Yellow
    & $pythonExe -m pip install --upgrade pip
    if (Test-Path "requirements.txt") {
        & $pythonExe -m pip install -r requirements.txt
    }
    Write-Host "✅ 升级完成！如需运行请执行 start.bat 或 python main.py" -ForegroundColor Green
    exit 0
}

# --- Action: Uninstall ---
if ($Action -eq "uninstall") {
    if (-not (Confirm-Prompt "⚠️ 确定要彻底清理当前项目环境与文件吗？" $false)) {
        Write-Host "✅ 已取消卸载操作。" -ForegroundColor Green
        exit 0
    }
    $currentDir = Get-Location
    Set-Location ..
    Write-Host "🗑️ 正在删除项目目录: $currentDir ..." -ForegroundColor Yellow
    Remove-Item -Path $currentDir -Recurse -Force
    Write-Host "✅ 彻底卸载完成！" -ForegroundColor Green
    exit 0
}

# 1. 检查 Python
try {
    $pyVersion = & python --version 2>&1
    Write-Host "✅ 检测到 Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 未检测到 Python，请先从 https://www.python.org 或 Microsoft Store 安装 Python 3.10+" -ForegroundColor Red
    exit 1
}

# 2. 检查 Git
try {
    $gitVersion = & git --version 2>&1
    Write-Host "✅ 检测到 Git: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 未检测到 Git，请先安装 Git for Windows (https://git-scm.com/download/win)" -ForegroundColor Red
    exit 1
}

# 3. 检查代码目录
if (-not (Test-Path "main.py")) {
    if (-not (Test-Path $FolderName)) {
        Write-Host "⬇️ 正在从 GitHub 克隆仓库..." -ForegroundColor Yellow
        & git clone $RepoUrl $FolderName
    }
    Set-Location $FolderName
}

# 4. 创建虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "📦 正在创建 Python 虚拟环境 (venv)..." -ForegroundColor Yellow
    & python -m venv venv
    Write-Host "✅ 虚拟环境创建完成。" -ForegroundColor Green
}

# 5. 安装依赖
Write-Host "📦 正在安装依赖包..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -m pip install --upgrade pip
if (Test-Path "requirements.txt") {
    & .\venv\Scripts\python.exe -m pip install -r requirements.txt
} else {
    & .\venv\Scripts\python.exe -m pip install "lark-oapi>=1.7.3" "pydantic>=2.0" "pydantic-settings>=2.0" "aiosqlite>=0.20"
}
Write-Host "✅ 依赖安装完成。" -ForegroundColor Green

# 6. 配置 .env
$needConfigEnv = $false
if (-not (Test-Path ".env") -or $ForceEnv) {
    $needConfigEnv = $true
} else {
    Write-Host "✅ 已存在 .env 配置文件。" -ForegroundColor Green
}

if ($needConfigEnv) {
    $targetAppId = if (-not [string]::IsNullOrWhiteSpace($AppId)) { $AppId } else { $env:FEISHU_APP_ID }
    $targetAppSecret = if (-not [string]::IsNullOrWhiteSpace($AppSecret)) { $AppSecret } else { $env:FEISHU_APP_SECRET }

    if ([string]::IsNullOrWhiteSpace($targetAppId) -or [string]::IsNullOrWhiteSpace($targetAppSecret)) {
        if (-not $Yes) {
            Write-Host ""
            Write-Host "请输入飞书应用的配置信息 (可在飞书开发者后台获取):" -ForegroundColor Cyan
            $targetAppId = Read-Host "👉 FEISHU_APP_ID (例: cli_a4...)"
            $targetAppSecret = Read-Host "👉 FEISHU_APP_SECRET"
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($targetAppId) -and -not [string]::IsNullOrWhiteSpace($targetAppSecret)) {
        $envContent = @"
FEISHU_APP_ID=$targetAppId
FEISHU_APP_SECRET=$targetAppSecret
DEFAULT_MODEL=$Model
DANGEROUSLY_SKIP_PERMISSIONS=true
"@
        Set-Content -Path ".env" -Value $envContent -Encoding UTF8
        Write-Host "✅ .env 文件已生成。" -ForegroundColor Green
    } else {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env" -Force
            Write-Host "⚠️ 已复制 .env.example 模板，请稍后手动在 .env 中填入飞书凭据。" -ForegroundColor Yellow
        }
    }
}

# 7. 生成快捷启动脚本 start.bat
$batContent = @"
@echo off
chcp 65001 >nul
title Antigravity Feishu Bot
echo 正在启动 Antigravity 飞书机器人...
call .\venv\Scripts\activate.bat
python main.py
pause
"@
Set-Content -Path "start.bat" -Value $batContent -Encoding UTF8
Write-Host "✅ 已生成一键启动脚本: start.bat" -ForegroundColor Green

# 8. 完成总结
Write-Host ""
Write-Host "🎉 安装完成！你可以通过以下方式启动机器人：" -ForegroundColor Cyan
Write-Host "   1. 双击运行 start.bat" -ForegroundColor Yellow
Write-Host "   2. 命令行执行: .\venv\Scripts\python.exe main.py" -ForegroundColor Yellow

if (-not $NoStart) {
    if (Confirm-Prompt "是否立即在当前窗口启动机器人？" $false) {
        Write-Host "🚀 正在启动服务..." -ForegroundColor Cyan
        & .\venv\Scripts\python.exe main.py
    }
}
