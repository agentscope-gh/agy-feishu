"""Card builders: system."""

import os
import re
from datetime import datetime

from cards.common import create_footer
from cards.locales import SYSTEM_WELCOME, SYSTEM_SECURITY_BLOCKED

def build_no_update_card(current_version):
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "green",
            "title": {"content": "✅ 系统已是最新版本", "tag": "plain_text"}
        },
        "elements": [
            {
                "tag": "markdown",
                "content": f"**当前运行版本**：`{current_version}`\n\n🎉 经过全网云端探测，本地代码已与云端保持一致。"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔄 强制重启重载服务"},
                        "type": "default",
                        "value": {"action": "user_choice", "choice": "/update confirm", "label": "强制重启重载服务"}
                    }
                ]
            },
            create_footer()
        ]
    }


def build_update_card(current_version, latest_version, changelog):
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "orange",
            "title": {"content": "🔄 系统 OTA 升级提醒", "tag": "plain_text"}
        },
        "elements": [
            {
                "tag": "markdown",
                "content": f"**当前版本**：`{current_version}`\n**发现新版本**：`{latest_version}`\n\n**更新日志 (Changelog)**：\n{changelog}\n\n<font color='red'>⚠️ 警告：执行升级将进行强制同步，会覆盖本地所有未提交的代码修改（您的 .env 配置和本地数据库不受影响）。</font>"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "确认并执行升级"},
                        "type": "primary",
                        "value": {"action": "user_choice", "choice": "/update confirm", "label": "确认并执行升级"}
                    }
                ]
            },
            create_footer()
        ]
    }


def build_welcome_card():
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "green",
            "title": {"content": SYSTEM_WELCOME["title"], "tag": "plain_text"}
        },
        "elements": [
            {
                "tag": "markdown",
                "content": SYSTEM_WELCOME["content"]
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "layout": "flow",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": SYSTEM_WELCOME["btn_project"]},
                        "type": "primary",
                        "value": {"action": "user_choice", "choice": "/project", "label": "工作区项目"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": SYSTEM_WELCOME["btn_model"]},
                        "type": "default",
                        "value": {"action": "user_choice", "choice": "/model", "label": "切换模型"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": SYSTEM_WELCOME["btn_help"]},
                        "type": "default",
                        "value": {"action": "user_choice", "choice": "/help", "label": "查看帮助"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": SYSTEM_WELCOME["btn_clear"]},
                        "type": "default",
                        "value": {"action": "user_choice", "choice": "/clear", "label": "清空上下文"}
                    }
                ]
            },
            create_footer()
        ]
    }


def build_security_warning(blocked_command):
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "red",
            "title": {"content": SYSTEM_SECURITY_BLOCKED["title"], "tag": "plain_text"}
        },
        "elements": [
            {
                "tag": "markdown",
                "content": SYSTEM_SECURITY_BLOCKED["template"].format(blocked_command=blocked_command)
            },
            create_footer()
        ]
    }


def build_help_card():
    elements = [
        {
            "tag": "markdown",
            "content": "🤖 **欢迎使用 Antigravity 智能助理控制台！**\n包含系统的所有指令与交互菜单，点击下方按钮或发送斜杠指令即可快速调起操作："
        },
        {"tag": "hr"},
        {
            "tag": "markdown",
            "content": (
                "🎛️ **模型与会话控制：**\n"
                "• `/menu` : ⚡ **快捷指令中心**（按场景分组列出所有指令，点击直接生效）\n"
                "• `/conversations` : 浏览宿主机最近活跃会话列表并一键接入\n"
                "• `/continue` : 快速接管宿主机上最近一次本地活跃会话 (对应 agy -c)\n"
                "• `/attach <id>` : 绑定指定会话 ID 并继承其完整上下文\n"
                "• `/model` : 弹出大模型选择面板，自由热切换模型\n"
                "• `/context` : 查看对话上下文 Token 占用统计与容量看板\n"
                "• `/memory` : 查看与管理您的个人偏好设定（支持交互式新增与删除）\n"
                "• `/brain` : 查看 Antigravity 全局跨会话记忆库\n"
                "• `/clear` : 彻底清空当前会话的上下文记忆，重新开始"
            )
        },
        {"tag": "hr"},
        {
            "tag": "markdown",
            "content": (
                "📁 **项目与记事本工程：**\n"
                "• `/project` : 弹出项目管理器（支持切换工作区、新建项目、设置路径与翻页）\n"
                "• `/note` : 记事本管理看板（支持添加、查看详情、删除与清空）\n"
                "• `/quota` : 查询 Google AI Pro 套餐官方剩余额度看板\n"
                "• `/status` : 查看机器人的运行状态、CPU/内存/Uptime 与日志"
            )
        },
        {"tag": "hr"},
        {
            "tag": "markdown",
            "content": (
                "⚡ **系统管理与运维：**\n"
                "• `/status` : 查看机器人的运行状态、CPU/内存/Uptime 与日志\n"
                "• `/plugin` : 打开插件中心管理器（查看已挂载插件与热重载）\n"
                "• `/stop` : 中止当前会话中正在执行的后台任务\n"
                "• `/update` : 检查并更新机器人服务至最新版本\n"
                "• `/ping` : 快速测试机器人服务连通性\n"
                "• `/help` : 显示此帮助卡片"
            )
        },

        {"tag": "hr"},
        {
            "tag": "markdown",
            "content": "🎯 **快捷交互控制** (点击一键调起)："
        },
        {
            "tag": "action",
            "layout": "flow",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "⚡ 快捷指令中心"},
                    "type": "primary",
                    "value": {"action": "user_choice", "choice": "/menu", "label": "快捷指令中心"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📂 会话管理"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/conversations", "label": "会话管理"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📁 项目管理"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/project", "label": "项目管理"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🤖 切换模型"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/model", "label": "切换模型"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🧠 偏好记忆"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/memory", "label": "偏好记忆"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📝 记事本"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/note", "label": "记事本"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🧹 清空上下文"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/clear", "label": "清空上下文"}
                }
            ]
        },
        {"tag": "hr"},
        {
            "tag": "markdown",
            "content": (
                "⚙️ **系统功能特性：**\n"
                "• **多模态文件解析**：支持处理 PDF、Word、语音、视频与图片格式\n"
                "• **受控终端执行**：支持受控执行终端命令与工作区文件读写\n"
                "• **网页内容解析**：输入网页链接可自动提取关键内容摘要"
            )
        },
        create_footer()
    ]

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"content": "💡 Antigravity 帮助与控制大厅", "tag": "plain_text"}
        },
        "elements": elements
    }


def build_status_card(cpu, mem_mb, uptime_str, status, restarts, err_logs, git_status="未知", bot_stats=None):
    status_emoji = "🟢" if status == "online" else "🔴"
    if not bot_stats:
        bot_stats = {"total_requests": 0, "success_requests": 0, "failed_requests": 0}
        
    elements = [
        {
            "tag": "markdown",
            "content": f"**服务状态**：{status_emoji} {status.upper()}\n**运行时长**：{uptime_str}\n**重启次数**：{restarts} 次"
        },
        {
            "tag": "hr"
        },
        {
            "tag": "markdown",
            "content": f"**🌿 代码库状态 (Git)**\n{git_status}"
        },
        {
            "tag": "hr"
        },
        {
            "tag": "markdown",
            "content": f"**📈 机器人请求统计 (自上次重启以来)**\n- **总请求数**: {bot_stats.get('total_requests', 0)}\n- **成功处理**: {bot_stats.get('success_requests', 0)}\n- **执行异常**: {bot_stats.get('failed_requests', 0)}"
        },
        {
            "tag": "hr"
        },
        {
            "tag": "markdown",
            "content": f"**💡 模型算力消耗统计 (自上次重启以来 · 自带模型)**\n- **累计消耗 Tokens**: {bot_stats.get('total_tokens', 0):,}"
        },
        {
            "tag": "hr"
        },
        {
            "tag": "markdown",
            "content": f"**💻 资源占用**\n- **CPU**：{cpu}%\n- **内存**：{mem_mb} MB"
        }
    ]
    
    elements.append({
        "tag": "hr"
    })
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🔄 刷新状态"},
                "type": "primary",
                "value": {"action": "refresh_status"}
            }
        ]
    })
    
    elements.append(create_footer())
    
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"content": "📊 服务器运行状态", "tag": "plain_text"}
        },
        "elements": elements
    }


def build_startup_card(start_time, pid, hostname, version_str, plugins=None, recovery_info=None):
    plugins_display = ", ".join(plugins) if plugins else "无"

    overview_text = (
        f"✅ **飞书核心服务已成功就绪并建立长连接！**\n\n"
        f"• **启动时间**：{start_time}\n"
        f"• **当前版本**：{version_str}\n"
        f"• **进程实例**：PID {pid} · 主机 {hostname}"
    )

    elements = [
        {
            "tag": "markdown",
            "content": overview_text
        },
        {"tag": "hr"},
        {
            "tag": "markdown",
            "content": f"🧩 **已挂载插件 ({len(plugins or [])})**：\n{plugins_display}"
        }
    ]

    if recovery_info and recovery_info.get("recovered_from_suppressed", 0) > 0:
        suppressed = recovery_info.get("recovered_from_suppressed", 0)
        streak = recovery_info.get("previous_streak", suppressed)
        elements.extend([
            {"tag": "hr"},
            {
                "tag": "markdown",
                "content": f"> ⚠️ **频控恢复提示**：此前系统连续检测到 **{streak}** 次高频重启，自动进入指数退避静默期（共抑制了 **{suppressed}** 次告警），现已度过冷却期并平稳恢复上线。"
            }
        ])

    elements.extend([
        {"tag": "hr"},
        {
            "tag": "action",
            "layout": "flow",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "⚡ 快捷菜单"},
                    "type": "primary",
                    "value": {"action": "user_choice", "choice": "/menu", "label": "快捷菜单"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📊 运行状态"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/status", "label": "运行状态"}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "💡 指令帮助"},
                    "type": "default",
                    "value": {"action": "user_choice", "choice": "/help", "label": "指令帮助"}
                }
            ]
        },
        create_footer()
    ])

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "green",
            "title": {"content": "🟢 飞书助手服务已上线", "tag": "plain_text"}
        },
        "elements": elements
    }
