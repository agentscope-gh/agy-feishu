#!/usr/bin/env bash

# ==============================================================================
# Antigravity Feishu Bot 通用自动化部署与安装脚本
# 支持环境: Linux (Debian, Ubuntu, CentOS, Rocky, Alma, Fedora, Alpine, Arch, openSUSE)
# 支持场景: 物理主机、云主机 VPS、WSL / WSL2、Docker 容器、Kubernetes Pod
# 权限兼容: root 身份、具备 sudo 权限的普通用户、无 sudo 的受限普通用户
# ==============================================================================

set -eo pipefail

REPO_URL="https://github.com/agentscope-gh/agy-feishu.git"
SERVICE_NAME="agy-feishu-bot"
FOLDER_NAME="agy-feishu"

# ------------------------------------------------------------------------------
# 1. 命令行参数与交互状态解析
# ------------------------------------------------------------------------------
ACTION="install"
AUTO_YES=false
FORCE_ENV=false
NO_PM2=false
NO_START=false
CLI_APP_ID=""
CLI_APP_SECRET=""

# 检测终端是否为交互式 TTY
IS_INTERACTIVE=false
if [ -t 0 ]; then
    IS_INTERACTIVE=true
fi

# CI / 非交互式环境变量检测
if [ "${CI:-}" = "true" ] || [ "${NON_INTERACTIVE:-}" = "true" ]; then
    AUTO_YES=true
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        update)
            ACTION="update"
            shift
            ;;
        uninstall)
            ACTION="uninstall"
            shift
            ;;
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        -f|--force-env)
            FORCE_ENV=true
            shift
            ;;
        --no-pm2)
            NO_PM2=true
            shift
            ;;
        --no-start)
            NO_START=true
            shift
            ;;
        --app-id)
            CLI_APP_ID="$2"
            shift 2
            ;;
        --app-secret)
            CLI_APP_SECRET="$2"
            shift 2
            ;;
        -h|--help)
            echo "Antigravity Feishu Bot 部署脚本帮助"
            echo "用法: ./install.sh [命令] [选项]"
            echo ""
            echo "命令:"
            echo "  (无)        完整部署安装机器人服务"
            echo "  update      拉取最新代码并热升级现有服务"
            echo "  uninstall   卸载机器人后台服务与清理文件"
            echo ""
            echo "选项:"
            echo "  -y, --yes          全自动非交互模式，默认确认所有提示"
            echo "  -f, --force-env    强制重新生成 .env 配置文件"
            echo "  --no-pm2           跳过 PM2 依赖安装与后台常驻管理"
            echo "  --no-start         部署完成后不自动启动服务"
            echo "  --app-id <ID>      显式传入飞书 FEISHU_APP_ID"
            echo "  --app-secret <SEC> 显式传入飞书 FEISHU_APP_SECRET"
            echo "  -h, --help         显示此帮助信息"
            exit 0
            ;;
        *)
            echo "⚠️ 未知参数: $1 (输入 --help 查看使用说明)"
            shift
            ;;
    esac
done

prompt_confirm() {
    local message="$1"
    local default_ans="${2:-Y}"
    if [ "$AUTO_YES" = true ] || [ "$IS_INTERACTIVE" = false ]; then
        if [[ "$default_ans" =~ ^[Yy]$ ]]; then
            return 0
        else
            return 1
        fi
    fi

    local prompt_text="[Y/n]"
    [[ "$default_ans" =~ ^[Nn]$ ]] && prompt_text="[y/N]"

    read -r -p "$message $prompt_text: " user_input
    user_input="${user_input:-$default_ans}"
    if [[ "$user_input" =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# ------------------------------------------------------------------------------
# 2. 系统、环境与权限多维检测
# ------------------------------------------------------------------------------
IS_ROOT=false
[ "$EUID" -eq 0 ] && IS_ROOT=true

HAS_SUDO=false
if ! $IS_ROOT && command -v sudo &> /dev/null; then
    if sudo -n true 2>/dev/null || [ "$IS_INTERACTIVE" = true ]; then
        HAS_SUDO=true
    fi
fi

run_as_root() {
    if $IS_ROOT; then
        "$@"
    elif $HAS_SUDO; then
        sudo "$@"
    else
        return 1
    fi
}

IS_WSL=false
if grep -qi "microsoft" /proc/version 2>/dev/null || grep -qi "wsl" /proc/version 2>/dev/null; then
    IS_WSL=true
fi

IS_CONTAINER=false
if [ -f /.dockerenv ] || [ -f /run/.containerenv ] || grep -qa 'docker\|kubepods\|containerd' /proc/1/cgroup 2>/dev/null || [ -n "${KUBERNETES_SERVICE_HOST:-}" ]; then
    IS_CONTAINER=true
fi

DISTRO="unknown"
if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    DISTRO="${ID:-unknown}"
fi

PKG_MANAGER=""
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
elif command -v apk &> /dev/null; then
    PKG_MANAGER="apk"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
elif command -v zypper &> /dev/null; then
    PKG_MANAGER="zypper"
fi

print_environment_summary() {
    echo "=========================================="
    echo "    Antigravity Feishu Bot 部署与检测向导"
    echo "=========================================="
    echo "• 操作系统发行版: $DISTRO"
    echo "• 包管理器支持:   ${PKG_MANAGER:-未检测到标准包管理器}"
    if $IS_WSL; then
        echo "• 虚拟化层识别:   WSL / WSL2 (Windows Subsystem for Linux)"
    elif $IS_CONTAINER; then
        echo "• 虚拟化层识别:   容器环境 (Docker / K8s Pod)"
    else
        echo "• 虚拟化层识别:   裸机 / 云 VPS 主机"
    fi

    if $IS_ROOT; then
        echo "• 当前运行权限:   root 拥有最高权限"
    elif $HAS_SUDO; then
        echo "• 当前运行权限:   普通用户 (支持 sudo 提权)"
    else
        echo "• 当前运行权限:   普通用户 (无 sudo 提权，已启用用户空间自适应隔离模式)"
    fi
    echo "=========================================="
    echo ""
}

# ------------------------------------------------------------------------------
# 3. 处理 update 与 uninstall 子流程
# ------------------------------------------------------------------------------
if [ "$ACTION" == "update" ]; then
    print_environment_summary
    echo "⬇️ 正在拉取远程代码仓库..."
    git pull origin main || true

    PYTHON_BIN="python3"
    if [ -d "venv" ] && [ -f "venv/bin/python3" ]; then
        PYTHON_BIN="venv/bin/python3"
    fi

    echo "📦 正在更新 Python 核心依赖..."
    "$PYTHON_BIN" -m pip install --upgrade pip || true
    if [ -f "requirements.txt" ]; then
        "$PYTHON_BIN" -m pip install -r requirements.txt || true
    fi

    echo "🚀 正在重载机器人服务..."
    if command -v pm2 &> /dev/null; then
        if pm2 describe "$SERVICE_NAME" >/dev/null 2>&1; then
            pm2 restart "$SERVICE_NAME" || true
            pm2 save || true
            echo "✅ 服务已通过 PM2 重启。"
        else
            echo "⚠️ PM2 中未找到 $SERVICE_NAME 服务，跳过自动重启。"
        fi
    else
        echo "ℹ️ 系统未安装 PM2，请在相应进程管理器中重启服务。"
    fi
    echo "✅ 升级流程执行完毕！"
    exit 0
fi

if [ "$ACTION" == "uninstall" ]; then
    print_environment_summary
    if ! prompt_confirm "⚠️ 警告：此操作将彻底停止后台服务并可清除当前项目源码。确定要继续卸载吗？" "N"; then
        echo "✅ 已取消卸载操作。"
        exit 0
    fi

    echo "🛑 正在停止并移除后台服务..."
    if command -v pm2 &> /dev/null; then
        if pm2 describe "$SERVICE_NAME" >/dev/null 2>&1; then
            pm2 delete "$SERVICE_NAME" || true
            pm2 save || true
            echo "✅ PM2 服务 [$SERVICE_NAME] 已注销并清理。"
        fi
    fi

    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    if [ -f "$SCRIPT_DIR/main.py" ]; then
        if prompt_confirm "是否彻底删除项目源码目录 ($SCRIPT_DIR)？" "N"; then
            cd ..
            echo "🗑️ 正在删除源码目录: $SCRIPT_DIR ..."
            rm -rf "$SCRIPT_DIR"
            echo "✅ 源码已完全清除。"
        fi
    fi
    echo "✅ 卸载流程完成！"
    exit 0
fi

# ------------------------------------------------------------------------------
# 4. 正式部署 - 环境预检与基础包自动补充
# ------------------------------------------------------------------------------
print_environment_summary

if ! prompt_confirm "即将开始全自动检测与部署飞书机器人，确定要继续吗？" "Y"; then
    echo "✅ 已取消部署操作。"
    exit 0
fi

# 检查并尝试补齐系统包 (git, python3)
install_missing_system_tool() {
    local tool_name="$1"
    local deb_pkg="$2"
    local rhel_pkg="$3"
    local alpine_pkg="$4"

    if ! command -v "$tool_name" &> /dev/null; then
        echo "⚠️ 未检测到基础命令工具: $tool_name，尝试自动安装..."
        if ! run_as_root true 2>/dev/null; then
            echo "❌ 当前环境无 root/sudo 权限，无法自动安装 $tool_name。请联系系统管理员安装 $deb_pkg 后重试。"
            exit 1
        fi

        case "$PKG_MANAGER" in
            apt)
                run_as_root apt-get update && run_as_root apt-get install -y "$deb_pkg"
                ;;
            dnf)
                run_as_root dnf install -y "$rhel_pkg"
                ;;
            yum)
                run_as_root yum install -y "$rhel_pkg"
                ;;
            apk)
                run_as_root apk add --no-cache "$alpine_pkg"
                ;;
            pacman)
                run_as_root pacman -Sy --noconfirm "$deb_pkg"
                ;;
            zypper)
                run_as_root zypper install -y "$rhel_pkg"
                ;;
            *)
                echo "❌ 无法识别的包管理器，请手动安装: $tool_name"
                exit 1
                ;;
        esac
    fi
}

install_missing_system_tool "git" "git" "git" "git"
install_missing_system_tool "python3" "python3" "python3" "python3"

# 检查 Python 版本 (需 >= 3.10)
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "❌ 检测到当前 Python 版本为 $PY_VER，本项目要求 Python 3.10+，请升级 Python 版本。"
    exit 1
else
    echo "✅ Python 版本符合要求: $PY_VER"
fi

# ------------------------------------------------------------------------------
# 5. Node.js 与 PM2 守护安装适配 (支持无 root 纯用户空间隔离部署)
# ------------------------------------------------------------------------------
ensure_pm2_available() {
    if [ "$NO_PM2" = true ]; then
        echo "⏭️ 按照参数配置，跳过 PM2 检测与安装。"
        return 0
    fi

    if command -v pm2 &> /dev/null; then
        echo "✅ PM2 已就绪: $(pm2 -v 2>/dev/null || echo '可用')"
        return 0
    fi

    echo "ℹ️ 未检测到 pm2 命令，正在准备自动适配安装..."

    # 1. 如果没有 npm，先尝试安装 nodejs 与 npm
    if ! command -v npm &> /dev/null; then
        if run_as_root true 2>/dev/null; then
            echo "⬇️ 正在使用系统包管理器安装 nodejs 与 npm..."
            case "$PKG_MANAGER" in
                apt)
                    run_as_root apt-get update && run_as_root apt-get install -y nodejs npm || true
                    ;;
                dnf)
                    run_as_root dnf install -y nodejs npm || true
                    ;;
                yum)
                    run_as_root yum install -y nodejs npm || true
                    ;;
                apk)
                    run_as_root apk add --no-cache nodejs npm || true
                    ;;
                pacman)
                    run_as_root pacman -Sy --noconfirm nodejs npm || true
                    ;;
                zypper)
                    run_as_root zypper install -y nodejs npm || true
                    ;;
            esac
        else
            echo "⚠️ 当前无 root/sudo 权限，无法自动安装 nodejs/npm 系统包。"
        fi
    fi

    # 2. 如果具备 npm，安装 pm2
    if command -v npm &> /dev/null; then
        echo "⬇️ 正在配置并安装 PM2..."
        if $IS_ROOT; then
            npm install -g pm2 || true
        elif $HAS_SUDO; then
            sudo npm install -g pm2 || true
        else
            # 无 root/sudo 权限的纯用户空间安装模式
            echo "💡 启用用户空间 npm-global 模式安装 pm2..."
            NPM_USER_DIR="$HOME/.npm-global"
            mkdir -p "$NPM_USER_DIR"
            npm config set prefix "$NPM_USER_DIR"
            export PATH="$NPM_USER_DIR/bin:$PATH"

            # 写入当前用户的 shell 配置文件中
            for profile_file in "$HOME/.bashrc" "$HOME/.profile"; do
                if [ -f "$profile_file" ] && ! grep -q "\.npm-global/bin" "$profile_file"; then
                    echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> "$profile_file"
                fi
            done

            npm install -g pm2 || true
        fi
    fi

    if command -v pm2 &> /dev/null; then
        echo "✅ PM2 安装成功: $(pm2 -v 2>/dev/null || echo '可用')"
    else
        echo "⚠️ 未能完成 PM2 自动安装。服务部署完成后支持直接通过 python3 main.py 启动。"
    fi
}

ensure_pm2_available

# ------------------------------------------------------------------------------
# 6. Antigravity 引擎 (agy) 识别与 PATH 自动注入
# ------------------------------------------------------------------------------
check_antigravity_cli() {
    # 检查当前 PATH
    if command -v agy &> /dev/null || command -v antigravity &> /dev/null; then
        echo "✅ 检测到 Antigravity CLI 核心引擎。"
        return 0
    fi

    # 检查常见安装位置并自动注入 PATH
    local CANDIDATE_PATHS=(
        "$HOME/.local/bin"
        "$HOME/.gemini/antigravity-cli/bin"
        "/usr/local/bin"
    )

    for cpath in "${CANDIDATE_PATHS[@]}"; do
        if [ -f "$cpath/agy" ] || [ -f "$cpath/antigravity" ]; then
            echo "💡 在 $cpath 发现 Antigravity CLI 引擎，自动注入当前会话 PATH。"
            export PATH="$cpath:$PATH"
            for pfile in "$HOME/.bashrc" "$HOME/.profile"; do
                if [ -f "$pfile" ] && ! grep -q "$cpath" "$pfile"; then
                    echo "export PATH=\"$cpath:\$PATH\"" >> "$pfile"
                fi
            done
            return 0
        fi
    done

    echo "💡 提示: 未检测到宿主机 Antigravity (agy) 命令行引擎。"
    echo "   若后续需要执行本地代码审查或 agy 会话接管，建议安装 Google Antigravity CLI。"
}

check_antigravity_cli

# ------------------------------------------------------------------------------
# 7. 源码定位与仓库拉取
# ------------------------------------------------------------------------------
if [ ! -f "main.py" ]; then
    echo "⚠️ 当前目录下未发现 main.py，准备克隆项目仓库..."
    if [ ! -d "$FOLDER_NAME" ]; then
        echo "⬇️ 从 GitHub 克隆项目: $REPO_URL ..."
        git clone "$REPO_URL" "$FOLDER_NAME"
    fi
    cd "$FOLDER_NAME"
    echo "⬇️ 拉取最新代码..."
    git pull origin main || true
else
    echo "✅ 当前工作目录已处于项目源码根路径。"
    git pull origin main 2>/dev/null || true
fi

# ------------------------------------------------------------------------------
# 8. 环境变量配置 (.env) 自适应生成
# ------------------------------------------------------------------------------
setup_environment_config() {
    local should_configure=true

    if [ -f .env ] && [ "$FORCE_ENV" = false ]; then
        if [ "$AUTO_YES" = true ] || [ "$IS_INTERACTIVE" = false ]; then
            should_configure=false
            echo "✅ 检测到已有 .env 配置文件，自动模式下保持现有配置。"
        else
            if prompt_confirm "检测到已存在 .env 配置文件，是否覆盖重置？" "N"; then
                should_configure=true
            else
                should_configure=false
                echo "⏭️ 保留现有 .env 配置文件。"
            fi
        fi
    fi

    if [ "$should_configure" = true ]; then
        local app_id="${CLI_APP_ID:-${FEISHU_APP_ID:-}}"
        local app_secret="${CLI_APP_SECRET:-${FEISHU_APP_SECRET:-}}"
        local def_model="${DEFAULT_MODEL:-gemini-3.8-flash-high}"

        if [ -z "$app_id" ] || [ -z "$app_secret" ]; then
            if [ "$IS_INTERACTIVE" = true ]; then
                echo "--------------------------------------------------"
                echo "请输入飞书应用的认证凭据 (可在飞书开发者后台凭证页面获取):"
                read -r -p "👉 FEISHU_APP_ID (例: cli_a4...): " app_id
                read -r -p "👉 FEISHU_APP_SECRET: " app_secret
            else
                echo "⚠️ 非交互模式且未提供 FEISHU_APP_ID / FEISHU_APP_SECRET。"
                if [ -f ".env.example" ] && [ ! -f ".env" ]; then
                    cp .env.example .env
                    echo "📄 已自动根据 .env.example 生成模板文件，后续请记得手动补全密钥！"
                fi
                return 0
            fi
        fi

        if [ -n "$app_id" ] && [ -n "$app_secret" ]; then
            cat <<EOF > .env
FEISHU_APP_ID=$app_id
FEISHU_APP_SECRET=$app_secret
DEFAULT_MODEL=$def_model
DANGEROUSLY_SKIP_PERMISSIONS=true
EOF
            echo "✅ .env 配置文件已成功保存。"
        fi
    fi
}

setup_environment_config

# ------------------------------------------------------------------------------
# 9. Python 虚拟环境与依赖自适应隔离构建
# ------------------------------------------------------------------------------
setup_python_dependencies() {
    echo "📦 正在配置 Python 运行时环境与依赖组件..."
    local VENV_CREATED=false
    local PYTHON_TARGET="python3"

    # 1. 尝试创建 venv
    if [ ! -d "venv" ]; then
        if python3 -m venv venv 2>/dev/null; then
            VENV_CREATED=true
        else
            echo "⚠️ 标准 python3 -m venv 创建失败，尝试自动补齐系统 venv 依赖..."
            if run_as_root true 2>/dev/null; then
                case "$PKG_MANAGER" in
                    apt)
                        run_as_root apt-get update && run_as_root apt-get install -y python3-venv python3.11-venv python3.12-venv || true
                        ;;
                    dnf|yum)
                        run_as_root "$PKG_MANAGER" install -y python3-virtualenv || true
                        ;;
                    apk)
                        run_as_root apk add --no-cache py3-virtualenv || true
                        ;;
                esac
            fi

            if python3 -m venv venv 2>/dev/null; then
                VENV_CREATED=true
            elif command -v virtualenv &> /dev/null && virtualenv venv 2>/dev/null; then
                VENV_CREATED=true
            fi
        fi
    else
        VENV_CREATED=true
    fi

    # 2. 依赖安装处理 (venv 优先，回退到 --user / --break-system-packages)
    if [ "$VENV_CREATED" = true ] && [ -f "venv/bin/python3" ]; then
        echo "✅ 成功挂载本地隔离虚拟环境 (venv)。"
        PYTHON_TARGET="venv/bin/python3"
        "$PYTHON_TARGET" -m pip install --upgrade pip || true
        if [ -f "requirements.txt" ]; then
            "$PYTHON_TARGET" -m pip install -r requirements.txt
        else
            "$PYTHON_TARGET" -m pip install "lark-oapi>=1.7.3" "pydantic>=2.0" "pydantic-settings>=2.0" "aiosqlite>=0.20"
        fi
    else
        echo "⚠️ 无法创建独立虚拟环境，尝试用户级空间 (--user) 安装依赖..."
        PYTHON_TARGET="python3"
        local PIP_FLAGS=""
        if $IS_CONTAINER || $IS_ROOT; then
            PIP_FLAGS="--break-system-packages"
        else
            PIP_FLAGS="--user"
        fi

        if [ -f "requirements.txt" ]; then
            # shellcheck disable=SC2086
            python3 -m pip install $PIP_FLAGS -r requirements.txt || python3 -m pip install --user -r requirements.txt
        else
            # shellcheck disable=SC2086
            python3 -m pip install $PIP_FLAGS "lark-oapi>=1.7.3" "pydantic>=2.0" "pydantic-settings>=2.0" "aiosqlite>=0.20"
        fi
    fi

    echo "✅ Python 依赖安装就绪。"
    GLOBAL_PYTHON_TARGET="$PYTHON_TARGET"
}

setup_python_dependencies

# ------------------------------------------------------------------------------
# 10. 服务启动与常驻守护
# ------------------------------------------------------------------------------
if [ "$NO_START" = true ]; then
    echo ""
    echo "🎉 部署安装完成！已按要求跳过自动启动。"
    echo "👉 启动指令:"
    echo "   $GLOBAL_PYTHON_TARGET main.py"
    exit 0
fi

echo ""
echo "🚀 准备启动机器人服务..."

# 容器与 Pod 环境特殊提示
if $IS_CONTAINER; then
    echo "💡 容器运行提示: 当前环境为容器/Pod 实例。"
    echo "   若容器未配置守护层，前台直接运行可保证 Pod 生命周期:"
    echo "   $GLOBAL_PYTHON_TARGET main.py"
fi

if command -v pm2 &> /dev/null && [ "$NO_PM2" = false ]; then
    if prompt_confirm "是否立即使用 PM2 注册并常驻运行 $SERVICE_NAME 服务？" "Y"; then
        if pm2 describe "$SERVICE_NAME" >/dev/null 2>&1; then
            pm2 restart "$SERVICE_NAME"
            echo "✅ 服务已平滑重启。"
        else
            pm2 start "$GLOBAL_PYTHON_TARGET" --name "$SERVICE_NAME" -- main.py
            echo "✅ 服务已成功注册到 PM2 并常驻启动。"
        fi

        pm2 save 2>/dev/null || true
        echo ""
        echo "🎉 部署完成！飞书机器人正在后台稳定运行。"
        echo "• 查看运行日志: pm2 logs $SERVICE_NAME"
        echo "• 查看进程状态: pm2 status"
        exit 0
    fi
fi

echo ""
echo "🎉 部署完成！你可以通过以下命令在前台或 nohup 中启动机器人："
echo "   $GLOBAL_PYTHON_TARGET main.py"
