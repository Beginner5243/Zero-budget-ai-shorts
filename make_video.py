import asyncio
import json
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path

import edge_tts

OUTPUT_DIR = Path("output")
TMP = Path(tempfile.mkdtemp())

LANGS = {
    "en": {
        "voice": "en-US-GuyNeural",
        "font_query": "DejaVu Sans:bold",
        "font_fallback": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "wrap": 20,
    },
    "hi": {
        "voice": "hi-IN-MadhurNeural",
        "font_query": "Noto Sans Devanagari:bold",
        "font_fallback": "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        "wrap": 18,
    },
}


def find_font(query, fallback):
    try:
        out = subprocess.check_output(
            ["fc-match", "-f", "%{file}", query]).decode().strip()
        if out and Path(out).exists():
            return out
    except Exception:
        pass
    return fallback


async def make_audio(text, voice, path):
    await edge_tts.Communicate(text, voice).save(str(path))


def audio_duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return float(out.strip())


def build_filter(script, duration, font, wrap, tag):
    sentences = [s for s in re.split(r"(?<=[.!?।])\s+", script.strip()) if s]
    total = sum(len(s) for s in sentences) or 1
    parts, t = [], 0.0
    for k, s in enumerate(sentences):
        d = duration * len(s) / total
        tf = TMP / f"cap_{tag}_{k}.txt"
        tf.write_text(textwrap.fill(s, wrap), encoding="utf-8")
        parts.append(
            f"drawtext=fontfile={font}:textfile={tf}:expansion=none"
            ":fontcolor=white:fontsize=64:line_spacing=20"
            ":borderw=3:bordercolor=black"
            ":x=(w-text_w)/2:y=(h-text_h)/2"
            f":enable='between(t,{t:.2f},{t + d:.2f})'"
        )
        t += d
    return ",".join(parts)


def render(script, lang, name):
    cfg = LANGS[lang]
    font = find_font(cfg["font_query"], cfg["font_fallback"])
    print(f"[{name}] font: {font}")

    audio = OUTPUT_DIR / f"{name}.mp3"
    video = OUTPUT_DIR / f"{name}.mp4"

    asyncio.run(make_audio(script.replace("\n", " "), cfg["voice"], audio))
    dur = audio_duration(audio)
    vf = build_filter(script, dur, font, cfg["wrap"], name)

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x0b1d3a:s=1080x1920:d={dur + 0.5}:r=30",
        "-i", str(audio),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(video),
    ], check=True)
    print(f"Created {video} ({dur:.1f}s)")


def main():
    ideas = json.loads(
        (OUTPUT_DIR / "shorts_ideas.json").read_text(encoding="utf-8"))
    if not ideas:
        print("No ideas found, nothing to render.")
        return

    for i, idea in enumerate(ideas, start=1):
        for lang in ("en", "hi"):
            script = idea[lang]["script"]
            try:
                render(script, lang, f"short_{i}_{lang}")
            except Exception as error:
                print(f"short_{i}_{lang} failed: {error}")


if __name__ == "__main__":
    main()
