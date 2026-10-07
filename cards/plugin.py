"""Plugin management card builder for agy-feishu."""

from datetime import datetime
from cards.common import create_footer


def build_plugin_panel_card(plugin_list: list, active_tab: str = "installed") -> dict:
    """Build interactive card displaying installed plugins."""
    elements = [
        {
            "tag": "markdown",
            "content": f"**📦 已安装插件中心 (共 {len(plugin_list)} 个插件)**\n"
                       f"管理本地 `plugins/` 扩展插件与运行状态。"
        },
        {"tag": "hr"}
    ]

    if not plugin_list:
        elements.append({
            "tag": "markdown",
            "content": "⚠️ *当前 `plugins/` 目录下暂无启用的插件。*"
        })
    else:
        for p in plugin_list:
            pid = p.get("id", "")
            name = p.get("name", pid)
            version = p.get("version", "1.0.0")
            cmds = p.get("commands", [])
            cmd_str = ", ".join([f"`{c}`" for c in cmds]) if cmds else "无专属指令"
            enabled = p.get("enabled", True)
            status_tag = "🟢 已激活" if enabled else "⚪ 已禁用"

            elements.append({
                "tag": "markdown",
                "content": f"**{name}** (`{pid}` v{version})\n"
                           f"• **运行状态**：{status_tag}\n"
                           f"• **注册指令**：{cmd_str}"
            })
            elements.append({"tag": "hr"})

    elements.append({
        "tag": "action",
        "layout": "flow",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🔄 热重载插件库 (Reload)"},
                "type": "primary",
                "value": {"action": "reload_plugins"}
            }
        ]
    })

    elements.append({
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": f"最后扫描更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        ]
    })

    footer = create_footer()
    if footer:
        elements.append(footer)

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "🧩 插件管理中心"},
            "template": "blue"
        },
        "elements": elements
    }

