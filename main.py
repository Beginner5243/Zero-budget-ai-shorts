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
        topics = discover_topics()
    except Exception as error:
        print(f"Topic discovery error: {error}")
        return

    if not topics:
        print("No topics found. Try again later.")
        return

    results = []

    for item in topics[:5]:
        topic = item if isinstance(item, str) else str(item)
        print(f"Processing: {topic}")

        try:
            verification = verify_fact(topic)
        except Exception as error:
            verification = {
                "verified": False,
                "message": str(error),
            }

        script = generate_script(topic)

       
