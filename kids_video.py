"""Kids Hindi cartoon video: render MP4 (images + Hindi voice + captions)."""

import asyncio
import io
import json
import math
import subprocess
import tempfile
import textwrap
from pathlib import Path
from urllib.parse import quote

import edge_tts
import requests
from PIL import Image, ImageDraw, ImageFont

OUT = Path("output_kids")
TMP = Path(tempfile.mkdtemp())
VOICE = "hi-IN-SwaraNeural"
W, H = 1620, 2880
STYLE = ("cute kawaii cartoon, children's picture book illustration, "
         "soft pastel colors, simple clean background, big friendly eyes, "
         "no text, no letters")
PALETTES = [
    ((255, 214, 224), (255, 240, 200)),
    ((200, 235, 255), (230, 255, 220)),
    ((255, 235, 180), (255, 200, 200)),
    ((220, 210, 255), (200, 245, 255)),
]


def fc_file(query, fallback=None):
    try:
        p = subprocess.check_output(
            ["fc-match", "-f", "%{file}", query]).decode().strip()
        if p and Path(p).exists():
            return p
    except Exception:
        pass
    return fallback


FONT = fc_file("Noto Sans Devanagari:bold",
               "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf")
EMOJI_FONT = fc_file("Noto Color Emoji")


def cover_crop(img):
    img = img.convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((math.ceil(img.width * scale), math.ceil(img.height * scale)),
                     Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((left, top, left + W, top + H))


def ai_image(prompt, seed):
    url = ("https://image.pollinations.ai/prompt/"
           f"{quote(prompt + ', ' + STYLE)}"
           f"?width=720&height=1280&nologo=true&seed={seed}")
    for attempt in range(2):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 5000:
                return cover_crop(Image.open(io.BytesIO(r.content)))
            print(f"image try {attempt + 1}: status {r.status_code}")
        except Exception as error:
            print(f"image try {attempt + 1} error: {error}")
    return None


def emoji_card(emoji, seed):
    top, bottom = PALETTES[seed % len(PALETTES)]
    grad = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / (H - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t)
                                    for i in range(3)))
    img = grad.resize((W, H))
    if EMOJI_FONT:
        try:
            f = ImageFont.truetype(EMOJI_FONT, 109)
            tile = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
            ImageDraw.Draw(tile).text((0, 0), emoji, font=f, embedded_color=True)
            size = 1150
            tile = tile.resize((size, int(size * 128 / 136)), Image.LANCZOS)
            img.paste(tile, ((W - size) // 2, 760), tile)
        except Exception as error:
            print(f"emoji error: {error}")
    return img


async def make_audio(text, path):
    await edge_tts.Communicate(text, VOICE, rate="-10%", pitch="+4Hz").save(str(path))


def duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(out.strip())


def render_scene(i, scene, seed):
    text = scene["text"].strip()
    img_path, aud, vid = TMP / f"s{i}.jpg", TMP / f"s{i}.mp3", TMP / f"s{i}.mp4"
    cap = TMP / f"cap{i}.txt"

    img = ai_image(scene["image_prompt"], seed + i)
    print(f"scene {i}: {'AI image' if img else 'emoji card'}")
    if img is None:
        img = emoji_card(scene.get("emoji") or "🐾", seed + i)
    img.save(img_path, quality=92)

    asyncio.run(make_audio(text, aud))
    dur = duration(aud) + 0.5
    frames = int(dur * 30)

    cap.write_text(textwrap.fill(text, 16), encoding="utf-8")
    vf = (
        f"zoompan=z='min(zoom+0.0006,1.12)'"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s=1080x1920:fps=30,"
        f"drawtext=fontfile={FONT}:textfile={cap}:expansion=none"
        ":fontcolor=white:fontsize=72:line_spacing=18"
        ":box=1:boxcolor=black@0.45:boxborderw=26"
        ":x=(w-text_w)/2:y=h*0.72,format=yuv420p"
    )
    subprocess.run([
        "ffmpeg", "-y", "-i", str(img_path), "-i", str(aud),
        "-vf", vf, "-af", "apad", "-t", f"{dur:.2f}",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-r", "30",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", str(vid),
    ], check=True)
    return vid


def main():
    data = json.loads((OUT / "kids_script.json").read_text(encoding="utf-8"))
    seed = sum(ord(c) for c in data["title"]) % 1000
    clips = []
    for i, scene in enumerate(data["scenes"]):
        try:
            clips.append(render_scene(i, scene, seed))
        except Exception as error:
            print(f"scene {i} failed: {error}")

    if not clips:
        raise SystemExit("No scenes rendered")

    lst = TMP / "list.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips), encoding="utf-8")
    final = OUT / f"kids_{data.get('format', 'video')}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(final)], check=True)
    print(f"Created {final} ({duration(final):.1f}s, {len(clips)} scenes)")


if __name__ == "__main__":
    main()
