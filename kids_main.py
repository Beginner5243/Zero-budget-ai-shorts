"""Kids Hindi cartoon video: script generator (Gemini)."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

OUT = Path("output_kids")
API_KEY = os.environ.get("GEMINI_API_KEY", "")
API_BASE = "https://generativelanguage.googleapis.com/v1beta"
PREFERRED_MODELS = ["gemini-3.8-flash"]

ANIMALS = [
    "dog", "cat", "cow", "duck", "elephant", "lion", "monkey", "rabbit",
    "horse", "sheep", "frog", "parrot", "goat", "tiger", "bear", "penguin",
    "fish", "bee", "pig", "owl", "giraffe", "zebra", "deer", "peacock",
]
LEARNING = [
    "counting 1 to 5 with animals", "counting 6 to 10 with animals",
    "five basic colors with animals", "Hindi vowels अ आ इ ई उ with animal names",
    "big and small with animals", "fruits and their colors",
]
ORDER = ["animals", "story", "rhyme", "learning"]

FORMAT_RULES = {
    "animals": (
        "Teach 3 animals: for each give its Hindi name, the sound it makes "
        "(like भौं भौं), and one very simple TRUE fun fact for a small child. "
        "Animals today: {animals}. End by asking the child which one they liked."
    ),
    "story": (
        "Tell a very short original story with 2 cute animal characters and a "
        "gentle moral (sharing, honesty, kindness or helping). Characters today: "
        "{animals}. Happy ending. Nothing scary."
    ),
    "rhyme": (
        "Write an ORIGINAL short rhyming poem (do not copy any existing nursery "
        "rhyme) with 4 verses of 2 lines each about: {animals}. Simple, bouncy, "
        "repeating words. Each verse is one scene."
    ),
    "learning": (
        "Teach: {learning}. Use cute animals as examples. One idea per scene, "
        "repeat the key word. End by asking the child to say it again."
    ),
}


def pick_format():
    f = os.environ.get("KIDS_FORMAT", "auto").strip().lower()
    if f in FORMAT_RULES:
        return f
    return ORDER[datetime.now(timezone.utc).toordinal() % len(ORDER)]


def pick_seed():
    day = datetime.now(timezone.utc).toordinal()
    animals = [ANIMALS[(day * 3 + i) % len(ANIMALS)] for i in range(3)]
    return ", ".join(animals), LEARNING[day % len(LEARNING)]


def list_flash_models():
    try:
        r = requests.get(f"{API_BASE}/models",
                         headers={"x-goog-api-key": API_KEY},
                         params={"pageSize": 100}, timeout=30)
        if r.status_code != 200:
            return []
        names = []
        for m in r.json().get("models", []):
            n = m.get("name", "").split("/")[-1]
            if ("generateContent" in m.get("supportedGenerationMethods", [])
                    and "flash" in n
                    and not any(x in n for x in
                                ("image", "tts", "live", "audio", "thinking"))):
                names.append(n)
        return sorted(names, reverse=True)
    except Exception as error:
        print(f"list models error: {error}")
        return []


def valid(data):
    sc = data.get("scenes") if isinstance(data, dict) else None
    if not isinstance(sc, list) or len(sc) < 3:
        return False
    return all(isinstance(s, dict) and s.get("text") and s.get("image_prompt")
               for s in sc) and bool(data.get("title"))


def try_model(model, prompt):
    url = f"{API_BASE}/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "temperature": 0.8},
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
        if valid(data):
            print(f"Script made with {model}")
            return data
        print(f"{model}: bad JSON shape")
    except Exception as error:
        print(f"{model} error: {error}")
    return None


def call_gemini(prompt):
    if not API_KEY:
        print("GEMINI_API_KEY missing")
        return None
    tried = []
    for m in PREFERRED_MODELS + list_flash_models()[:3]:
        if m in tried:
            continue
        tried.append(m)
        data = try_model(m, prompt)
        if data:
            return data
    return None


def fallback():
    def sc(t, e, p):
        return {"text": t, "emoji": e, "image_prompt": p}
    return {
        "title": "प्यारे जानवर और उनकी आवाज़",
        "description": "बच्चों के लिए प्यारे जानवर।",
        "scenes": [
            sc("आज हम तीन प्यारे जानवरों से मिलेंगे।", "🐾", "three cute cartoon animals together"),
            sc("यह है कुत्ता। कुत्ता कहता है भौं भौं।", "🐶", "cute cartoon puppy"),
            sc("यह है बिल्ली। बिल्ली कहती है म्याऊं म्याऊं।", "🐱", "cute cartoon kitten"),
            sc("यह है गाय। गाय कहती है मूं मूं।", "🐮", "cute cartoon cow"),
            sc("आपको कौन सा जानवर पसंद आया? फॉलो करना मत भूलना।", "🐾", "happy cartoon animals waving"),
        ],
    }


def main():
    OUT.mkdir(exist_ok=True)
    fmt = pick_format()
    animals, learning = pick_seed()
    rule = FORMAT_RULES[fmt].format(animals=animals, learning=learning)
    print(f"Format: {fmt} | animals: {animals}")

    prompt = f"""You create gentle, safe Hindi videos for children aged 2 to 6.
Task: {rule}

RULES:
- Everything must be child-safe, happy and non-scary. All facts must be TRUE.
- Write the spoken text in very simple Hindi (Devanagari). Each scene text is
  at most 14 words. Total 7 to 9 scenes.
- Scene text is read aloud and shown on screen, so no emojis in the text.
- image_prompt: English, describe ONE cute cartoon animal doing something simple
  with a simple colorful background. No text or letters in the picture.
- emoji: ONE emoji that matches the scene (for example 🐶).
- title: a cute Hindi title under 60 characters. description: 2 short Hindi lines.

Return ONLY JSON: {{"title": "...", "description": "...",
"scenes": [{{"text": "...", "image_prompt": "...", "emoji": "..."}}]}}"""

    data = call_gemini(prompt) or fallback()
    data["format"] = fmt
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    with open(OUT / "kids_script.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(data['scenes'])} scenes")


if __name__ == "__main__":
    main()
