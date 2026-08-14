#!/usr/bin/env python3
"""
Dump a Sleeper fantasy football league's full history to JSON.

Sleeper's read API is public (no auth). This script starts from one season's
league_id and walks the `previous_league_id` chain backward to capture every
prior season, then saves users, rosters, matchups (all weeks), brackets, and
league settings for each.

Usage:
    pip install requests
    python pull_sleeper.py 1389723831165259776

Output:
    sleeper_data/<season>/league.json
    sleeper_data/<season>/users.json
    sleeper_data/<season>/rosters.json
    sleeper_data/<season>/matchups/week_<n>.json
    sleeper_data/<season>/winners_bracket.json
    sleeper_data/<season>/losers_bracket.json

Commit the sleeper_data/ directory and I'll take it from there.
"""
import json
import os
import sys
import time
import urllib.request

BASE = "https://api.sleeper.app/v1"
OUT = "sleeper_data"
# Pull generously; empty weeks just come back as [] and are skipped.
MAX_WEEK = 18


def get(path):
    url = f"{BASE}/{path}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                print(f"  ! failed {url}: {e}")
                return None
            time.sleep(2 ** attempt)
    return None


def save(obj, *parts):
    path = os.path.join(OUT, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    return path


def dump_season(league):
    season = league.get("season", "unknown")
    lid = league["league_id"]
    print(f"== Season {season} (league {lid}) ==")

    save(league, season, "league.json")
    save(get(f"league/{lid}/users") or [], season, "users.json")
    save(get(f"league/{lid}/rosters") or [], season, "rosters.json")
    save(get(f"league/{lid}/winners_bracket") or [], season, "winners_bracket.json")
    save(get(f"league/{lid}/losers_bracket") or [], season, "losers_bracket.json")

    for wk in range(1, MAX_WEEK + 1):
        data = get(f"league/{lid}/matchups/{wk}")
        if not data:
            continue
        save(data, season, "matchups", f"week_{wk:02d}.json")
        print(f"  week {wk:>2}: {len(data)} team-entries")

    return league.get("previous_league_id")


def main():
    if len(sys.argv) < 2:
        print("Usage: python pull_sleeper.py <league_id>")
        sys.exit(1)

    lid = sys.argv[1]
    seen = set()
    while lid and lid not in ("0", "null", None) and lid not in seen:
        seen.add(lid)
        league = get(f"league/{lid}")
        if not league:
            print(f"Could not fetch league {lid}; stopping.")
            break
        lid = dump_season(league)

    print(f"\nDone. {len(seen)} season(s) written to ./{OUT}/")
    print("Commit the sleeper_data/ directory and push.")


if __name__ == "__main__":
    main()
