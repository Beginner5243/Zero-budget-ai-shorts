import requests
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "ZeroBudgetScienceBot/1.0 (educational content)"
}


def verify_fact(topic_data):
    """
    Validate topic metadata and independently retrieve its
    Wikipedia source page. This checks source availability,
    not whether every scientific claim is definitively true.
    """

    topic = topic_data.get("topic", "").strip()
    summary = topic_data.get("summary", "").strip()
    source_url = topic_data.get("source_url", "").strip()

    if not topic or len(summary) < 100:
        print("[REJECTED] Missing topic or insufficient source text.")
        return False

    parsed = urlparse(source_url)

    if parsed.scheme != "https" or parsed.hostname != "en.wikipedia.org":
        print("[REJECTED] Source must be an English Wikipedia page.")
        return False

    try:
        response = requests.get(
            source_url,
            headers=HEADERS,
            timeout=20
        )

        if response.status_code != 200:
            print(
                f"[REJECTED] Source returned HTTP "
                f"{response.status_code}."
            )
            return False

        content_type = response.headers.get("Content-Type", "")

        if "text/html" not in content_type.lower():
            print("[REJECTED] Source is not an HTML page.")
            return False

        print(f"[SOURCE AVAILABLE] {source_url}")
        print("[NOTICE] Source availability does not prove every claim.")
        return True

    except requests.RequestException as error:
        print(f"[ERROR] Could not verify source: {error}")
        return False


if __name__ == "__main__":
    sample = {
        "topic": "Earth",
        "summary": (
            "Earth is the third planet from the Sun. "
            "It is the only astronomical object known to "
            "harbor life."
        ),
        "source_url": "https://en.wikipedia.org/wiki/Earth"
    }

    print("Verification result:", verify_fact(sample))
