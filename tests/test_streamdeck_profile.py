import copy
import json

import pytest

from repair_streamdeck_profile import clear_overrides, repair_profile


def profile():
    return {"Controllers": [{"Type": "Keypad", "Actions": {
        "3,1": {"UUID": "com.paul.video-pedal.toggle", "Settings": {"project": "/repo"},
                "States": [{"Image": "Images/VIDEO_PEDAL_OFF.png", "Title": "Video Pedal",
                            "FontSize": 12}]},
        "0,0": {"UUID": "other.action", "States": [{"Image": "keep.png", "Title": "Keep"}]},
    }}]}


def test_removes_only_video_pedal_image_and_title_overrides():
    document = profile()
    other = copy.deepcopy(document["Controllers"][0]["Actions"]["0,0"])
    assert clear_overrides(document) == 1
    actions = document["Controllers"][0]["Actions"]
    assert actions["3,1"]["States"] == [{"FontSize": 12}]
    assert actions["3,1"]["Settings"] == {"project": "/repo"}
    assert actions["0,0"] == other
    assert clear_overrides(document) == 0


def test_repair_preserves_exact_backup_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr("repair_streamdeck_profile.stream_deck_running", lambda: False)
    path = tmp_path / "manifest.json"
    original = json.dumps(profile()).encode()
    path.write_bytes(original)
    backup = repair_profile(path)
    assert backup.read_bytes() == original
    assert "Image" not in json.loads(path.read_text())["Controllers"][0]["Actions"]["3,1"]["States"][0]
    assert repair_profile(path) is None


def test_refuses_to_modify_profile_while_stream_deck_runs(tmp_path, monkeypatch):
    monkeypatch.setattr("repair_streamdeck_profile.stream_deck_running", lambda: True)
    path = tmp_path / "manifest.json"
    original = json.dumps(profile()).encode()
    path.write_bytes(original)
    with pytest.raises(RuntimeError, match="Quit Stream Deck"):
        repair_profile(path)
    assert path.read_bytes() == original
