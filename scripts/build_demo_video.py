"""Assemble submission/video/cobol-phoenix-demo.mp4 from the Playwright recording,
the text-to-speech narration clips and scenes.json (written by e2e/record-demo.spec.ts)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

V = Path(__file__).resolve().parents[1] / "submission" / "video"
LEAD = 0.4  # seconds between scene start and narration


def ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def main() -> None:
    narration = {n["id"]: n["text"] for n in json.loads((V / "narration.json").read_text())}
    durations = json.loads((V / "durations.json").read_text())
    scenes = json.loads((V / "scenes.json").read_text())
    srt, inputs, filters, labels = [], [], [], []
    for i, sc in enumerate(scenes["scenes"], start=1):
        start = sc["start"] + LEAD
        inputs += ["-i", str(V / "audio" / f"{sc['id']}.aiff")]
        filters.append(f"[{i}:a]adelay={int(start * 1000)}|{int(start * 1000)}[a{i}]")
        labels.append(f"[a{i}]")
        # split long narration into two subtitle cues
        words = narration[sc["id"]].split()
        half = len(words) // 2 if len(words) > 22 else len(words)
        parts = [" ".join(words[:half]), " ".join(words[half:])] if half < len(words) else [" ".join(words)]
        d = durations[sc["id"]]
        for k, p in enumerate(parts):
            a = start + d * k / len(parts)
            b = start + d * (k + 1) / len(parts)
            srt.append(f"{len(srt) + 1}\n{ts(a)} --> {ts(b)}\n{p}\n")
    (V / "cobol-phoenix-demo.srt").write_text("\n".join(srt))
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,apad[aout]")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(V / "raw-recording.webm"), *inputs,
        "-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", str(V / "cobol-phoenix-demo.mp4"),
    ]  # fmt: skip
    subprocess.run(cmd, check=True)
    print("wrote", V / "cobol-phoenix-demo.mp4", "and", V / "cobol-phoenix-demo.srt")


if __name__ == "__main__":
    main()
