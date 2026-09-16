#!/usr/bin/env python3
"""Generate crisp 144px state icons for the Video Pedal Stream Deck action."""

from __future__ import annotations

from pathlib import Path
import subprocess


OUT = Path(__file__).resolve().parent / "icons"


def svg(accent: str, label: str, symbol: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144" viewBox="0 0 144 144">
  <rect width="144" height="144" rx="22" fill="#101827"/>
  <rect x="5" y="5" width="134" height="134" rx="18" fill="none" stroke="#263449" stroke-width="3"/>
  <circle cx="24" cy="23" r="8" fill="{accent}"/>
  <rect x="28" y="46" width="72" height="52" rx="12" fill="none" stroke="#F4F7FB" stroke-width="7"/>
  <path d="M100 61 L122 50 Q127 48 127 54 V90 Q127 96 122 94 L100 83 Z" fill="none" stroke="#F4F7FB" stroke-width="7" stroke-linejoin="round"/>
  <circle cx="64" cy="72" r="15" fill="none" stroke="{accent}" stroke-width="6"/>
  {symbol}
  <rect x="17" y="112" width="110" height="22" rx="11" fill="{accent}"/>
  <text x="72" y="128" text-anchor="middle" fill="#101827" font-family="Verdana" font-size="13" font-weight="bold">{label}</text>
</svg>'''


ICONS = {
    "off": svg("#FF453A", "OFF", '<path d="M30 35 L112 109" stroke="#FF453A" stroke-width="8" stroke-linecap="round"/>'),
    "starting": svg("#AAB4C3", "START", '<circle cx="64" cy="72" r="25" fill="none" stroke="#AAB4C3" stroke-width="5" stroke-dasharray="8 8"/>'),
    "live": svg("#39D353", "LIVE", '<circle cx="64" cy="72" r="8" fill="#39D353"/>'),
    "rec": svg("#FF453A", "REC", '<circle cx="64" cy="72" r="8" fill="#FF453A"/><circle cx="64" cy="72" r="23" fill="none" stroke="#FF453A" stroke-width="3" opacity=".55"/>'),
    "loop": svg("#FFB020", "LOOP", '<path d="M42 61 A25 25 0 0 1 84 51" fill="none" stroke="#FFB020" stroke-width="6" stroke-linecap="round"/><path d="M84 51 L82 39 M84 51 L96 49" fill="none" stroke="#FFB020" stroke-width="6" stroke-linecap="round"/><path d="M86 83 A25 25 0 0 1 44 93" fill="none" stroke="#FFB020" stroke-width="6" stroke-linecap="round"/><path d="M44 93 L46 105 M44 93 L32 95" fill="none" stroke="#FFB020" stroke-width="6" stroke-linecap="round"/>'),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, markup in ICONS.items():
        svg_path = OUT / f"{name}.svg"
        png_path = OUT / f"{name}.png"
        svg_path.write_text(markup)
        subprocess.run(["convert", "-background", "none", "-font", "/System/Library/Fonts/Supplemental/Verdana Bold.ttf", str(svg_path), str(png_path)], check=True)
        print(png_path)


if __name__ == "__main__":
    main()
