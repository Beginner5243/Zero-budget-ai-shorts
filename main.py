"""
Zero-Budget AI Shorts Automation
Main entry point
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from topic_discovery import discover_topics
from fact_checker import verify_fact


OUTPUT_DIR = Path("output")


def normalize_topics(raw):
    """Turn whatever discover_topics() returns into a list of topic names."""
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
            name = (
                item.get("title")
                or item.get("topic")
                or item.get("name")
                or str(item)
            )
            names.append(str(name))
        else:
            names.append(str(item))
    return names


def generate_script(topic):
    """Create a basic Shorts script without a paid AI API."""
    return (
        f"Did you know this interesting fact about {topic}?\n\n"
        f"Let's explore {topic} and discover something surprising!\n\n"
        "Follow for more interesting facts!"
    )


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

    for topic in topics[:5]:
        print(f"Processing: {topic}")

        try:
            verification = verify_fact(topic)
        except Exception as error:
            verification = {
                "verified": False,
                "message": str(error),
            }

        script = generate_script(topic)

        results.append({
            "topic": topic,
            "verification": verification,
            "script": script,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    out_file = OUTPUT_DIR / "shorts_ideas.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"Saved {len(results)} ideas to {out_file}")


if __name__ == "__main__":
    main()
