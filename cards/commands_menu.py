"""Card builder: Grouped quick commands menu."""

from typing import Dict, Any
from cards.common import create_footer, build_card


def build_commands_menu_card(is_admin: bool = False) -> Dict[str, Any]:
    """Build a categorized interactive card listing all shortcut commands with one-click execution."""
    elements = [
        {
            "tag": "markdown",
            "content": (
                "⚡ **快捷指令中心 (Quick Commands Menu)**\n"
                "常用功能指令已按场景分类归纳。**直接点击下方按钮即可触发执行**，无需手动记忆与输入斜杠命令："
            )
        },
        {"tag": "hr"},
        # 1. Models & Sessions
        {
            "tag": "markdown",
            "content": (
                "🤖 **大模型与会话管理：**\n"
                "• `/model` 切换大模型 / 思考深度　• `/conversations` 浏览历史会话\n"
                "• `/continue` 极速接管终端会话　• `/clear` 清空当前记忆　• `/stop` 紧急熔断"
            )
        },
        {
            "tag": "action",
            "layout": "flow",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🤖 切换模型"},
                    "type": "primary",
                    "value": {"action": "user_choice", "choice": "/model", "label": "切换模型"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📂 历史会话"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/conversations", "label": "历史会话"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "⚡ 极速接管"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/continue", "label": "极速接管"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🧹 清空记忆"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/clear", "label": "清空记忆"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "⏹️ 紧急熔断"},
                    "type": "danger",
                    "value": {"action": "user_choice", "choice": "/stop", "label": "紧急熔断"}
                }
            ]
        },
        {"tag": "hr"},
        # 2. Workspace & Projects
        {
            "tag": "markdown",
            "content": (
                "📁 **工作区与项目工程：**\n"
                "• `/project` 漫游宿主机项目目录、切换工作区、新建工程或克隆 Git 仓库\n"
                "• `/project clear` 重置并回退到默认工作区根目录"
            )
        },
        {
            "tag": "action",
            "layout": "flow",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📁 项目管理器"},
                    "type": "primary",
                    "value": {"action": "user_choice", "choice": "/project", "label": "项目管理器"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔄 重置工作区"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/project clear", "label": "重置工作区"}
                }
            ]
        },
        {"tag": "hr"},
        # 3. Monitoring & Quota
        {
            "tag": "markdown",
            "content": (
                "📊 **监控诊断与配额：**\n"
                "• `/quota` 官方 Google AI Pro 剩余配额与重置倒计时\n"
                "• `/context` 当前会话 Token 水位与容量　• `/health` 服务器负载与硬件健康\n"
                "• `/ping` 网络与核心服务连通性"
            )
        },
        {
            "tag": "action",
            "layout": "flow",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📊 查询配额"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/quota", "label": "查询配额"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📈 Token 水位"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/context", "label": "Token 水位"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🖥️ 服务器健康"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/health", "label": "服务器健康"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🏓 连通性测试"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/ping", "label": "连通性测试"}
                }
            ]
        },
        {"tag": "hr"},
        # 4. Utilities & Memory
        {
            "tag": "markdown",
            "content": (
                "📝 **随身工具与偏好记忆：**\n"
                "• `/note` 随身记事本与备忘清单　• `/cron` 计划任务管理中心 (定时/周期)\n"
                "• `/memory` 个人个性化偏好画像　• `/brain` Antigravity 全局跨会话记忆库"
            )
        },
        {
            "tag": "action",
            "layout": "flow",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📝 随身记事本"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/note", "label": "随身记事本"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "⏱️ 计划任务中心"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/cron", "label": "计划任务中心"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🧠 偏好记忆"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/memory", "label": "偏好记忆"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🌐 全局记忆图谱"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/brain", "label": "全局记忆图谱"}
                }
            ]
        }
    ]

    # 5. Admin operations
    if is_admin:
        elements.extend([
            {"tag": "hr"},
            {
                "tag": "markdown",
                "content": (
                    "🔐 **系统运维与权限治理 (管理员专属)：**\n"
                    "• `/status` 服务运行状态、Uptime 与日志　• `/user` 用户/群聊授权与权限档位\n"
                    "• `/plugin` 插件中心与动态热重载　• `/update` OTA 升级检测与平滑重启"
                )
            },
            {
                "tag": "action",
                "layout": "flow",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚙️ 系统看板"},
                        "type": "default",
                        "value": {"action": "user_choice", "choice": "/status", "label": "系统看板"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "👥 权限管理"},
                        "type": "default",
                        "value": {"action": "user_choice", "choice": "/user", "label": "权限管理"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🧩 插件中心"},
                        "type": "default",
                        "value": {"action": "user_choice", "choice": "/plugin", "label": "插件中心"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🚀 检查更新"},
                        "type": "default",
                        "value": {"action": "user_choice", "choice": "/update", "label": "检查更新"}
                    }
                ]
            }
        ])

    # Bottom navigation & actions
    elements.extend([
        {"tag": "hr"},
        {
            "tag": "action",
            "layout": "flow",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔄 刷新菜单"},
                    "type": "default",
                    "value": {"action": "refresh_command_menu"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "💡 查看详细手册 (/help)"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/help", "label": "查看详细手册"}
                }
            ]
        },
        create_footer()
    ])

    return build_card(
        header={
            "template": "blue",
            "title": {"content": "⚡ Antigravity 快捷指令中心", "tag": "plain_text"}
        },
        elements=elements
    )
