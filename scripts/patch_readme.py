#!/usr/bin/env python3
"""Preview or safely insert SVG cards at the TOP of the current README.

Never removes the existing README. --apply backs it up and edits only our marker block.
"""
from __future__ import annotations
import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- SOHAIL-ANIMATED-CARDS:START -->"
END = "<!-- SOHAIL-ANIMATED-CARDS:END -->"


def card_markup() -> str:
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    links = config["links"]
    if len(links) != 3:
        raise ValueError("Exactly three links required for 32.5% tile row")
    parts = [START, '<div align="center">',
             '<img src="./cards/hero.svg" alt="Muhammad Sohail - Full Stack Engineer" width="100%" />',
             "", "<!-- Each linked tile image uses width 32.5% -->"]
    for link in links:
        href = html.escape(link["url"], quote=True)
        key = re.sub(r"[^a-z0-9]+", "-", link["key"].lower()).strip("-")
        alt = html.escape(link["title"], quote=True)
        parts.append(f'<a href="{href}"><img src="./cards/tile-{key}.svg" alt="{alt}" width="32.5%" /></a>')
    parts.extend([
        "", '<img src="./cards/stats.svg" alt="GitHub contributions by month and streak" width="100%" />',
        '<img src="./cards/contribution-graph.svg" alt="GitHub contribution heatmap" width="100%" />',
        "", "</div>", "", "### Featured repositories", "",
    ])
    for item in config["featured_repos"]:
        repo = item["repo"]
        name = item["name"]
        slug = re.sub(r"[^a-z0-9]+", "-", repo.split("/")[-1].lower()).strip("-")
        href = html.escape('https://github.com/' + repo, quote=True)
        alt = html.escape(name + ' project', quote=True)
        parts.append(f'<a href="{href}"><img src="./cards/repo-{slug}.svg" alt="{alt}" width="100%" /></a>')
    parts.extend(["", END])
    return "\n".join(parts)


def patch(old: str) -> str:
    if (START in old) != (END in old):
        raise ValueError("Only one animated-card marker found; refusing unsafe edit")
    block = card_markup()
    if START in old:
        if old.count(START) != 1 or old.count(END) != 1 or old.index(START) > old.index(END):
            raise ValueError("Invalid marker positions or duplicates; refusing unsafe edit")
        a = old.index(START)
        b = old.index(END) + len(END)
        return old[:a] + block.rstrip("\n") + old[b:]
    return block + "\n\n---\n\n<!-- Original README content preserved below. -->\n\n" + old.lstrip("\ufeff")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="Apply to README.md after creating a timestamped backup")
    p.add_argument("--readme", default=str(ROOT / "README.md"), help="Path to existing README.md")
    args = p.parse_args()
    path = Path(args.readme)
    if not path.is_file():
        print(f"No existing README found at {path}. Copy this kit into your profile repo first.", file=sys.stderr)
        return 2
    original = path.read_text(encoding="utf-8")
    result = patch(original)
    if not args.apply:
        preview = path.with_name("README.preview.md")
        preview.write_text(result, encoding="utf-8")
        print(f"PREVIEW ONLY: {preview} (README.md untouched)")
        return 0
    if result == original:
        print("README already up-to-date; nothing changed")
        return 0
    backup = path.with_name("README.backup-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + ".md")
    if backup.exists():
        raise RuntimeError(f"Backup already exists: {backup}")
    backup.write_text(original, encoding="utf-8")
    path.write_text(result, encoding="utf-8")
    print(f"Updated {path}. Original saved at {backup}. No existing sections removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
