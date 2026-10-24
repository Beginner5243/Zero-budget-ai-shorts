import asyncio
import json
import subprocess
import textwrap
from pathlib import Path

import edge_tts

OUTPUT_DIR = Path("output")
VOICE = "en-US-GuyNeural"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


async def make_audio(text, path):
    await edge_tts.Communicate(text, VOICE).save(str(path))


def audio_duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return float(out.strip())


def main():
    ideas_file = OUTPUT_DIR / "shorts_ideas.json"
    ideas = json.loads(ideas_file.read_text(encoding="utf-8"))

    if not ideas:
        print("No ideas found, nothing to render.")
        return

    for i, idea in enumerate(ideas[:2], start=1):
        script = idea["script"]
        audio = OUTPUT_DIR / f"voice_{i}.mp3"
        textfile = OUTPUT_DIR / f"text_{i}.txt"
        video = OUTPUT_DIR / f"short_{i}.mp4"

        asyncio.run(make_audio(script.replace("\n", " "), audio))
        duration = audio_duration(audio) + 0.5

        wrapped = "\n".join(
            textwrap.fill(p, 24) for p in script.split("\n\n")
        )
        textfile.write_text(wrapped.replace("\n\n", "\n\n"), encoding="utf-8")

        vf = (
            f"drawtext=fontfile={FONT}:textfile={textfile}"
            ":fontcolor=white:fontsize=64:line_spacing=18"
            ":x=(w-text_w)/2:y=(h-text_h)/2"
        )
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x101830:s=1080x1920:d={duration}:r=30",
            "-i", str(audio),
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(video),
        ], check=True)
        print(f"Created {video}")


if __name__ == "__main__":
    main()
