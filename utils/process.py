"""
Cross-platform process management utilities.
Seamlessly supports Linux (x86_64/arm64), macOS (Darwin), and Windows (win32).
"""

import asyncio
import os
import signal
import subprocess
import sys
from typing import Any, Dict, List, Optional

from logger import log

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def get_subprocess_popen_kwargs(
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Return platform-appropriate popen keyword arguments for creating an isolated
    process group / session.
    - On POSIX (Linux/macOS): setsid creates a new session.
    - On Windows: CREATE_NEW_PROCESS_GROUP creates a new process group.
    """
    kwargs: Dict[str, Any] = {}
    if cwd:
        kwargs["cwd"] = cwd
    if env:
        kwargs["env"] = env

    if IS_WINDOWS:
        # CREATE_NEW_PROCESS_GROUP = 0x00000200
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        kwargs["creationflags"] = flags
    else:
        if hasattr(os, "setsid"):
            kwargs["preexec_fn"] = os.setsid

    return kwargs


def kill_process_tree(pid: int, force: bool = True) -> None:
    """
    Terminates a process and all its child/descendant processes cross-platform.
    - On Windows: Uses `taskkill /T /PID <pid>` (with `/F` if force is True).
    - On POSIX: Uses `os.killpg` on the PGID, cleans up descendant PIDs,
      and falls back to `os.kill`.
    """
    if not pid or pid <= 0:
        return

    if IS_WINDOWS:
        try:
            cmd = ["taskkill"]
            if force:
                cmd.append("/F")
            cmd.extend(["/T", "/PID", str(pid)])
            subprocess.run(
                cmd,
                capture_output=True,
                check=False,
                timeout=5,
            )
        except Exception as e:
            log.warning(f"[process] taskkill failed for PID {pid}: {e}")
            try:
                # Windows os.kill only accepts SIGTERM / signal.CTRL_C_EVENT / CTRL_BREAK_EVENT
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        return

    # POSIX (Linux / macOS)
    sig = signal.SIGKILL if force else signal.SIGTERM

    # 1. Collect descendants via pgrep if available
    descendant_pids: List[int] = []
    try:
        out = subprocess.check_output(
            ["pgrep", "-P", str(pid)], text=True, timeout=2
        ).strip()
        if out:
            for p in out.split():
                try:
                    descendant_pids.append(int(p))
                    sub_out = subprocess.check_output(
                        ["pgrep", "-P", p], text=True, timeout=2
                    ).strip()
                    if sub_out:
                        descendant_pids.extend([int(sp) for sp in sub_out.split()])
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Terminate entire process group if possible (never kill our own group)
    killed_group = False
    if hasattr(os, "getpgid") and hasattr(os, "killpg"):
        try:
            pgid = os.getpgid(pid)
            my_pgid = os.getpgid(os.getpid())
            if pgid != my_pgid and pgid != os.getpid() and pgid > 1:
                os.killpg(pgid, sig)
                killed_group = True
        except ProcessLookupError:
            return
        except Exception as e:
            log.debug(f"[process] killpg failed for PID {pid}: {e}")

    # 3. Kill descendant PIDs directly
    for d_pid in descendant_pids:
        try:
            os.kill(d_pid, sig)
        except Exception:
            pass

    # 4. Fallback: kill target PID directly if killpg wasn't available or successful
    if not killed_group:
        try:
            os.kill(pid, sig)
        except Exception:
            pass
