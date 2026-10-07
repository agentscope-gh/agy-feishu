import os
import json
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import get_brain_dir, get_transcript_path
from logger import log
from storage.database import save_session_async


def clean_user_prompt(raw: str) -> str:
    """Clean system injected headers, prompt directives, and XML tags from user input."""
    if not raw:
        return ""
    m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    raw = re.sub(r"<[^>]+>", "", raw)

    paras = [p.strip() for p in raw.split("\n\n") if p.strip()]
    user_paras = []
    for p in reversed(paras):
        if any(p.startswith(prefix) for prefix in [
            "[System", "[Role:", "[Notice", "【必须执行】", "用户核心准则：", "当前任务判定为", "1. 【", "- Current active"
        ]):
            break
        user_paras.insert(0, p)

    if user_paras:
        cleaned = "\n\n".join(user_paras).strip()
    else:
        cleaned = paras[-1] if paras else raw.strip()

    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def clean_assistant_response(text: str) -> str:
    """Clean planning tags from assistant response text."""
    if not text:
        return ""
    text = re.sub(r"\[TASK_PLAN\].*?\[/TASK_PLAN\]", "", text, flags=re.DOTALL)
    return text.strip()


def parse_conversation_info(conv_id: str, current_conv_id: str = "") -> Optional[Dict[str, Any]]:
    """Parse metadata, turn count, and complete last turn context for a given conversation UUID."""
    transcript_path = get_transcript_path(conv_id)
    if not os.path.exists(transcript_path):
        return None

    mtime = os.path.getmtime(transcript_path)
    dt_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    turns = []
    current_turn = None
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                except Exception:
                    continue

                stype = data.get("type")
                if stype == "USER_INPUT":
                    if current_turn:
                        turns.append(current_turn)
                    raw_content = str(data.get("content", ""))
                    current_turn = {
                        "user_query": clean_user_prompt(raw_content),
                        "assistant_response": "",
                        "tool_names": [],
                        "tool_call_count": 0,
                        "status": data.get("status", "DONE"),
                        "created_at": data.get("created_at", "")
                    }
                elif current_turn:
                    if stype == "PLANNER_RESPONSE":
                        t_calls = data.get("tool_calls") or []
                        if t_calls:
                            current_turn["tool_call_count"] += len(t_calls)
                            for tc in t_calls:
                                n = tc.get("name")
                                if n and n not in current_turn["tool_names"]:
                                    current_turn["tool_names"].append(n)
                        txt = data.get("content") or ""
                        if txt.strip():
                            current_turn["assistant_response"] = clean_assistant_response(txt)
                    if data.get("status") == "ERROR":
                        current_turn["status"] = "ERROR"

        if current_turn:
            turns.append(current_turn)
    except Exception as e:
        log.warning(f"[Conversations] Failed to parse transcript for {conv_id}: {e}")

    turn_count = len(turns)
    last_turn = turns[-1] if turns else {
        "user_query": "",
        "assistant_response": "",
        "tool_names": [],
        "tool_call_count": 0,
        "status": "DONE",
        "created_at": dt_str
    }

    last_query_text = last_turn.get("user_query", "")
    summary_text = last_query_text[:120] if last_query_text else "(空会话或无文本输入)"

    return {
        "id": conv_id,
        "short_id": conv_id[:8],
        "mtime": mtime,
        "updated_at": dt_str,
        "turn_count": turn_count,
        "summary": summary_text,
        "last_turn": last_turn,
        "is_current": bool(current_conv_id and current_conv_id == conv_id),
    }


def get_recent_conversations(current_conv_id: str = "", limit: int = 5) -> List[Dict[str, Any]]:
    """Scan the brain directory for valid, non-empty conversation directories."""
    brain_dir = get_brain_dir()
    if not os.path.isdir(brain_dir):
        return []

    candidates = []
    try:
        for entry in os.listdir(brain_dir):
            if len(entry) != 36:
                continue
            entry_dir = os.path.join(brain_dir, entry)
            if not os.path.isdir(entry_dir):
                continue
            t_path = os.path.join(entry_dir, ".system_generated", "logs", "transcript.jsonl")
            if os.path.exists(t_path) and os.path.getsize(t_path) > 0:
                candidates.append((entry, os.path.getmtime(t_path)))
    except Exception as e:
        log.error(f"[Conversations] Error scanning brain dir: {e}")
        return []

    candidates.sort(key=lambda x: x[1], reverse=True)
    results = []
    for conv_id, _ in candidates:
        info = parse_conversation_info(conv_id, current_conv_id=current_conv_id)
        if info:
            results.append(info)
            if len(results) >= limit:
                break
    return results


def get_latest_conversation(exclude_id: str = "") -> Optional[Dict[str, Any]]:
    """Get the single most recently updated conversation, optionally excluding one."""
    recent = get_recent_conversations(current_conv_id=exclude_id, limit=3)
    for c in recent:
        if c["id"] != exclude_id:
            return c
    return recent[0] if recent else None


async def switch_chat_conversation(chat_id: str, session_data: dict, target_conv_id: str) -> Optional[Dict[str, Any]]:
    """Switch the chat to target_conv_id, persist to DB, reset session pool, and prewarm."""
    info = parse_conversation_info(target_conv_id)
    if not info:
        return None

    old_conv = session_data.get("conversation", "")
    session_data["conversation"] = target_conv_id
    await save_session_async(chat_id, session_data)

    try:
        from core.session_pool import session_pool
        await session_pool.reset_session(chat_id)
        from config import DEFAULT_MODEL
        model_to_warm = session_data.get("model") or DEFAULT_MODEL
        if model_to_warm in ["Default", "默认"]:
            model_to_warm = DEFAULT_MODEL
        proj_val = session_data.get("project")
        cwd_dir = proj_val if (proj_val and os.path.isdir(proj_val) and proj_val not in ["默认", "Default"]) else None
        effort = session_data.get("reasoning_effort", "medium")
        import asyncio
        asyncio.create_task(session_pool.prewarm(
            chat_id, model_to_warm, cwd_dir, conversation_id=target_conv_id, effort=effort
        ))
    except Exception as e:
        log.warning(f"[Conversations] Error resetting session pool for chat {chat_id}: {e}")

    log.info(f"[Conversations] Chat {chat_id} switched conversation from {old_conv[:8]} to {target_conv_id[:8]}")
    return info
