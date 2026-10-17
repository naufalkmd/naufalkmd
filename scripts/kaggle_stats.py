"""Rewrite the Kaggle stats block in README.md from Kaggle's public user search.

Usage: python scripts/kaggle_stats.py <kaggle-username> [README.md]

Uses the official kagglesdk; no Kaggle API key is needed. On any API error the
README is left untouched, so the daily workflow never breaks because of Kaggle.
"""

import re
import sys
from urllib.parse import quote

from kagglesdk import KaggleClient
from kagglesdk.search.types.search_api_service import ListEntitiesFilters, ListEntitiesRequest
from kagglesdk.search.types.search_enums import DocumentType

START = "<!-- KAGGLE-STATS:START -->"
END = "<!-- KAGGLE-STATS:END -->"

TIER_COLORS = {
    "NOVICE": "5AC995",
    "CONTRIBUTOR": "20BEFF",
    "EXPERT": "95628F",
    "MASTER": "F96517",
    "GRANDMASTER": "DCA917",
}

CATEGORIES = [
    ("Competitions", "competitions", "competition"),
    ("Code", "code", "kernel"),
    ("Datasets", "datasets", "dataset"),
]


def fetch(username):
    filters = ListEntitiesFilters()
    filters.query = username
    filters.document_types = [DocumentType.USER]
    request = ListEntitiesRequest()
    request.filters = filters
    response = KaggleClient().search.search_api_client.list_entities(request)
    for doc in response.to_dict().get("documents", []):
        if doc.get("ownerUser", {}).get("userName", "").lower() == username.lower():
            return doc
    raise LookupError(f"Kaggle user {username!r} not found")


def badge(label, message, color, style):
    def esc(text):
        return quote(text.replace("-", "--").replace("_", "__"), safe="")

    return (
        f"https://img.shields.io/badge/{esc(label)}-{esc(message)}-{color}"
        f"?style={style}&logo=kaggle&logoColor=white&labelColor=black"
    )


def render(username, doc):
    tier = doc["ownerUser"].get("tier", "NOVICE")
    stats = doc.get("userDocument", {})
    profile = f"https://www.kaggle.com/{username}"

    lines = [
        START,
        '<p align="center">',
        f'  <a href="{profile}"><img alt="Kaggle tier" '
        f'src="{badge("Kaggle Tier", tier.title(), TIER_COLORS.get(tier, "20BEFF"), "for-the-badge")}"/></a>',
        "</p>",
        '<p align="center">',
    ]
    for label, path, key in CATEGORIES:
        message = f"{stats.get(f'{key}Points', 0)} pts"
        ranking = stats.get(f"{key}Ranking")
        if ranking:
            message += f" · #{ranking:,}"
        lines.append(
            f'  <a href="{profile}/{path}"><img alt="{label}" '
            f'src="{badge(label, message, "20BEFF", "flat-square")}"/></a>'
        )
    lines.append(
        f'  <a href="{profile}/models"><img alt="Models" '
        f'src="{badge("Models", "View", "20BEFF", "flat-square")}"/></a>'
    )
    lines += ["</p>", END]
    return "\n".join(lines)


def main():
    username = sys.argv[1]
    readme = sys.argv[2] if len(sys.argv) > 2 else "README.md"
    try:
        block = render(username, fetch(username))
    except Exception as e:
        print(f"Kaggle stats not updated: {e}")
        return

    with open(readme, encoding="utf-8", newline="") as f:
        text = f.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        print("Kaggle stats markers not found in README; nothing to update.")
        return
    newline = "\r\n" if "\r\n" in text else "\n"
    text = pattern.sub(lambda _: block.replace("\n", newline), text)
    with open(readme, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(block)


if __name__ == "__main__":
    main()
