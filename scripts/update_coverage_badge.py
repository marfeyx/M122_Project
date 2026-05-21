from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COVERAGE_JSON = ROOT / "coverage.json"
BADGE_PATH = ROOT / "badges" / "coverage.svg"


def badge_color(coverage_percent: float) -> str:
    if coverage_percent >= 90:
        return "#4c1"
    if coverage_percent >= 80:
        return "#97ca00"
    if coverage_percent >= 70:
        return "#dfb317"
    if coverage_percent >= 60:
        return "#fe7d37"
    return "#e05d44"


def make_badge(coverage_percent: float) -> str:
    value = f"{coverage_percent:.0f}%"
    color = badge_color(coverage_percent)
    label_width = 67
    value_width = 38
    total_width = label_width + value_width
    value_x = label_width + value_width / 2

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="coverage: {value}">
  <title>coverage: {value}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#555"/>
    <rect x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="33.5" y="15" fill="#010101" fill-opacity=".3">coverage</text>
    <text x="33.5" y="14">coverage</text>
    <text x="{value_x}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{value_x}" y="14">{value}</text>
  </g>
</svg>
"""


def main() -> None:
    coverage_data = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    coverage_percent = coverage_data["totals"]["percent_covered"]

    BADGE_PATH.parent.mkdir(exist_ok=True)
    BADGE_PATH.write_text(make_badge(coverage_percent), encoding="utf-8")


if __name__ == "__main__":
    main()
