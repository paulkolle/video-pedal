import sys
import time

from toggle_video_pedal import build_command, process_is_target, toggle


def test_build_command_runs_loop_pedal_through_uv(tmp_path):
    command = build_command(tmp_path, "/opt/homebrew/bin/uv")
    assert command == [
        "/opt/homebrew/bin/uv",
        "run",
        "--with-requirements",
        str(tmp_path / "requirements.txt"),
        "--no-project",
        str(tmp_path / "loop_pedal.py"),
    ]


def test_toggle_starts_then_stops_the_recorded_process(tmp_path):
    pid_file = tmp_path / "video-pedal.pid"
    log_file = tmp_path / "video-pedal.log"
    command = [sys.executable, "-c", "import time; time.sleep(60)  # toggle-marker"]

    try:
        assert toggle(pid_file, log_file, command, "toggle-marker", tmp_path) == "started"
        pid = int(pid_file.read_text())
        assert process_is_target(pid, "toggle-marker")

        assert toggle(pid_file, log_file, command, "toggle-marker", tmp_path) == "stopped"
        for _ in range(20):
            if not process_is_target(pid, "toggle-marker"):
                break
            time.sleep(0.05)
        assert not process_is_target(pid, "toggle-marker")
        assert not pid_file.exists()
    finally:
        if pid_file.exists():
            pid_file.unlink()
