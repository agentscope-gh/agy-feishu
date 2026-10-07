"""Card builders: conversations management & switching."""

from cards.common import create_footer


def build_conversation_list_card(conversations: list, current_conv_id: str = "") -> dict:
    elements = [
        {
            "tag": "markdown",
            "content": f"📋 **当前绑定会话**：`{current_conv_id or '未绑定（发送消息自动新建）'}`\n\n以下是本地检测到的最近活跃 `agy conversation`，可点击一键接入："
        }
    ]

    if not conversations:
        elements.append({
            "tag": "markdown",
            "content": "*(暂无检测到本地历史会话)*"
        })
    else:
        for idx, c in enumerate(conversations, 1):
            is_current = c.get("is_current", False)
            status_badge = "🟢 **[当前活跃]** " if is_current else ""
            summary_escaped = c['summary'].replace("\n", " ")

            last_turn = c.get("last_turn") or {}
            last_resp = (last_turn.get("assistant_response") or "").replace("\n", " ").strip()
            resp_preview = f"\n> 🤖 {last_resp[:80]}..." if last_resp else ""

            card_item_md = (
                f"{status_badge}**{idx}. `{c['short_id']}`** · 🕒 {c['updated_at']} ({c['turn_count']} 轮)\n"
                f"> 👤 {summary_escaped[:80]}"
                f"{resp_preview}"
            )
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "markdown",
                "content": card_item_md
            })

            action_buttons = []
            if is_current:
                action_buttons.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "✅ 当前会话"},
                    "type": "primary",
                    "value": {"action": "noop"}
                })
            else:
                action_buttons.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": f"⚡ 接入 {c['short_id']}"},
                    "type": "default",
                    "value": {"action": "switch_conversation", "conversation_id": c["id"]}
                })

            elements.append({
                "tag": "action",
                "layout": "flow",
                "actions": action_buttons
            })

    elements.append({"tag": "hr"})
    # Bottom control buttons
    elements.append({
        "tag": "action",
        "layout": "flow",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🔄 刷新列表"},
                "type": "default",
                "value": {"action": "refresh_conversations"}
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "➕ 开启全新会话"},
                "type": "default",
                "value": {"action": "new_conversation"}
            }
        ]
    })
    elements.append(create_footer())

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"content": "📂 本地 agy 会话管理器", "tag": "plain_text"}
        },
        "elements": elements
    }


def build_conversation_switched_card(conv_info: dict, previous_conv_id: str = "") -> dict:
    last_turn = conv_info.get("last_turn") or {}
    user_q = (last_turn.get("user_query") or "").strip()
    assist_r = (last_turn.get("assistant_response") or "").strip()
    status = last_turn.get("status", "DONE")
    tool_count = last_turn.get("tool_call_count", 0)
    tools = last_turn.get("tool_names", [])

    status_str = "✅ 已就绪 (空闲等待指令)" if status != "ERROR" else "⚠️ 上轮异常或被中断"
    elements = [
        {
            "tag": "markdown",
            "content": (
                f"🎉 **已成功接管本地会话！**\n\n"
                f"> 🆔 **会话 ID**：`{conv_info['id']}`\n"
                f"> 🕒 **最后更新**：{conv_info['updated_at']} (共 {conv_info['turn_count']} 轮历史)\n"
                f"> ⚡ **运行状态**：{status_str}"
            )
        }
    ]

    # If there is last turn history, render the snapshot
    if user_q or assist_r:
        snapshot_lines = ["📜 **上一轮执行快照 (Last Turn Context)**"]

        if user_q:
            display_q = user_q[:300] + ("..." if len(user_q) > 300 else "")
            quoted_q = "\n> ".join(display_q.splitlines())
            snapshot_lines.append(f"👤 **用户提问**：\n> {quoted_q}")

        if assist_r:
            ellipsis_text = "\n> \n> *(余下内容已省略，可直接继续追问)*" if len(assist_r) > 600 else ""
            display_r = assist_r[:600] + ellipsis_text
            quoted_r = "\n> ".join(display_r.splitlines())
            snapshot_lines.append(f"🤖 **最后交付**：\n> {quoted_r}")
        elif status == "ERROR":
            snapshot_lines.append("🤖 **最后交付**：\n> *(执行过程发生异常，未生成完整回复)*")
        else:
            snapshot_lines.append("🤖 **最后交付**：\n> *(已完成前序指令，等待新输入)*")

        if tool_count > 0:
            tool_str = ", ".join(f"`{t}`" for t in tools[:4])
            if len(tools) > 4:
                tool_str += f" 等 {len(tools)} 种工具"
            snapshot_lines.append(f"🛠️ **工具执行**：共调用 {tool_count} 次 ({tool_str})")

        elements.append({"tag": "hr"})
        elements.append({
            "tag": "markdown",
            "content": "\n\n".join(snapshot_lines)
        })

    elements.append({"tag": "hr"})
    elements.append({
        "tag": "markdown",
        "content": "*💡 后台会话池已重新预热就绪，直接在飞书中发送消息即可无缝承接上述工作。*"
    })
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "action",
        "layout": "flow",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📂 查看所有会话"},
                "type": "default",
                "value": {"action": "show_conversations"}
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "➕ 新建对话 (/clear)"},
                "type": "default",
                "value": {"action": "new_conversation"}
            }
        ]
    })
    elements.append(create_footer())

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "green",
            "title": {"content": "✅ 已接管 agy 会话", "tag": "plain_text"}
        },
        "elements": elements
    }
