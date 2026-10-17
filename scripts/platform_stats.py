"""Draw the Other Platforms stat cards shown in README.md.

Usage: python scripts/platform_stats.py <username> [output-dir]

Writes one SVG card per platform (default: profile-platforms/<platform>.svg):
- Kaggle: official kagglesdk public user search (no API key).
- Hugging Face: public https://huggingface.co/api/users/<user>/overview.
- Devpost: no API, so the totals are read from the public profile page.
If a platform can't be reached, its card is left as it was, so the daily
workflow never breaks because of one site. Cards follow GitHub's light and
dark themes through prefers-color-scheme.
"""

import json
import os
import re
import subprocess
import sys
from xml.sax.saxutils import escape

USER_AGENT = "Mozilla/5.0 (profile-readme-stats; +https://github.com/naufalkmd)"
LOGO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos")

KAGGLE_TIER_COLORS = {
    "NOVICE": "#5AC995",
    "CONTRIBUTOR": "#20BEFF",
    "EXPERT": "#95628F",
    "MASTER": "#F96517",
    "GRANDMASTER": "#DCA917",
}


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
    categories = [("Competitions", "competition"), ("Code", "kernel"), ("Datasets", "dataset")]
    cells = [(f"{stats.get(f'{key}Points', 0):,}", "pts", label) for label, key in categories]
    rankings = [stats[f"{key}Ranking"] for _, key in categories if stats.get(f"{key}Ranking")]
    caption = "performance tier"
    if rankings:
        caption += f" · best rank #{min(rankings):,}"
    return {
        "name": "Kaggle",
        "logo": "kaggle",
        "logo_color": "#20BEFF",
        "accent": KAGGLE_TIER_COLORS.get(tier, "#20BEFF"),
        "headline": tier.title(),
        "caption": caption,
        "cells": cells,
    }


def huggingface(username):
    data = json.loads(get(f"https://huggingface.co/api/users/{username}/overview"))
    return {
        "name": "Hugging Face",
        "logo": "huggingface",
        "logo_color": "#FFD21E",
        "accent": "#FF9D00",
        "headline": f"@{data.get('user', username)}",
        "caption": f"{data.get('numFollowers', 0):,} followers · {data.get('numLikes', 0):,} likes",
        "cells": [
            (f"{data.get('numModels', 0):,}", "", "Models"),
            (f"{data.get('numDatasets', 0):,}", "", "Datasets"),
            (f"{data.get('numSpaces', 0):,}", "", "Spaces"),
        ],
    }


def devpost(username):
    html = get(f"https://devpost.com/{username}")
    totals = {
        label: int(number)
        for number, label in re.findall(r'<div class="totals"><span>(\d+)</span></div>\s*(\w+)', html)
    }
    if "Projects" not in totals:
        raise LookupError("Devpost totals not found on profile page")
    return {
        "name": "Devpost",
        "logo": "devpost",
        "logo_color": "#003E54",
        "logo_color_dark": "#7FD3EA",
        "accent": "#00A0C6",
        "headline": f"{totals['Projects']} projects",
        "caption": f"{totals.get('Followers', 0):,} followers · {totals.get('Likes', 0):,} likes",
        "cells": [
            (f"{totals.get('Hackathons', 0):,}", "", "Hackathons"),
            (f"{totals.get('Achievements', 0):,}", "", "Achievements"),
            (f"{totals.get('Following', 0):,}", "", "Following"),
        ],
    }


def logo(name):
    if name == "kaggle":
        # The simple-icons Kaggle logo is the full wordmark, unreadable at 20px.
        return '<text x="23" y="36" class="logo" style="font: 800 26px Helvetica, Arial, sans-serif">k</text>'
    with open(os.path.join(LOGO_DIR, f"{name}.svg"), encoding="utf-8") as f:
        path = re.search(r'<path d="([^"]+)"', f.read())[1]
    return f'<svg x="20" y="18" width="20" height="20" viewBox="0 0 24 24"><path class="logo" d="{path}"/></svg>'


def render(card):
    width, height = 280, 168
    dark_logo = card.get("logo_color_dark", card["logo_color"])
    columns = []
    for i, (value, unit, label) in enumerate(card["cells"]):
        x = 20 + i * 84
        unit_text = f'<tspan class="unit" dx="3">{escape(unit)}</tspan>' if unit else ""
        columns.append(
            f'<text x="{x}" y="128" class="value">{escape(value)}{unit_text}</text>'
            f'<text x="{x}" y="146" class="label">{escape(label)}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(card['name'])}: {escape(card['headline'])}">
<title>{escape(card['name'])}: {escape(card['headline'])}</title>
<style>
  .card {{ fill: #ffffff; stroke: #d0d7de; }}
  .name {{ font: 600 14px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #1f2328; }}
  .headline {{ font: 700 24px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; fill: {card['accent']}; }}
  .caption {{ font: 400 12px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #59636e; }}
  .value {{ font: 700 17px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #1f2328; }}
  .unit {{ font: 500 10px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #59636e; }}
  .label {{ font: 400 11px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #59636e; }}
  .rule {{ stroke: #d8dee4; }}
  .logo {{ fill: {card['logo_color']}; }}
  @media (prefers-color-scheme: dark) {{
    .card {{ fill: #0d1117; stroke: #30363d; }}
    .name, .value {{ fill: #e6edf3; }}
    .caption, .unit, .label {{ fill: #9198a1; }}
    .rule {{ stroke: #21262d; }}
    .logo {{ fill: {dark_logo}; }}
  }}
</style>
<clipPath id="shape"><rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10"/></clipPath>
<rect class="card" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10"/>
<rect x="0" y="0" width="{width}" height="4" fill="{card['accent']}" clip-path="url(#shape)"/>
{logo(card['logo'])}
<text x="48" y="33" class="name">{escape(card['name'])}</text>
<text x="20" y="72" class="headline">{escape(card['headline'])}</text>
<text x="20" y="91" class="caption">{escape(card['caption'])}</text>
<line class="rule" x1="20" y1="105" x2="{width - 20}" y2="105"/>
{"".join(columns)}
</svg>
'''


PLATFORMS = {"kaggle": kaggle, "huggingface": huggingface, "devpost": devpost}


def main():
    username = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "profile-platforms"
    os.makedirs(out_dir, exist_ok=True)
    for name, fetch in PLATFORMS.items():
        try:
            svg = render(fetch(username))
        except Exception as e:
            print(f"{name}: not updated ({e})")
            continue
        with open(os.path.join(out_dir, f"{name}.svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        print(f"{name}: updated")


if __name__ == "__main__":
    main()
