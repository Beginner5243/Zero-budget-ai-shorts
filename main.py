"""
Zero-Budget AI Shorts Automation
Main entry point
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from topic_discovery import discover_topics
from fact_checker import verify_fact


OUTPUT_DIR = Path("output")
API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODELS = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
MAX_TOPICS = 2


def normalize_topics(raw):
    if raw is None:
        return []
    if isinstance(raw, dict):
        for key in ("topics", "items", "results", "data"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
        else:
            raw = [raw]
    if isinstance(raw, str):
        raw = [raw]
    names = []
    for item in list(raw):
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            names.append(str(item.get("title") or item.get("topic")
                             or item.get("name") or item))
        else:
            names.append(str(item))
    return names


def call_gemini(prompt):
    if not API_KEY:
        print("GEMINI_API_KEY missing")
        return None
    for model in MODELS:
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent")
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.7,
            },
        }
        headers = {"x-goog-api-key": API_KEY,
                   "Content-Type": "application/json"}
        try:
            r = requests.post(url, headers=headers, json=body, timeout=60)
            if r.status_code != 200:
                print(f"{model} failed: {r.status_code} {r.text[:200]}")
                continue
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip().strip("`")
            if text.startswith("json"):
                text = text[4:]
            data = json.loads(text)
            if all(isinstance(data.get(k), str) and data.get(k)
                   for k in ("title_en", "script_en", "title_hi", "script_hi")):
                print(f"Script made with {model}")
                return data
            print(f"{model}: JSON keys missing")
        except Exception as error:
            print(f"{model} error: {error}")
    return None


def fallback_scripts(topic):
    return {
        "title_en": f"Amazing fact about {topic}",
        "script_en": (
            f"Did you know this about {topic}? "
            f"There is more to {topic} than most people realise. "
            "Follow for more amazing facts."
        ),
        "title_hi": f"{topic} के बारे में हैरान करने वाला तथ्य",
        "script_hi": (
            f"क्या आप {topic} के बारे में यह जानते हैं? "
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
- Use only true, well-known facts. Never invent numbers, names or dates.
- Start with a strong hook question or shocking line.
- 6 to 8 short sentences, about 70 to 85 words (30 to 35 seconds when spoken).
- Plain spoken language. No emojis, no hashtags, no stage directions.
- End by asking the viewer to follow for more amazing facts.

Return ONLY JSON with exactly these keys:
title_en, script_en, title_hi, script_hi
script_hi is the same story written naturally in Hindi (Devanagari script)."""
    return call_gemini(prompt) or fallback_scripts(topic)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=== Zero-Budget AI Shorts Creator ===")
    print("Finding topics...")

    try:
        topics = normalize_topics(discover_topics())
    except Exception as error:
        print(f"Topic discovery error: {error}")
        topics = []

    if not topics:
        print("No topics found. Try again later.")

    results = []

    for topic in topics[:MAX_TOPICS]:
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
