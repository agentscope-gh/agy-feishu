import os
import asyncio
import re

from storage.database import delete_pending_task, get_session_async, get_profile_async, save_session_async
from cards import CardBuilder
from client.lark_client import send_interactive_card_sdk, patch_interactive_card_sdk, set_emoji_sdk, delete_emoji_sdk
from core.executor import execute_antigravity
from logger import log
import config
from core import stats
from core import app_state
from handlers.media import (
    _process_image_message,
    _process_post_message,
    _process_link_message,
    _process_file_audio_media_message,
    _process_batch_media_message,
)

# Local aliases so extracted code that referenced globals still works after light rewrite
running_processes = app_state.running_processes
chat_queues = app_state.chat_queues
chat_workers = app_state.chat_workers


def get_recent_conversation_context(session_data: dict, max_chars: int = 600) -> str:
    """提取前一轮对话上下文（待办任务、AI提出的方案或最近交互），用于决策网关评估."""
    if not isinstance(session_data, dict):
        return ""
    # 1. 优先使用已持久化记录的上一轮 AI 输出摘要
    last_summary = session_data.get("last_ai_summary")
    if last_summary and isinstance(last_summary, str) and last_summary.strip():
        last_user = session_data.get("last_user_query", "")
        if last_user:
            return f"Previous User Request: {last_user[:150]}\nPrevious AI Response/Plan: {last_summary.strip()[:max_chars]}"
        return last_summary.strip()[:max_chars]

    # 2. 兜底从 transcript.jsonl 中快速读取最近的 PLANNER_RESPONSE
    conv_id = session_data.get("conversation")
    if not conv_id:
        return ""

    from config import get_transcript_path
    transcript_path = get_transcript_path(conv_id)
    if not os.path.exists(transcript_path):
        return ""

    try:
        import json
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in reversed(lines[-200:]):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("type") == "PLANNER_RESPONSE" and data.get("content"):
                    content = str(data["content"]).strip()
                    if content:
                        clean_content = re.sub(r'```.*?```', '[代码块]', content, flags=re.DOTALL)
                        clean_content = re.sub(r'[\r\n]+', ' ', clean_content).strip()
                        return clean_content[:max_chars]
            except Exception:
                continue
    except Exception as e:
        log.warning(f"[Pipeline] Failed to read recent transcript context: {e}")

    return ""


CREDENTIAL_SENSITIVE_PATTERN = re.compile(
    r'(?:密码|password|token|令牌|ghp_|ssh|端口|port|root|ip\s*[:：地址\d]|服务器|server|vps|nas|macmini)',
    re.IGNORECASE
)

BROAD_QUERY_PATTERN = re.compile(
    r'(?:所有服务器|全部服务器|服务器列表|备忘录|每台服务器|所有主机|全部主机|密码本|服务器密码|列出凭证|所有凭证|凭证列表)',
    re.IGNORECASE
)


def extract_note_identifiers(note: str) -> list:
    """从一条凭证/服务器备忘录中提取出用于检索匹配的关键实体词、IP或域名."""
    identifiers = set()

    # 1. 提取 IPv4 地址
    ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', note)
    for ip in ips:
        identifiers.add(ip.lower())

    # 2. 提取域名
    domains = re.findall(r'\b[a-zA-Z0-9.-]+\.(?:pw|com|cn|org|net|xyz|top|me|cc|io)\b', note)
    for d in domains:
        identifiers.add(d.lower())

    # 3. 常见知名品牌、主机类型与代码托管平台
    known_targets = [
        "搬瓦工", "腾讯云", "阿里云", "华为云", "百度云", "飞牛", "群晖",
        "macmini", "mac mini", "树莓派", "raspberry", "github", "gitlab", "gitee"
    ]
    note_lower = note.lower()
    for kt in known_targets:
        if kt in note_lower:
            identifiers.add(kt)
            if kt == "macmini":
                identifiers.add("mac mini")
            elif kt == "mac mini":
                identifiers.add("macmini")

    # 4. 提取 "...服务器" / "...主机" / "...nas" / "...令牌" 前缀中的关键词
    prefix_matches = re.findall(r'([\u4e00-\u9fa5a-zA-Z0-9]{2,12})(?:服务器|主机|nas|令牌|token)', note)
    for m in prefix_matches:
        identifiers.add(m.lower())
        for brand in ["腾讯云", "阿里云", "华为云"]:
            if brand in m:
                identifiers.add(brand)
                region = m.replace(brand, "")
                if len(region) >= 2:
                    identifiers.add(region)

    if "github" in note_lower or "ghp_" in note_lower:
        identifiers.add("github")
        identifiers.add("ghp_")

    return [i for i in identifiers if i]


def filter_relevant_notes(notes: list, query: str, context: str = "") -> list:
    """
    JIT Credential & Note Injection (按需敏感凭证挂载):
    1. 非敏感的普通偏好/常规备忘：默认安全放行保留；
    2. 含有账号密码/SSH/IP/Token的高危凭证：
       - 当用户意图明确涉及该特定目标（如提及主机名、IP、域名、特定云厂商或Git推送等）时，才精准动态挂载对应凭证；
       - 若为泛化查询所有备忘录/服务器信息，全量挂载；
       - 本地常规工程、CSS调整、业务逻辑开发、闲聊问答，100% 屏蔽敏感凭证，杜绝隐私泄露与 Prompt 臃肿！
    """
    if not notes:
        return []

    combined_text = f"{query} {context}".lower()

    # 若用户明确查询全部凭证或备忘录清单
    if BROAD_QUERY_PATTERN.search(combined_text):
        return list(notes)

    filtered = []
    for note in notes:
        # 非敏感常规提醒，安全保留
        if not CREDENTIAL_SENSITIVE_PATTERN.search(note):
            filtered.append(note)
            continue

        # 敏感凭证：按需匹配
        identifiers = extract_note_identifiers(note)
        matched = False
        for ident in identifiers:
            if ident in combined_text:
                matched = True
                break

        # 对 github 令牌的额外友好语义匹配（用户说 push / 推送代码 / git 推送 时自动按需注入）
        if not matched and ("github" in note.lower() or "ghp_" in note.lower()):
            if any(k in combined_text for k in ["git push", "push代码", "推送代码", "推送到远程", "提交到远程", "push 到"]):
                matched = True

        if matched:
            filtered.append(note)

    return filtered


async def process_chat_queue(chat_id):
    queue = chat_queues[chat_id]
    try:
        while not queue.empty():
            task = await queue.get()
            try:
                await _process_single_task(chat_id, task)
                stats.record_success()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                stats.record_failure()
                log.error(f"Error processing queued task for {chat_id}: {e}")
            finally:
                queue.task_done()
                created_at = task.get("created_at")
                if created_at:
                    delete_pending_task(chat_id, created_at)
    except asyncio.CancelledError:
        log.info(f"Chat worker for {chat_id} was cancelled by /stop")
        try:
            from plugins.manager import plugin_manager
            await plugin_manager.dispatch_task_stop(chat_id)
        except Exception as e:
            log.error(f"Error dispatching task stop on worker cancellation: {e}")
    finally:
        chat_workers.pop(chat_id, None)
        # 回收空闲的队列条目，防止 chat_queues 随 chat_id 数量单调增长
        # 仅在队列为空时 pop，避免与并发入队产生竞态
        q = chat_queues.get(chat_id)
        if q is not None and q.empty():
            chat_queues.pop(chat_id, None)


async def _process_single_task(chat_id, task):
    message_id = task["message_id"]
    message_type = task["message_type"]
    content_json = task["content_json"]
    content_raw = task["content_raw"]
    raw_text = task["raw_text"]
    
    loop = asyncio.get_running_loop()
    session_data = await get_session_async(chat_id)
    
    # 首次部署成功后的欢迎引导消息推送
    if not session_data.get("welcome_sent"):
        session_data["welcome_sent"] = True
        await save_session_async(chat_id, session_data)
        welcome_card = CardBuilder.build_welcome_card()
        await loop.run_in_executor(None, lambda: send_interactive_card_sdk(message_id, welcome_card))
        
    downloaded_file_name = None
    download_success = True
    bot_reply_msg_id = task.get("bot_reply_msg_id")
    is_resumed = bool(task.get("resumed"))

    if message_type == "text":
        user_text = raw_text
    elif message_type == "image":
        if is_resumed:
            user_text = raw_text
        else:
            user_text, downloaded_file_name, download_success, bot_reply_msg_id = await _process_image_message(loop, message_id, content_json, content_raw)
    elif message_type == "post":
        if is_resumed:
            user_text = raw_text
        else:
            user_text, downloaded_file_name, download_success, bot_reply_msg_id = await _process_post_message(loop, message_id, content_json)
    elif message_type == "link":
        if is_resumed:
            user_text = raw_text
        else:
            user_text, downloaded_file_name, download_success, bot_reply_msg_id = await _process_link_message(content_json)
    elif message_type in ["file", "audio", "media"]:
        if is_resumed:
            user_text = raw_text
        else:
            user_text, downloaded_file_name, download_success, bot_reply_msg_id = await _process_file_audio_media_message(loop, message_id, message_type, content_json)
    elif message_type == "batch_media":
        if is_resumed:
            user_text = raw_text
        else:
            user_text, downloaded_file_name, download_success, bot_reply_msg_id = await _process_batch_media_message(loop, message_id, content_json)
    else:
        user_text = f"[暂不支持的消息类型: {message_type}]"

    if not user_text:
        return

    # 🚀 极致性能优化：抢先下发首张打字机/思考交互卡片（秒回卡片）
    # 彻底杜绝因等待 TypeSafe Jev 远程认知网关（~2s）、插件初始化或会话锁导致的前端卡片延迟
    is_voice_message = bool(
        task.get("message_type") == "audio" or 
        task.get("is_voice_message")
    )
    if not bot_reply_msg_id and not is_resumed:
        init_card = CardBuilder.build_typing_indicator(
            downloaded_file_name, download_success, user_text, is_voice=is_voice_message
        )
        try:
            bot_reply_msg_id = await app_state.run_feishu_sync(
                loop, lambda: send_interactive_card_sdk(message_id, init_card)
            )
            if bot_reply_msg_id:
                task["bot_reply_msg_id"] = bot_reply_msg_id
                try:
                    save_pending_task(chat_id, task)
                except Exception:
                    pass
        except Exception as e:
            log.warning(f"[Pipeline] Failed to send early typing card for chat {chat_id}: {e}")

    # 先预热上一轮的档位，与 Jev 判定并行；若新档位不同，判定后再切到精确档位。
    prewarm_task = None
    prewarmed_model = session_data.get("model", "Default")
    prewarmed_effort = session_data.get("reasoning_effort", "low")
    try:
        from core.session_pool import session_pool
        proj_val = session_data.get("project")
        cwd_dir = proj_val if (proj_val and os.path.isdir(proj_val) and proj_val not in ["默认", "Default"]) else None
        conv_id_to_resume = session_data.get("conversation", "") if not is_resumed else ""
        prewarm_task = asyncio.create_task(
            session_pool.prewarm(
                chat_id, prewarmed_model, cwd_dir,
                conversation_id=conv_id_to_resume, effort=prewarmed_effort
            )
        )
    except Exception:
        pass

    from plugins.manager import plugin_manager
    session_data["bot_reply_msg_id"] = bot_reply_msg_id

    # 1. 运行插件 on_before_ai 钩子
    user_text, session_data = await plugin_manager.dispatch_before_ai(user_text, chat_id, session_data)
    if not user_text or not user_text.strip():
        log.info(f"Message in chat {chat_id} was intercepted and consumed by plugin hook. Skipping AI execution.")
        return

    # 2. 插件极速直达通道 (Fast-Path / 零模型冷启动延迟)
    # 服务器状态巡检
    if any(kw in user_text for kw in ["服务器状态", "系统状态", "健康巡检", "系统健康", "巡检报告"]):
        health_plugin = plugin_manager.plugins.get("server_health")
        if health_plugin and health_plugin.enabled:
            log.info(f"[FastPath] Direct dispatch to server_health plugin for chat {chat_id}")
            handled = await health_plugin.on_command("/health", "", chat_id, message_id, session_data)
            if handled:
                return

    # 备忘录快速访问
    if any(kw in user_text for kw in ["查看备忘", "列出备忘", "所有备忘", "查看笔记", "列出笔记", "所有笔记", "查备忘", "查笔记"]):
        notes_plugin = plugin_manager.plugins.get("notes_manager")
        if notes_plugin and notes_plugin.enabled:
            log.info(f"[FastPath] Direct dispatch note listing to notes_manager for chat {chat_id}")
            handled = await notes_plugin.on_command("/notes", "", chat_id, message_id, session_data)
            if handled:
                return

    # 计划任务定时创建快速识别
    cron_plugin = plugin_manager.plugins.get("cron_scheduler")
    if cron_plugin and cron_plugin.enabled:
        try:
            from plugins.cron_scheduler.scheduler import parse_schedule_intent
            if parse_schedule_intent(user_text):
                log.info(f"[FastPath] Direct dispatch schedule intent to cron_scheduler for chat {chat_id}")
                handled = await cron_plugin.on_command("/cron", user_text, chat_id, message_id, session_data)
                if handled:
                    return
        except Exception as e:
            log.warning(f"[FastPath] Failed to parse schedule intent: {e}")

    # 3. 区分提问与命令 (严格贯彻：提问纯文本秒回，操作自主执行到底)
    OPERATION_KEYWORDS = [
        "创建", "删除", "修改", "编写", "运行", "执行", "安装", "部署", "构建",
        "写一个", "实现", "修复", "排查", "启动", "停止", "git", "bash", "python",
        "commit", "push", "pull", "test", "docker", "pm2", "发给", "发送文件"
    ]
    is_complex_agent = (
        session_data.get("mode") == "agent"
        or any(kw in user_text.lower() for kw in OPERATION_KEYWORDS)
    )

    current_proj = session_data.get("project", "默认")

    system_instruction = (
        "[System Rule: MUST ALWAYS communicate, reply, explain, and write responses in Simplified Chinese (简体中文). "
        "Any English text in the response must be limited to code syntax or technical names only. "
        "Absolute directive: NEVER output internal chain-of-thought, reasoning steps, planning commentary, or English preambles. "
        "Output ONLY your final answer directly in Simplified Chinese.]\n\n"
        "[System Feishu Resource Delivery / 飞书文件传送规范]\n"
        "1. 【统一使用飞书官方推送】：向用户提供文件时，请在最终回复中直接以标准 Markdown 链接输出该文件的本地绝对路径（例如 `[导出报告.xlsx](/path/to/file.xlsx)` 或 `📄 [文档.md](/path/to/doc.md)`），系统后台会自动拦截该路径并调用飞书官方 API 原生推送到当前会话供用户点击下载。严禁在脚本中私自 curl/webhook 传文件。\n"
        "2. 【命令行主动发送】：在终端脚本中如需主动传送文件，可直接运行 `python3 send_to_feishu.py <文件路径>`。\n\n"
        f"[System Active Project Context]\n- Current active project workspace path is: {current_proj}\n\n"
        "[System Execution & Safety Guardrails]\n"
        "1. 【全指令强制超时】：终端执行必须前缀 `timeout <秒数>`。\n"
        "2. 【受限递归与安全避让】：严禁系统全盘无限制递归搜索；严禁重启当前飞书机器人自身进程。\n"
        "3. 【计划任务调度能力】：用户有定时提醒或周期任务时，使用 run_command 执行 CLI 注册到 cron_scheduler 引擎中。\n\n"
        "[System Punctuation & Typography Directive / 排版标点规范]\n"
        "严禁使用弯双引号 “ ” 或弯单引号 ‘ ’（部分客户端会渲染为两个单引号），中文引用一律使用直角引号 「 」 或加粗 **强调**。\n\n"
    )

    project_prompts = session_data.get("project_prompts", {})
    if current_proj in project_prompts and project_prompts[current_proj]:
        proj_prompt_text = project_prompts[current_proj]
        system_instruction += f"[Active Project Specific Rules & Description]\n{proj_prompt_text}\n\n"

    if is_complex_agent:
        system_instruction += (
            "[System Mandatory Task Planning Directive / 任务规划强制规范]\n"
            "【必须执行】：只要你判断当前任务需要调用工具执行操作（读写代码、运行终端命令、多步排错、生成导出文件等），必须在回复的最开始输出一行结构化规划标签：\n"
            "[TASK_PLAN] 步骤1名称 | 步骤2名称 | 步骤3名称 | 步骤4名称 [/TASK_PLAN]\n"
            "规则要求：规划精炼定制（3~4步为宜），输出标签后立即调用首个工具开始执行，不要输出任何多余过渡句；纯文本问答严禁输出此标签。\n\n"
            "[System Autonomous Execution Directive / 自主执行决策规范]\n"
            "用户核心准则：【严格区分提问与命令】。\n"
            "1. 【命令必须自主执行并交付】：对于用户的操作、修改、运行、测试、排查等执行诉求（包括「改吧」、「执行」等简短授权），你必须作为全功能 Autonomous Agent 自主调用相应工具直接执行并交付最终结果！\n"
            "2. 【绝对严禁推诿与二次确认】：严禁让用户在服务器或本地终端手动运行命令；严禁抛出多选方案让用户做选择题；严禁停下来等待用户确认；绝对严禁以「受安全策略限制」为借口拒绝执行命令！\n\n"
        )
    else:
        system_instruction += (
            "[System Interaction Directive / 问答交互规范]\n"
            "用户核心准则：【严格区分提问与命令】。\n"
            "1. 【提问秒回纯文本】：当用户提出的是概念咨询、原理解释、方案探讨或日常闲聊时，无需调用工具，直接针对问题组织语言，用凝练、专业、清晰的语言进行解答。\n"
            "2. 【操作绝不推诿拒执】：若用户意图中含有明确的操作诉求，你依然拥有完整的全套 Agent 工具调用能力，必须自主调用工具完成任务，绝对严禁以「处于轻量纯文本交互模式」为由拒绝执行，严禁推诿让用户手动操作！\n\n"
        )

    # 注入长期记忆上下文（由 ai_memory 插件提取）
    mem_ctx = session_data.get("memory_context")
    if mem_ctx:
        system_instruction += f"[User Long-Term Memory / 用户长期偏好与记忆]\n{mem_ctx}\n\n"

    # 注入用户备忘录 Notes
    raw_notes = session_data.get("notes", [])
    if raw_notes:
        recent_context = get_recent_conversation_context(session_data)
        relevant_notes = filter_relevant_notes(raw_notes, user_text, context=recent_context)
        if relevant_notes:
            notes_block = "\n".join([f"- {note}" for note in relevant_notes])
            system_instruction += f"[User's Permanent Notes / 备忘录]\n{notes_block}\n\n"

    # Load long-term memory if this is a new conversation
    final_prompt = user_text
    is_new_conversation = not session_data.get("conversation")
    if is_new_conversation:
        memories = await get_profile_async(chat_id)
        if memories:
            memory_block = "\n".join([f"- {m}" for m in memories])
            final_prompt = f"[System Context: User preferences:]\n{memory_block}\n\n[User's Message:]\n{user_text}"
            
    # Delegate execution to executor
    # 43200s (12小时) 总超时兜底：支持长达数小时至十几小时的超大型自动化工程任务
    # 超时时 CancelledError 会进入 execute_antigravity，其 finally 块仍会执行清理
    is_error = False
    try:
        is_error = await asyncio.wait_for(
            execute_antigravity(
                chat_id, user_text, message_id, bot_reply_msg_id, session_data, 
                is_new_conversation, system_instruction, final_prompt, downloaded_file_name, 
                download_success, running_processes, is_resumed=is_resumed, task_meta=task
            ),
            timeout=43200.0
        )
    except asyncio.TimeoutError:
        log.error(f"[Pipeline] execute_antigravity hard timeout (43200s / 12h) for chat {chat_id}")
        is_error = True
    except Exception as e:
        log.error(f"[Pipeline] execute_antigravity raised for chat {chat_id}: {e}")
        is_error = True
    
    if is_error:
        await set_emoji(message_id, "CrossMark")
    else:
        await set_emoji(message_id, "DONE")





async def set_emoji(message_id, emoji_type):
    # Map custom / obsolete emojis to standard Lark emoji names
    mapping = {
        "StatusReading": "Typing",
        "CrossMark": "CrossMark",
        "DONE": "DONE"
    }
    mapped_type = mapping.get(emoji_type, emoji_type)
    
    loop = asyncio.get_running_loop()
    try:
        reaction_id = await app_state.run_feishu_sync(loop, lambda: set_emoji_sdk(message_id, mapped_type))
        return reaction_id
    except Exception as e:
        log.error(f"Failed to set emoji reaction {emoji_type}: {e}")
        return None


async def delete_emoji(message_id, reaction_id):
    if not reaction_id:
        return
    loop = asyncio.get_running_loop()
    try:
        await app_state.run_feishu_sync(loop, lambda: delete_emoji_sdk(message_id, reaction_id))
    except Exception as e:
        log.error(f"Failed to delete emoji reaction: {e}")

# emoji_spinner removed
