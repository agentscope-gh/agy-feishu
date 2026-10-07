"""Multi-mode task execution engine for cron_scheduler daemon."""

import asyncio
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from typing import Tuple

from logger import log


def build_reminder_card(task: dict) -> dict:
    """构建定时提醒专用交互卡片"""
    name = task.get("name", "定时提醒")
    prompt = task.get("prompt", "您设定的提醒时间到了！")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 动态匹配图标
    icon = "⏰"
    if "喝水" in name or "喝水" in prompt:
        icon = "💧"
    elif "站会" in name or "开会" in name or "会议" in prompt:
        icon = "📅"
    elif "吃" in name or "饭" in name:
        icon = "🍱"
    elif "休息" in name:
        icon = "☕"
    elif "巡检" in name or "检查" in name:
        icon = "🔍"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"{icon} 提醒事项：{name}"},
            "template": "blue"
        },
        "elements": [
            {
                "tag": "markdown",
                "content": f"**{prompt}**\n\n• **触发时间**：`{now_str}`\n• **任务编号**：`{task.get('id')}`"
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "layout": "flow",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚙️ 计划任务中心"},
                        "type": "default",
                        "value": {"action": "open_cron_panel"}
                    }
                ]
            }
        ]
    }


def build_execution_report_card(task: dict, result_text: str, is_error: bool = False, duration_ms: int = 0) -> dict:
    """构建任务执行报告卡片"""
    name = task.get("name", "计划任务")
    task_id = task.get("id", "")
    dur_str = f"{duration_ms / 1000.0:.2f} 秒" if duration_ms > 0 else "< 0.1 秒"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    action_type = task.get("action_type", "task")

    type_label = {
        "reminder": "💬 消息提醒",
        "shell": "🖥️ Shell 脚本",
        "ai_agent": "🧠 AI 智能巡检",
        "webhook": "🌐 Webhook 通知"
    }.get(action_type, "⚙️ 系统任务")

    header_color = "red" if is_error else "green"
    status_title = "❌ 任务执行异常" if is_error else "✅ 任务执行成功"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"{status_title}: {name}"},
            "template": header_color
        },
        "elements": [
            {
                "tag": "markdown",
                "content": f"**任务摘要**：\n• **类型**：`{type_label}`\n• **耗时**：`{dur_str}`\n• **时间**：`{now_str}`\n• **编号**：`{task_id}`"
            },
            {"tag": "hr"},
            {
                "tag": "markdown",
                "content": f"**执行输出**：\n{result_text}"
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "layout": "flow",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚙️ 打开任务面板"},
                        "type": "default",
                        "value": {"action": "open_cron_panel"}
                    }
                ]
            }
        ]
    }


async def execute_task(task: dict, send_card_func=None) -> Tuple[bool, str, int]:
    """
    通用任务分发执行引擎
    支持：
    1. reminder: 消息提醒
    2. shell: 本地 Shell 命令执行
    3. webhook: HTTP Webhook 触发
    4. ai_agent: 智能巡检报告生成
    """
    start_time = time.time()
    chat_id = task.get("chat_id")
    action_type = task.get("action_type", "reminder")
    prompt = task.get("prompt", "")
    command = task.get("command", "")

    # 如果任务指令中包含 reload_plugins，执行热重载
    if command == "sys_reload_plugins" or prompt == "sys_reload_plugins":
        try:
            from plugins.manager import plugin_manager
            plugin_manager.reload_plugins()
            log.info("[executors] execute_task successfully reloaded all plugins.")
            return True, "sys_reload_plugins done", 0
        except Exception as _e:
            log.error(f"[executors] Failed to reload plugins: {_e}")
            return False, str(_e), 0

    is_success = True
    result_text = ""

    try:
        # 1. 文本与卡片类提醒
        if action_type == "reminder":
            result_text = f"提醒内容已送达：{prompt}"
            if send_card_func and chat_id:
                card = build_reminder_card(task)
                await send_card_func(chat_id, card)

        # 2. Shell 运维脚本类任务
        elif action_type == "shell":
            cmd = command or prompt
            if not cmd:
                raise ValueError("Shell 任务未指定可执行命令")

            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
                out_str = stdout.decode("utf-8", errors="replace").strip()
                err_str = stderr.decode("utf-8", errors="replace").strip()

                if proc.returncode == 0:
                    result_text = f"```bash\n{out_str or '命令执行成功，无额外输出'}\n```"
                else:
                    is_success = False
                    result_text = f"❌ 命令执行返回非零状态码 `{proc.returncode}`\n\n```bash\n{err_str or out_str}\n```"
            except asyncio.TimeoutError:
                proc.kill()
                is_success = False
                result_text = "❌ 命令执行超时 (超过 60 秒限制)，已强制终止。"

            if send_card_func and chat_id:
                card = build_execution_report_card(task, result_text, is_error=not is_success, duration_ms=int((time.time() - start_time) * 1000))
                await send_card_func(chat_id, card)

        # 3. HTTP Webhook 类任务
        elif action_type in ("webhook", "http"):
            url = command or prompt
            if not url or not url.startswith(("http://", "https://")):
                raise ValueError("Webhook 任务需指定合法的 http:// 或 https:// 目标 URL")

            req = urllib.request.Request(url, headers={"User-Agent": "AgyFeishuCron/3.0"})
            loop = asyncio.get_running_loop()
            
            def _do_http():
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.getcode(), resp.read().decode("utf-8", errors="replace")[:500]

            status_code, body = await loop.run_in_executor(None, _do_http)
            result_text = f"🌐 Webhook 请求成功 (状态码 `{status_code}`)\n\n```text\n{body}\n```"

            if send_card_func and chat_id:
                card = build_execution_report_card(task, result_text, is_error=False, duration_ms=int((time.time() - start_time) * 1000))
                await send_card_func(chat_id, card)

        # 4. AI 智能巡检类任务
        elif action_type == "ai_agent":
            result_text = f"AI 巡检任务触发完成。\n预设指令：`{prompt}`\n已向目标会话就绪执行。"
            if send_card_func and chat_id:
                card = build_reminder_card(task)
                await send_card_func(chat_id, card)

        else:
            result_text = f"任务触发成功：{prompt}"
            if send_card_func and chat_id:
                card = build_reminder_card(task)
                await send_card_func(chat_id, card)

    except Exception as e:
        is_success = False
        result_text = f"执行异常: {str(e)}"
        if send_card_func and chat_id:
            try:
                card = build_execution_report_card(task, result_text, is_error=True, duration_ms=int((time.time() - start_time) * 1000))
                await send_card_func(chat_id, card)
            except Exception:
                pass

    duration_ms = int((time.time() - start_time) * 1000)
    return is_success, result_text, duration_ms
