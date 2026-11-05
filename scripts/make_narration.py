"""Generate narration clips for the demo video with macOS `say`.

Writes submission/video/audio/<scene>.aiff and durations.json.
Usage: python3 scripts/make_narration.py [--voice Daniel] [--rate 150]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

V = Path(__file__).resolve().parents[1] / "submission" / "video"
# spoken forms for words the synthesiser mispronounces
SPOKEN = {"GnuCOBOL": "G N U COBOL", "FastAPI": "Fast A P I", "COBOL Phoenix": "COBOL Phoenix"}
PAUSE_MS = 380  # pause after each sentence


def spoken(text: str) -> str:
    for k, v in SPOKEN.items():
        text = text.replace(k, v)
    return re.sub(r"([.?!:])\s+", rf"\1 [[slnc {PAUSE_MS}]] ", text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Daniel")
    ap.add_argument("--rate", type=int, default=150)
    a = ap.parse_args()
    (V / "audio").mkdir(exist_ok=True)
    durations = {}
    for s in json.loads((V / "narration.json").read_text()):
        out = V / "audio" / f"{s['id']}.aiff"
        subprocess.run(["say", "-v", a.voice, "-r", str(a.rate), "-o", str(out), spoken(s["text"])], check=True)
        d = float(subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout)
        durations[s["id"]] = d
        print(f"{s['id']}: {d:.1f}s")
    (V / "durations.json").write_text(json.dumps(durations, indent=1))
    print(f"total narration {sum(durations.values()):.1f}s ({a.voice}, {a.rate} wpm)")


if __name__ == "__main__":
    main()
