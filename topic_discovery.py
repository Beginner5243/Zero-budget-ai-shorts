import requests
import random

HEADERS = {
    "User-Agent": "ZeroBudgetScienceBot/1.0 (educational content)"
}

SCIENCE_CATEGORIES = [
    "Physics",
    "Astronomy",
    "Biology",
    "Earth science",
    "Oceanography",
    "Chemistry",
    "Animal",
    "Human body",
    "Space exploration",
    "Weather"
]


def discover_topics():
    """Discover a random science-related Wikipedia article."""

    category = random.choice(SCIENCE_CATEGORIES)

    search_url = "https://en.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"intitle:{category} science facts",
        "gsrnamespace": 0,
        "gsrlimit": 10,
        "prop": "extracts|info",
        "exintro": True,
        "explaintext": True,
        "inprop": "url",
        "format": "json"
    }

    try:
        response = requests.get(
            search_url,
            params=params,
            headers=HEADERS,
            timeout=20
        )
        response.raise_for_status()

        pages = response.json().get(
            "query", {}
        ).get("pages", {})

        candidates = []

        for page in pages.values():
            title = page.get("title", "")
            summary = page.get("extract", "").strip()
            source_url = page.get("fullurl", "")

            if (
                len(summary) >= 250
                and title
                and source_url.startswith("https://")
            ):
                candidates.append({
                    "topic": title,
                    "summary": summary,
                    "source_title": f"Wikipedia: {title}",
                    "source_url": source_url
                })

        if candidates:
            result = random.choice(candidates)
            print(f"[INFO] Discovered topic: {result['topic']}")
            return result

    except (requests.RequestException, ValueError) as error:
        print(f"[WARNING] Wikipedia request failed: {error}")

    raise RuntimeError(
        "No suitable topic discovered. "
        "The pipeline should retry later."
    )


if __name__ == "__main__":
    print(discover_topics())
