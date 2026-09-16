#!/usr/bin/env python3
"""Print the pynput identity of every key pressed until Ctrl+C.

Use this when a physical key has no obvious pynput name, for example Fn on a
Windows keyboard connected to macOS. The printed suggestion can be copied to
loop_pedal.py's --key or --live-key option.
"""

from __future__ import annotations

import sys

from pynput import keyboard


MACOS_FN_VK = 0x3F


def configure_macos_fn() -> None:
    """Make pynput report macOS's Fn modifier as press/release events."""
    if sys.platform != "darwin":
        return
    try:
        import Quartz

        fn_flag = getattr(Quartz, "kCGEventFlagMaskSecondaryFn")
        fn = keyboard.KeyCode.from_vk(MACOS_FN_VK)
        modifier_flags = getattr(keyboard.Listener, "_MODIFIER_FLAGS")
        modifier_flags.setdefault(fn, fn_flag)
    except (ImportError, AttributeError):
        pass


def describe(key) -> tuple[str, str, str]:
    """Return (display name, virtual key code, character) for a pynput key."""
    value = key.value if isinstance(key, keyboard.Key) else key
    vk = getattr(value, "vk", None)
    char = getattr(value, "char", None)
    name = key.name if isinstance(key, keyboard.Key) else None
    return name or "KeyCode", "none" if vk is None else str(vk), repr(char)


def config_name(key, vk: str) -> str:
    if isinstance(key, keyboard.Key):
        return key.name
    if vk == str(MACOS_FN_VK) and sys.platform == "darwin":
        return "fn"
    char = getattr(key, "char", None)
    if char and len(char) == 1:
        return char
    return f"vk:{vk}"


def main() -> int:
    configure_macos_fn()
    print("Drücke die gewünschte Taste. Beenden: Ctrl+C")
    print("Jede Taste wird mit dem Namen für --key/--live-key ausgegeben.")
    print("Wenn Fn nichts ausgibt, wird sie von der Tastatur nicht an das OS weitergereicht.")

    def report(kind, key) -> None:
        name, vk, char = describe(key)
        spec = config_name(key, vk)
        print(f"{kind:7} name={name!r:16} vk={vk:>4} char={char:>6}  -> {spec}", flush=True)

    listener = keyboard.Listener(
        on_press=lambda key: report("press", key),
        on_release=lambda key: report("release", key),
    )
    listener.start()
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nBeendet.")
        listener.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
