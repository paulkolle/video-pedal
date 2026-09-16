import json

from video_pedal_status import OFF, LIVE, LOOPING, RECORDING, StatusWriter
from streamdeck_plugin.video_pedal_plugin import (
    ACTION_UUID,
    VideoPedalPlugin,
    display_status,
    parse_plugin_args,
    toggle_command,
)


def test_status_writer_publishes_mode_and_loop_timing(tmp_path):
    path = tmp_path / "state.json"
    writer = StatusWriter(path, pid=1234, clock=lambda: 100.0)

    writer.update(RECORDING, {"elapsed": 2.5, "total": 30.0, "progress": 0.08})

    payload = json.loads(path.read_text())
    assert payload == {
        "running": True,
        "pid": 1234,
        "mode": "REC",
        "elapsed": 2.5,
        "total": 30.0,
        "progress": 0.08,
        "updated_at": 100.0,
    }


def test_status_writer_marks_process_off(tmp_path):
    path = tmp_path / "state.json"
    writer = StatusWriter(path, pid=1234, clock=lambda: 100.0)

    writer.off()

    payload = json.loads(path.read_text())
    assert payload["running"] is False
    assert payload["mode"] == OFF
    assert payload["pid"] == 1234


def test_display_status_shows_loop_progress_and_recording_time():
    assert display_status(
        {"running": True, "mode": LOOPING, "elapsed": 3.2, "total": 8.0, "updated_at": 10},
        now=10,
    ) == ("LOOP", "LOOP 3.2/8.0s")
    assert display_status(
        {"running": True, "mode": RECORDING, "elapsed": 2.5, "updated_at": 10},
        now=10,
    ) == ("REC", "REC 2.5s")


def test_display_status_treats_missing_or_stale_status_as_off():
    assert display_status(None, now=10) == ("OFF", "Video Pedal")
    assert display_status(
        {"running": True, "mode": LIVE, "updated_at": 0},
        now=10,
    ) == ("OFF", "Video Pedal")


def test_parse_plugin_args_accepts_stream_deck_flagged_arguments():
    assert parse_plugin_args([
        "-port", "28196",
        "-pluginUUID", "instance-id",
        "-registerEvent", "registerPlugin",
        "-info", "{}",
    ]) == (28196, "instance-id", "registerPlugin")


def test_plugin_renders_icon_and_title_for_a_visible_action(tmp_path):
    class FakeWebSocket:
        sock = object()

        def __init__(self):
            self.messages = []

        def send_json(self, message):
            self.messages.append(message)

    status_path = tmp_path / "state.json"
    status_path.write_text(json.dumps({
        "running": True,
        "mode": LOOPING,
        "elapsed": 3.2,
        "total": 8.0,
        "updated_at": 10,
    }))
    ws = FakeWebSocket()
    plugin = VideoPedalPlugin(ws, status_path=status_path, clock=lambda: 10)

    plugin.handle({"event": "willAppear", "action": ACTION_UUID, "context": "ctx"})

    assert ws.messages[0]["event"] == "setImage"
    assert ws.messages[0]["payload"]["image"].startswith("data:image/png;base64,")
    assert ws.messages[1]["event"] == "setTitle"
    assert ws.messages[1]["payload"]["title"] == "LOOP 3.2/8.0s"


def test_toggle_uses_the_camera_authorized_launcher_app(tmp_path):
    launcher = tmp_path / "Video Pedal.app"
    launcher.mkdir()

    assert toggle_command({"launcher": str(launcher)}, tmp_path) == [
        "open", "-a", str(launcher)
    ]


def test_key_down_registers_context_even_if_will_appear_was_missed(tmp_path):
    class FakeWebSocket:
        sock = object()

        def __init__(self):
            self.messages = []

        def send_json(self, message):
            self.messages.append(message)

    status_path = tmp_path / "state.json"
    status_path.write_text(json.dumps({"running": False, "mode": OFF, "updated_at": 10}))
    ws = FakeWebSocket()
    plugin = VideoPedalPlugin(ws, status_path=status_path, clock=lambda: 10)
    plugin.toggle = lambda _settings: None

    plugin.handle({"event": "keyDown", "action": ACTION_UUID, "context": "ctx"})

    assert "ctx" in plugin.contexts
    assert ws.messages[-1]["event"] == "setTitle"
