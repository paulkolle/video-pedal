#!/usr/bin/env python3
"""Start or stop the video pedal process with one repeated launcher click."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


def build_command(project: Path, uv: str) -> list[str]:
    """Build the uv command used to run the loop pedal."""
    project = Path(project)
    return [
        str(uv),
        "run",
        "--with-requirements",
        str(project / "requirements.txt"),
        "--no-project",
        str(project / "loop_pedal.py"),
    ]


def process_command(pid: int) -> str:
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def process_is_target(pid: int, marker: str) -> bool:
    """Return true only when pid is alive and its command contains marker."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    return marker in process_command(pid)


def stop_process(pid: int, marker: str) -> None:
    """Stop a process group created by this launcher."""
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    for _ in range(40):
        if not process_is_target(pid, marker):
            return
        time.sleep(0.05)

    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def toggle(pid_file: Path, log_file: Path, command: list[str], marker: str, cwd: Path) -> str:
    """Toggle the command and return ``started`` or ``stopped``."""
    pid_file = Path(pid_file)
    log_file = Path(log_file)
    cwd = Path(cwd)
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
        except (OSError, ValueError):
            pid = 0
        if process_is_target(pid, marker):
            stop_process(pid, marker)
            pid_file.unlink(missing_ok=True)
            return "stopped"
        pid_file.unlink(missing_ok=True)

    with log_file.open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pid_file.write_text(str(process.pid) + "\n")
    return "started"


def main() -> int:
    project = Path(__file__).resolve().parent
    state_dir = Path.home() / "Library" / "Logs" / "video-pedal"
    uv = os.environ.get("VIDEO_PEDAL_UV") or shutil.which("uv") or "/opt/homebrew/bin/uv"
    command = build_command(project, uv)
    result = toggle(
        state_dir / "video-pedal.pid",
        state_dir / "launcher.log",
        command,
        str(project / "loop_pedal.py"),
        project,
    )
    print(f"video pedal {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
