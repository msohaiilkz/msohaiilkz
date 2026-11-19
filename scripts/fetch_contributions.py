#!/usr/bin/env python3
"""Fetch PUBLIC GitHub contribution-calendar data and public repo metadata.

No invented metrics. If the GitHub API fails, the existing JSON is left intact.
Requires GITHUB_TOKEN (GitHub Actions' automatic token is sufficient for public data).
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
USERNAME = CONFIG["username"]
DEST = ROOT / "data" / "contributions.json"
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()


def api_json(url: str, *, body: dict | None = None) -> dict:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required to refresh contribution data")
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "sohail-profile-cards/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main() -> int:
    query = """query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }"""
    try:
        result = api_json("https://api.github.com/graphql", body={"query": query, "variables": {"login": USERNAME}})
        if result.get("errors"):
            raise RuntimeError("GitHub GraphQL error: " + json.dumps(result["errors"]))
        calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        days = [
            {"date": day["date"], "count": int(day["contributionCount"])}
            for week in calendar["weeks"] for day in week["contributionDays"]
        ]
        if len(days) < 300 or len({d["date"] for d in days}) != len(days):
            raise ValueError("Incomplete or duplicate contribution-calendar days; refusing to replace previous data")
        for day in days:
            dt.date.fromisoformat(day["date"])
            if day["count"] < 0:
                raise ValueError("Negative contribution count")
        days.sort(key=lambda d: d["date"])
        repos = {}
        for item in CONFIG["featured_repos"]:
            repo = item["repo"]
            try:
                info = api_json("https://api.github.com/repos/" + urllib.parse.quote(repo, safe="/"))
                repos[repo] = {
                    "stars": int(info.get("stargazers_count", 0)),
                    "language": info.get("language"),
                    "updated_at": info.get("updated_at"),
                    "html_url": info.get("html_url"),
                }
            except (KeyError, ValueError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                # A private or missing repo must not cause invented public metadata.
                print(f"Note: repo metadata unavailable for {repo}: {exc}", file=sys.stderr)
        payload = {
            "username": USERNAME,
            "updated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "source": "GitHub GraphQL public contribution calendar and REST public repo metadata",
            "total_contributions": int(calendar["totalContributions"]),
            "days": days,
            "repos": repos,
        }
        # Atomic write: never destroy last known-good data on failure.
        temp = DEST.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(DEST)
        print(f"Updated {DEST.relative_to(ROOT)}: {len(days)} days, {len(repos)} repos")
        return 0
    except (RuntimeError, ValueError, KeyError, TypeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"Contribution refresh FAILED; previous JSON preserved: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
