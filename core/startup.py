"""Startup notification and progressive debounce engine for Antigravity Feishu Bot.

Ensures the administrator is notified via Feishu interactive card whenever the service
boots or restarts, while preventing notification storms via exponential backoff cooldowns.
"""

import asyncio
from datetime import datetime
import os
import socket
import time
from typing import Dict, Tuple, Optional

from config import ADMIN_USERS
from logger import log
from storage.database import get_bot_meta, set_bot_meta, get_db

# Debounce configuration
BASE_COOLDOWN = 60.0        # Initial cooldown window (seconds)
RAPID_WINDOW = 120.0        # Threshold under which a restart is considered rapid (seconds)
MAX_COOLDOWN = 1800.0       # Maximum cooldown cap (30 minutes)
BACKOFF_FACTOR = 2.0        # Exponential backoff multiplier


def evaluate_startup_notification(now: Optional[float] = None) -> Tuple[bool, Dict]:
    """Evaluate whether a startup notification should be dispatched.

    Returns:
        (should_notify, details_dict)
    """
    if now is None:
        now = time.time()

    last_time_str = get_bot_meta("startup_last_time")
    streak_str = get_bot_meta("startup_streak")
    cooldown_str = get_bot_meta("startup_cooldown")
    suppressed_str = get_bot_meta("startup_suppressed_count")

    last_time = float(last_time_str) if last_time_str else 0.0
    streak = int(streak_str) if streak_str else 0
    current_cooldown = float(cooldown_str) if cooldown_str else BASE_COOLDOWN
    suppressed_count = int(suppressed_str) if suppressed_str else 0

    delta = now - last_time

    # Determine if this restart occurred within the active rapid window / backoff cooldown
    is_rapid = (last_time > 0) and (delta < max(RAPID_WINDOW, current_cooldown))

    if is_rapid:
        streak += 1
        # Exponential backoff: base * (factor ^ (streak - 1))
        new_cooldown = min(BASE_COOLDOWN * (BACKOFF_FACTOR ** (streak - 1)), MAX_COOLDOWN)
        suppressed_count += 1

        set_bot_meta("startup_last_time", str(now))
        set_bot_meta("startup_streak", str(streak))
        set_bot_meta("startup_cooldown", str(new_cooldown))
        set_bot_meta("startup_suppressed_count", str(suppressed_count))

        return False, {
            "streak": streak,
            "cooldown": new_cooldown,
            "suppressed": suppressed_count,
            "delta": delta,
        }

    # Healthy / normal startup: record and reset counters
    recovered_suppressed = suppressed_count
    recovered_streak = streak

    set_bot_meta("startup_last_time", str(now))
    set_bot_meta("startup_streak", "0")
    set_bot_meta("startup_cooldown", str(BASE_COOLDOWN))
    set_bot_meta("startup_suppressed_count", "0")

    return True, {
        "recovered_from_suppressed": recovered_suppressed,
        "previous_streak": recovered_streak,
        "cooldown": BASE_COOLDOWN,
        "delta": delta,
    }


def record_update_restart(now: Optional[float] = None):
    """Mark an update-triggered restart to reset streak counters and avoid false rapid alarm."""
    if now is None:
        now = time.time()
    set_bot_meta("startup_last_time", str(now))
    set_bot_meta("startup_streak", "0")
    set_bot_meta("startup_cooldown", str(BASE_COOLDOWN))
    set_bot_meta("startup_suppressed_count", "0")


def resolve_admin_target() -> Optional[str]:
    """Resolve the target chat_id or open_id of the administrator."""
    # 1. Primary: persisted admin_chat_id in bot_meta
    admin_chat_id = get_bot_meta("admin_chat_id")
    if admin_chat_id:
        return admin_chat_id

    # 2. Configured ADMIN_USERS in environment
    if ADMIN_USERS:
        return ADMIN_USERS[0]

    # 3. Fallback: query auth_sessions table for admin role
    try:
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT chat_id FROM auth_sessions WHERE role = 'admin' ORDER BY updated_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row and row["chat_id"]:
                return row["chat_id"]
        finally:
            conn.close()
    except Exception as e:
        log.error(f"[StartupNotice] Error querying admin session: {e}")

    return None


async def notify_admin_startup_async(is_update_restart: bool = False, delay: float = 2.0):
    """Background task to notify administrator of successful service startup."""
    if is_update_restart:
        record_update_restart()
        log.info("[StartupNotice] Service restart triggered by OTA update; startup notice skipped.")
        return

    if delay > 0:
        await asyncio.sleep(delay)

    loop = asyncio.get_running_loop()
    should_notify, details = await loop.run_in_executor(None, evaluate_startup_notification)

    if not should_notify:
        log.warning(
            f"[StartupNotice] High-frequency restart detected! Notification suppressed. "
            f"Streak={details.get('streak')}, Cooldown={details.get('cooldown'):.0f}s, "
            f"SuppressedCount={details.get('suppressed')}, Delta={details.get('delta', 0):.1f}s"
        )
        return

    admin_target = await loop.run_in_executor(None, resolve_admin_target)
    if not admin_target:
        log.info("[StartupNotice] No administrator target chat found; startup notification skipped.")
        return

    try:
        from cards import CardBuilder
        from client.lark_client import send_card_to_chat_async
        from core.commands import get_version_string
        from plugins.manager import plugin_manager

        start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pid = os.getpid()
        hostname = socket.gethostname()
        version_str = await loop.run_in_executor(None, lambda: get_version_string("HEAD"))
        plugins = list(plugin_manager.plugins.keys())

        card = CardBuilder.build_startup_card(
            start_time=start_time_str,
            pid=pid,
            hostname=hostname,
            version_str=version_str,
            plugins=plugins,
            recovery_info=details,
        )

        ok = await send_card_to_chat_async(admin_target, card)
        if ok:
            log.info(f"[StartupNotice] Successfully dispatched startup card to admin ({admin_target}).")
        else:
            log.error(f"[StartupNotice] Failed to dispatch startup card to admin ({admin_target}).")
    except Exception as e:
        log.error(f"[StartupNotice] Exception while sending startup notification: {e}")
