"""
Zero-Budget AI Shorts Automation
Main entry point
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from fact_checker import verify_fact


OUTPUT_DIR = Path("output")
API_KEY = os.environ.get("GEMINI_API_KEY", "")
API_BASE = "https://generativelanguage.googleapis.com/v1beta"
PREFERRED_MODELS = ["gemini-3.8-flash"]
MAX_TOPICS = 2
REQUIRED_KEYS = ("title_en", "script_en", "title_hi", "script_hi")

# Wikipedia-friendly names of topics that make good "wow" Shorts.
WOW_TOPICS = [
    "Mariana Trench", "Octopus", "Black hole", "Bermuda Triangle",
    "Tardigrade", "Great Blue Hole", "Voyager 1", "Tunguska event",
    "Antikythera mechanism", "Lake Natron", "Anglerfish",
    "Turritopsis dohrnii", "Neutron star", "Aurora", "Lightning",
    "Great Pyramid of Giza", "Dead Sea", "Amazon rainforest",
    "Honey bee", "Mount Everest", "Sahara", "Human brain",
    "Platypus", "Pluto", "Saturn", "Jupiter", "Sun", "Moon",
    "Deep Sea", "Great Barrier Reef", "Baikal", "Yellowstone Caldera",
    "Mantis shrimp", "Axolotl", "Blue whale", "Giant squid",
    "Chernobyl disaster", "International Space Station",
    "Rosetta Stone", "Stonehenge", "Fibonacci sequence",
    "Speed of light", "DNA", "Photosynthesis", "Gravity",
]


def pick_topics():
    """Pick different topics every day, without any API."""
    n = len(WOW_TOPICS)
    start = (datetime.now(timezone.utc).toordinal() * MAX_TOPICS) % n
    return [WOW_TOPICS[(start + i) % n] for i in range(MAX_TOPICS)]


def list_flash_models():
    """Ask Google which flash models this key can use right now."""
    try:
        r = requests.get(
            f"{API_BASE}/models",
            headers={"x-goog-api-key": API_KEY},
            params={"pageSize": 100},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"list models failed: {r.status_code}")
            return []
        names = []
        for m in r.json().get("models", []):
            name = m.get("name", "").split("/")[-1]
            methods = m.get("supportedGenerationMethods", [])
            if ("generateContent" in methods and "flash" in name
                    and not any(x in name for x in
                                ("image", "tts", "live", "audio", "thinking"))):
                names.append(name)
        return sorted(names, reverse=True)
    except Exception as error:
        print(f"list models error: {error}")
        return []


def try_model(model, prompt):
    url = f"{API_BASE}/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.7,
        },
    }
    headers = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=headers, json=body, timeout=90)
        if r.status_code != 200:
            print(f"{model} failed: {r.status_code} {r.text[:150]}")
            return None
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip().strip("`")
        if text.startswith("json"):
            text = text[4:]
        data = json.loads(text)
        if all(isinstance(data.get(k), str) and data.get(k)
               for k in REQUIRED_KEYS):
            print(f"Script made with {model}")
            return data
        print(f"{model}: JSON keys missing")
    except Exception as error:
        print(f"{model} error: {error}")
    return None


def call_gemini(prompt):
    if not API_KEY:
        print("GEMINI_API_KEY missing")
        return None

    for model in PREFERRED_MODELS:
        data = try_model(model, prompt)
        if data:
            return data

    for model in list_flash_models()[:3]:
        if model in PREFERRED_MODELS:
            continue
        data = try_model(model, prompt)
        if data:
            return data
    return None


def fallback_scripts(topic):
    return {
        "title_en": f"Amazing fact about {topic}",
        "script_en": (
            f"Did you know this about {topic}? "
            f"There is more to {topic} than most people realise. "
            "Follow for more amazing facts."
        ),
        "title_hi": "हैरान करने वाला तथ्य",
        "script_hi": (
            "क्या आप यह जानते हैं? "
            "इसमें बहुत कुछ ऐसा है जो ज्यादातर लोग नहीं जानते। "
            "ऐसे और तथ्यों के लिए फॉलो करें।"
        ),
    }


def generate_scripts(topic, verification):
    notes = str(verification)[:800]
    prompt = f"""You write viral YouTube Shorts scripts for a science and mystery facts channel.
Topic: {topic}
Reference notes (may be incomplete): {notes}

Rules:
- Pick the single most surprising, TRUE fact about the topic. Never invent numbers, names or dates.
- First sentence is a shocking hook, under 12 words.
- 6 to 8 short sentences, about 70 to 85 words in total (30 to 35 seconds when spoken).
- Use simple everyday spoken words, like talking to a friend. No flowery or poetic language.
- No emojis, no hashtags, no stage directions.
- Last sentence: ask the viewer to follow for more amazing facts.

Return ONLY JSON with exactly these keys:
title_en, script_en, title_hi, script_hi
title is a catchy title under 60 characters.
script_hi is the same story written naturally in simple spoken Hindi (Devanagari script)."""
    return call_gemini(prompt) or fallback_scripts(topic)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=== Zero-Budget AI Shorts Creator ===")
    topics = pick_topics()
    print(f"Today's topics: {topics}")

    results = []

    for topic in topics:
        print(f"Processing: {topic}")
        try:
            verification = verify_fact(topic)
        except Exception as error:
            verification = {"verified": False, "message": str(error)}

        scripts = generate_scripts(topic, verification)
        results.append({
            "topic": topic,
            "verification": verification,
            "en": {"title": scripts["title_en"], "script": scripts["script_en"]},
            "hi": {"title": scripts["title_hi"], "script": scripts["script_hi"]},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    out_file = OUTPUT_DIR / "shorts_ideas.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"Saved {len(results)} ideas to {out_file}")


if __name__ == "__main__":
    main()
