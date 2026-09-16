"""Publish the video pedal state for local integrations such as Stream Deck."""

from __future__ import annotations

import json
import os
from pathlib import Path
import time


OFF, STARTING, LIVE, RECORDING, LOOPING = "OFF", "STARTING", "LIVE", "REC", "LOOP"


def default_status_path() -> Path:
    return Path.home() / "Library" / "Logs" / "video-pedal" / "state.json"


class StatusWriter:
    """Write a small, atomically replaced status snapshot."""

    def __init__(self, path: Path | str | None = None, pid: int | None = None, clock=time.time):
        self.path = Path(path) if path is not None else default_status_path()
        self.pid = pid if pid is not None else os.getpid()
        self._clock = clock

    def update(self, mode: str, info: dict | None = None) -> None:
        info = info or {}
        payload = {
            "running": True,
            "pid": self.pid,
            "mode": mode,
            "elapsed": info.get("elapsed"),
            "total": info.get("total"),
            "progress": info.get("progress"),
            "updated_at": self._clock(),
        }
        self._write(payload)

    def off(self) -> None:
        self._write({
            "running": False,
            "pid": self.pid,
            "mode": OFF,
            "elapsed": None,
            "total": None,
            "progress": None,
            "updated_at": self._clock(),
        })

    def _write(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{self.pid}.tmp")
        temporary.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
        os.replace(temporary, self.path)
