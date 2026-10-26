import asyncio
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import edge_tts

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
OUT = ROOT / "output"
WORK = ROOT / "work"

SCENES = [
    {
        "en": "A kingdom fell into darkness.",
        "hi": "Ek samrajya andhere mein doob gaya."
    },
    {
        "en": "But one warrior refused to kneel.",
        "hi": "Lekin ek yoddha jhuka nahi."
    },
    {
        "en": "The gods had chosen his fate.",
        "hi": "Devta uski kismat likh chuke the."
    },
    {
        "en": "Now he will challenge their power.",
        "hi": "Ab woh unki taakat ko chunauti dega."
    },
    {
        "en": "Someone rules from the shadows.",
        "hi": "Andhere mein koi aur raaj karta hai."
    },
    {
        "en": "No crown. No mercy. Only destiny.",
        "hi": "Na taaj. Na reham. Sirf kismat."
    }
]

def run(cmd):
    subprocess.run(cmd, check=True)

def get_font(size):
    for p in [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

async def voice(text, name, path):
    await edge_tts.Communicate(text, name).save(str(path))

def main():
    OUT.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)

    for i in range(1, 7):
        if not (ASSETS / f"scene{i:02d}.jpg").exists():
            raise FileNotFoundError(
                f"Missing assets/scene{i:02d}.jpg"
            )

    for lang, voice_name in [
        ("en", "en-US-GuyNeural"),
        ("hi", "hi-IN-SwaraNeural")
    ]:
        clips = []

        for i, scene in enumerate(SCENES, 1):
            img = Image.open(
                ASSETS / f"scene{i:02d}.jpg"
            ).convert("RGB")
            img = ImageOps.fit(img, (1080, 1920))
            draw = ImageDraw.Draw(img)

            draw.rectangle(
                (0, 1500, 1080, 1920), fill="black"
            )
            draw.text(
                (50, 1580), scene[lang],
                font=get_font(54), fill="white",
                stroke_width=2, stroke_fill="black"
            )

            frame = WORK / f"{lang}_{i:02d}.jpg"
            img.save(frame, quality=92)

            clip = WORK / f"{lang}_{i:02d}.mp4"
            run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-loop", "1", "-i", str(frame),
                "-vf",
                "zoompan=z='min(zoom+0.0005,1.05)':"
                "d=168:s=1080x1920:fps=24,"
                "format=yuv420p",
                "-t", "7", "-an",
                "-c:v", "libx264", "-preset", "ultrafast",
                str(clip)
            ])
            clips.append(clip)

        listing = WORK / f"{lang}_list.txt"
        listing.write_text(
            "".join(f"file '{p.resolve()}'\n" for p in clips)
        )

        silent = WORK / f"{lang}_silent.mp4"
        run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(listing), "-c", "copy", str(silent)
        ])

        narration = " ".join(s[lang] for s in SCENES)
        audio = WORK / f"{lang}_voice.mp3"
        asyncio.run(voice(narration, voice_name, audio))

        run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(silent), "-i", str(audio),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac",
            "-af", "apad", "-t", "42",
            "-shortest", str(OUT / f"crownless_{lang}.mp4")
        ])

    print("SUCCESS: Hindi and English trailers created!")

if __name__ == "__main__":
    main()
      
