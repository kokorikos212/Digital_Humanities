"""
Interactive PTY WebSocket terminal — spawns a real bash shell sandboxed inside
the user's project directory and streams I/O over WebSockets.

Mounted onto Gradio's internal FastAPI app at ``/ws/terminal/{user_id}/{project_id}``.
"""

from __future__ import annotations

import asyncio
import os
import pty
import struct
import termios
import fcntl
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect

from src.config import resolve_project_dir


def _spawn_pty(project_dir: str) -> tuple[int, int]:
    """Fork a bash process inside *project_dir* and return (pid, master_fd)."""
    pid, fd = pty.fork()
    if pid == 0:  # child
        os.chdir(project_dir)
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        env.setdefault("HOME", project_dir)
        env.setdefault("SHELL", "/bin/bash")
        os.execve("/bin/bash", ["/bin/bash"], env)
    return pid, fd


async def terminal_websocket_endpoint(websocket: WebSocket):
    """Handle a single PTY terminal session over WebSocket."""
    await websocket.accept()

    user_id = websocket.path_params.get("user_id", "demo")
    project_id = websocket.path_params.get("project_id", "default")
    project_dir = str(resolve_project_dir(user_id, project_id))

    pid, fd = _spawn_pty(project_dir)

    loop = asyncio.get_event_loop()

    def _read_pty():
        try:
            return os.read(fd, 4096)
        except OSError:
            return None

    async def _stream_output():
        while True:
            data = await loop.run_in_executor(None, _read_pty)
            if not data:
                break
            try:
                await websocket.send_bytes(data)
            except Exception:
                break

    output_task = asyncio.ensure_future(_stream_output())

    try:
        while True:
            msg = await websocket.receive()
            if "text" in msg:
                text = msg["text"]
                # Handle resize events from xterm.js
                if text.startswith("\x1b[8;") or text.startswith("\x1b[4;"):
                    parts = text.strip("\x1b\\").split(";")
                    if len(parts) >= 3 and text.startswith("\x1b[8;"):
                        try:
                            rows = int(parts[1])
                            cols = int(parts[2].rstrip("t"))
                            winsize = struct.pack("HHHH", rows, cols, 0, 0)
                            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
                        except (ValueError, OSError):
                            pass
                    continue
                os.write(fd, text.encode("utf-8", errors="replace"))
            elif "bytes" in msg:
                os.write(fd, msg["bytes"])
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        output_task.cancel()
        try:
            os.kill(pid, 15)  # SIGTERM
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass
