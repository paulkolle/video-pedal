#!/usr/bin/env python3
"""Remove static Video Pedal overrides from one explicitly selected profile page."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ACTION_UUID = "com.paul.video-pedal.toggle"


def clear_overrides(document: dict) -> int:
    """Preserve settings and other actions; let the plugin own image and title."""
    changed = 0
    for controller in document.get("Controllers", []):
        for action in controller.get("Actions", {}).values():
            if action.get("UUID") != ACTION_UUID:
                continue
            for state in action.get("States", []):
                if "Image" in state or "Title" in state:
                    changed += 1
                    state.pop("Image", None)
                    state.pop("Title", None)
    return changed


def stream_deck_running() -> bool:
    # Fail closed if process inspection is unavailable (e.g. in a sandbox).
    result = subprocess.run(["ps", "-ax", "-o", "comm="], check=True,
                            capture_output=True, text=True)
    return any(line.strip().endswith("/Contents/MacOS/Stream Deck")
               for line in result.stdout.splitlines())


def repair_profile(path: Path) -> Path | None:
    if stream_deck_running():
        raise RuntimeError("Quit Stream Deck completely before repairing its profile.")
    path = Path(path).resolve(strict=True)
    document = json.loads(path.read_text())
    if not clear_overrides(document):
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(f"{path.name}.video-pedal-{stamp}.bak")
    shutil.copy2(path, backup)
    fd, temporary = tempfile.mkstemp(prefix=".video-pedal-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(document, handle, indent=4, ensure_ascii=False)
            handle.write("\n")
        shutil.copymode(path, temporary)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return backup


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Profile page manifest.json (not the plugin manifest)")
    args = parser.parse_args()
    backup = repair_profile(args.manifest)
    print(f"Repaired; backup: {backup}" if backup else "No Video Pedal overrides to remove.")


if __name__ == "__main__":
    main()
