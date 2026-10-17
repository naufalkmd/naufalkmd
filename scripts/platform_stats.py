"""Rewrite the Other Platforms stats blocks in README.md.

Usage: python scripts/platform_stats.py <username> [README.md]

Each platform has its own marker block in the README and is updated on its own:
- Kaggle: official kagglesdk public user search (no API key).
- Hugging Face: public https://huggingface.co/api/users/<user>/overview.
- Devpost: no API, so the totals are read from the public profile page.
If a platform can't be reached, its block is left untouched, so the daily
workflow never breaks because of one site.
"""

import json
import re
import subprocess
import sys
from urllib.parse import quote

USER_AGENT = "Mozilla/5.0 (profile-readme-stats; +https://github.com/naufalkmd)"

KAGGLE_TIER_COLORS = {
    "NOVICE": "5AC995",
    "CONTRIBUTOR": "20BEFF",
    "EXPERT": "95628F",
    "MASTER": "F96517",
    "GRANDMASTER": "DCA917",
}


def badge(label, message, color, logo, style="flat-square"):
    def esc(text):
        return quote(text.replace("-", "--").replace("_", "__"), safe="")

    return (
        f"https://img.shields.io/badge/{esc(label)}-{esc(message)}-{color}"
        f"?style={style}&logo={logo}&logoColor=white&labelColor=black"
    )


def link(href, alt, src):
    return f'  <a href="{href}"><img alt="{alt}" src="{src}"/></a>'


def get(url):
    # curl rather than urllib: Devpost answers 403 to Python's HTTP client.
    result = subprocess.run(
        ["curl", "-sfL", "--max-time", "30", "-A", USER_AGENT, url],
        capture_output=True, check=True,
    )
    return result.stdout.decode("utf-8")


def kaggle(username):
    from kagglesdk import KaggleClient
    from kagglesdk.search.types.search_api_service import ListEntitiesFilters, ListEntitiesRequest
    from kagglesdk.search.types.search_enums import DocumentType

    filters = ListEntitiesFilters()
    filters.query = username
    filters.document_types = [DocumentType.USER]
    request = ListEntitiesRequest()
    request.filters = filters
    response = KaggleClient().search.search_api_client.list_entities(request)
    doc = next(
        (d for d in response.to_dict().get("documents", [])
         if d.get("ownerUser", {}).get("userName", "").lower() == username.lower()),
        None,
    )
    if doc is None:
        raise LookupError(f"Kaggle user {username!r} not found")

    tier = doc["ownerUser"].get("tier", "NOVICE")
    stats = doc.get("userDocument", {})
    profile = f"https://www.kaggle.com/{username}"
    lines = [link(profile, "Kaggle tier",
                  badge("Kaggle", tier.title(), KAGGLE_TIER_COLORS.get(tier, "20BEFF"), "kaggle", "for-the-badge"))]
    for label, path, key in [("Competitions", "competitions", "competition"),
                             ("Code", "code", "kernel"),
                             ("Datasets", "datasets", "dataset")]:
        message = f"{stats.get(f'{key}Points', 0)} pts"
        if stats.get(f"{key}Ranking"):
            message += f" · #{stats[f'{key}Ranking']:,}"
        lines.append(link(f"{profile}/{path}", label, badge(label, message, "20BEFF", "kaggle")))
    return lines


def huggingface(username):
    data = json.loads(get(f"https://huggingface.co/api/users/{username}/overview"))
    profile = f"https://huggingface.co/{username}"
    lines = [link(profile, "Hugging Face",
                  badge("Hugging Face", username, "FFD21E", "huggingface", "for-the-badge"))]
    # Only counts above zero, so the row fills in as things are published.
    for label, key, path in [("Models", "numModels", "?tab=models"),
                             ("Datasets", "numDatasets", "?tab=datasets"),
                             ("Spaces", "numSpaces", "?tab=spaces"),
                             ("Papers", "numPapers", ""),
                             ("Followers", "numFollowers", "")]:
        if data.get(key, 0) > 0:
            lines.append(link(f"{profile}{path}", label, badge(label, str(data[key]), "FFD21E", "huggingface")))
    return lines


def devpost(username):
    html = get(f"https://devpost.com/{username}")
    totals = {
        label: int(number)
        for number, label in re.findall(r'<div class="totals"><span>(\d+)</span></div>\s*(\w+)', html)
    }
    if "Projects" not in totals:
        raise LookupError("Devpost totals not found on profile page")
    profile = f"https://devpost.com/{username}"
    lines = [link(profile, "Devpost",
                  badge("Devpost", f"{totals['Projects']} projects", "003E54", "devpost", "for-the-badge"))]
    for label, path in [("Hackathons", "/challenges"), ("Achievements", "/achievements"), ("Followers", "/followers")]:
        if label in totals:
            lines.append(link(f"{profile}{path}", label, badge(label, str(totals[label]), "003E54", "devpost")))
    return lines


PLATFORMS = {"KAGGLE": kaggle, "HUGGINGFACE": huggingface, "DEVPOST": devpost}


def main():
    username = sys.argv[1]
    readme = sys.argv[2] if len(sys.argv) > 2 else "README.md"
    with open(readme, encoding="utf-8", newline="") as f:
        text = f.read()
    newline = "\r\n" if "\r\n" in text else "\n"

    for name, fetch in PLATFORMS.items():
        start, end = f"<!-- {name}-STATS:START -->", f"<!-- {name}-STATS:END -->"
        pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
        if not pattern.search(text):
            print(f"{name}: markers not found in README, skipped")
            continue
        try:
            lines = fetch(username)
        except Exception as e:
            print(f"{name}: not updated ({e})")
            continue
        block = newline.join([start, '<p align="center">', *lines, "</p>", end])
        text = pattern.sub(lambda _: block, text)
        print(f"{name}: updated")

    with open(readme, "w", encoding="utf-8", newline="") as f:
        f.write(text)


if __name__ == "__main__":
    main()
