#!/usr/bin/env python3
"""Stream Deck action that toggles Video Pedal and mirrors its state."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import select
import socket
import subprocess
import sys
import time
from typing import Any

ACTION_UUID = "com.paul.video-pedal.toggle"
DEFAULT_PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_LAUNCHER = Path.home() / "Applications" / "Video Pedal.app"
ICON_NAMES = {"OFF": "off", "STARTING": "starting", "LIVE": "live", "REC": "rec", "LOOP": "loop"}
STALE_AFTER = 2.5


def default_status_path() -> Path:
    return Path.home() / "Library" / "Logs" / "video-pedal" / "state.json"


def display_status(payload: dict[str, Any] | None, now: float | None = None) -> tuple[str, str]:
    """Return (icon state, title) for a status snapshot."""
    if now is None:
        now = time.time()
    if not payload or not payload.get("running"):
        return "OFF", "Video Pedal"
    try:
        stale = now - float(payload["updated_at"]) > STALE_AFTER
    except (KeyError, TypeError, ValueError):
        stale = True
    if stale:
        return "OFF", "Video Pedal"

    mode = payload.get("mode")
    if mode == "LIVE":
        return "LIVE", "LIVE"
    if mode == "REC":
        elapsed = payload.get("elapsed")
        return "REC", f"REC {float(elapsed):.1f}s" if elapsed is not None else "REC"
    if mode == "LOOP":
        elapsed = payload.get("elapsed")
        total = payload.get("total")
        if elapsed is not None and total is not None:
            return "LOOP", f"LOOP {float(elapsed):.1f}/{float(total):.1f}s"
        return "LOOP", "LOOP"
    if mode == "STARTING":
        return "STARTING", "START..."
    return "OFF", "Video Pedal"


def read_status(path: Path | str | None = None) -> dict[str, Any] | None:
    try:
        return json.loads((Path(path) if path else default_status_path()).read_text())
    except (OSError, ValueError):
        return None


def toggle_command(settings: dict[str, Any], project: Path = DEFAULT_PROJECT) -> list[str]:
    """Use the camera-authorized app launcher on macOS."""
    launcher = Path(settings.get("launcher", DEFAULT_LAUNCHER))
    if launcher.exists():
        return ["open", "-a", str(launcher)]
    return [sys.executable, str(Path(project) / "toggle_video_pedal.py")]


class WebSocket:
    """Minimal RFC 6455 client; the Stream Deck protocol needs text frames only."""

    def __init__(self, sock: socket.socket, buffered: bytes = b""):
        self.sock = sock
        self._buffer = bytearray(buffered)

    @classmethod
    def connect(cls, port: int) -> "WebSocket":
        sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        key = base64.b64encode(b"video-pedal-deck").decode()
        request = (
            f"GET / HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
        sock.sendall(request)
        response = b""
        while b"\r\n\r\n" not in response:
            response += sock.recv(4096)
        if not response.startswith(b"HTTP/1.1 101"):
            raise RuntimeError(f"Stream Deck websocket handshake failed: {response[:100]!r}")
        sock.settimeout(None)
        header_end = response.index(b"\r\n\r\n") + 4
        return cls(sock, response[header_end:])

    def send_json(self, message: dict[str, Any]) -> None:
        self._send_frame(json.dumps(message, separators=(",", ":")).encode())

    def has_buffered_data(self) -> bool:
        return bool(self._buffer)

    def receive_json(self) -> dict[str, Any] | None:
        opcode, payload = self._receive_frame()
        if opcode == 8:
            raise EOFError(f"Stream Deck websocket closed: {payload!r}")
        if opcode == 9:
            self._send_frame(payload, opcode=10)
            return None
        if opcode != 1:
            return None
        return json.loads(payload.decode())

    def _send_frame(self, payload: bytes, opcode: int = 1) -> None:
        length = len(payload)
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.extend((0x80 | 126).to_bytes(1, "big"))
            header.extend(length.to_bytes(2, "big"))
        else:
            header.extend((0x80 | 127).to_bytes(1, "big"))
            header.extend(length.to_bytes(8, "big"))
        mask = b"VPDk"
        header.extend(mask)
        header.extend(bytes(value ^ mask[index % 4] for index, value in enumerate(payload)))
        self.sock.sendall(header)

    def _receive_frame(self) -> tuple[int, bytes]:
        first, second = self._receive_exact(2)
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = int.from_bytes(self._receive_exact(2), "big")
        elif length == 127:
            length = int.from_bytes(self._receive_exact(8), "big")
        mask = self._receive_exact(4) if second & 0x80 else None
        payload = self._receive_exact(length)
        if mask:
            payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        return opcode, payload

    def _receive_exact(self, length: int) -> bytes:
        data = bytearray()
        if self._buffer:
            take = min(length, len(self._buffer))
            data.extend(self._buffer[:take])
            del self._buffer[:take]
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk:
                raise EOFError("Stream Deck websocket closed")
            data.extend(chunk)
        return bytes(data)


def image_data(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


class VideoPedalPlugin:
    def __init__(self, ws: WebSocket, project: Path = DEFAULT_PROJECT,
                 status_path: Path | None = None, clock=time.time):
        self.ws = ws
        self.project = project
        self.status_path = status_path or default_status_path()
        self.clock = clock
        self.contexts: set[str] = set()
        self.settings: dict[str, dict[str, Any]] = {}
        self.rendered: dict[str, tuple[str, str]] = {}
        self.icons = Path(__file__).resolve().parent / "icons"

    def run(self) -> None:
        next_poll = 0.0
        while True:
            readable = self.ws.has_buffered_data() or bool(select.select([self.ws.sock], [], [], 0.25)[0])
            if readable:
                message = self.ws.receive_json()
                if message:
                    self.handle(message)
            now = self.clock()
            if now >= next_poll:
                self.render_all()
                next_poll = now + 0.25

    def handle(self, message: dict[str, Any]) -> None:
        event = message.get("event")
        context = message.get("context")
        self.log(f"event={event} action={message.get('action')} context={context}")
        if event == "willAppear" and message.get("action") == ACTION_UUID and context:
            self.contexts.add(context)
            self.settings[context] = message.get("payload", {}).get("settings", {})
            self.render(context, force=True)
        elif event == "willDisappear" and context:
            self.contexts.discard(context)
            self.settings.pop(context, None)
            self.rendered.pop(context, None)
        elif event == "keyDown" and message.get("action") == ACTION_UUID:
            if context:
                self.contexts.add(context)
            self.toggle(self.settings.get(context or "", {}))
            self.render_all(force=True)

    def toggle(self, settings: dict[str, Any]) -> None:
        project = Path(settings.get("project", self.project))
        script = project / "toggle_video_pedal.py"
        command = toggle_command(settings, project)
        if command[0] != "open" and not script.exists():
            self.log(f"toggle script not found: {script}")
            return
        result = subprocess.run(command, cwd=project, check=False,
                                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        self.log(f"toggle command exited {result.returncode}: {command[0]}")

    def render_all(self, force: bool = False) -> None:
        for context in list(self.contexts):
            self.render(context, force=force)

    def render(self, context: str, force: bool = False) -> None:
        state, title = display_status(read_status(self.status_path), now=self.clock())
        rendered = (state, title)
        if not force and self.rendered.get(context) == rendered:
            return
        self.rendered[context] = rendered
        image = self.icons / f"{ICON_NAMES.get(state, 'off')}.png"
        if not image.exists():
            image = self.icons / "off.png"
        self.log(f"render context={context} state={state} title={title} image={image.name}")
        self.ws.send_json({
            "event": "setImage",
            "context": context,
            "payload": {"image": image_data(image), "target": 0},
        })
        self.ws.send_json({
            "event": "setTitle",
            "context": context,
            "payload": {"title": title, "target": 0},
        })

    def log(self, message: str) -> None:
        log = self.status_path.parent / "streamdeck-plugin.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as handle:
            handle.write(message + "\n")


def parse_plugin_args(argv: list[str]) -> tuple[int, str, str]:
    """Parse the flag-style arguments used by Stream Deck 7.x."""
    values: dict[str, str] = {}
    index = 0
    while index + 1 < len(argv):
        if argv[index].startswith("-"):
            values[argv[index].lstrip("-")] = argv[index + 1]
            index += 2
        else:
            index += 1
    try:
        return int(values["port"]), values["pluginUUID"], values["registerEvent"]
    except (KeyError, ValueError) as exc:
        raise ValueError("Stream Deck arguments need -port, -pluginUUID, and -registerEvent") from exc


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: video_pedal_plugin.py -port <port> -pluginUUID <uuid> -registerEvent <event>", file=sys.stderr)
        return 2
    try:
        port, plugin_uuid, register_event = parse_plugin_args(argv)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    ws = WebSocket.connect(port)
    ws.send_json({"event": register_event, "uuid": plugin_uuid})
    plugin = VideoPedalPlugin(ws)
    try:
        plugin.run()
    except (EOFError, OSError, KeyboardInterrupt) as exc:
        plugin.log(f"plugin connection ended: {type(exc).__name__}: {exc}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
