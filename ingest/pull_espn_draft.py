#!/usr/bin/env python3
"""
Pull ESPN draft results into Supabase for a range of seasons.

    python ingest/pull_espn_draft.py                # 2018..2024
    python ingest/pull_espn_draft.py 2024           # one year

Seasons should already exist (from pull_espn.py / load_espn_csv.py); if a
season row is missing it is created. Player names are resolved from the
season's player universe.
"""
import os
import sys

from db import get_client, upsert_season
from espn_api import get_players, get_view

LEAGUE_ID = os.environ.get("ESPN_LEAGUE_ID", "564698")
PLATFORM = "espn"


def pull_year(sb, year):
    print(f"== ESPN draft {year} ==")
    j = get_view(LEAGUE_ID, year, "mDraftDetail")
    detail = j.get("draftDetail", {})
    picks = detail.get("picks", [])
    if not picks:
        print("  no picks found; skipping")
        return
    settings = j.get("settings", {})
    dtype = settings.get("draftSettings", {}).get("type", "").lower() or None

    season_id = upsert_season(sb, PLATFORM, LEAGUE_ID, year,
                              settings.get("name") or f"ESPN League {year}", settings)
    team_by_roster = {
        str(t["platform_roster_id"]): t["team_id"]
        for t in sb.table("teams").select("team_id, platform_roster_id")
        .eq("season_id", season_id).execute().data
    }
    players = get_players(LEAGUE_ID, year)

    rounds = max((p.get("roundId", 0) for p in picks), default=0)
    sb.table("drafts").upsert(
        {"season_id": season_id, "platform_draft_id": str(detail.get("drafted", "")),
         "type": dtype, "rounds": rounds, "settings": settings.get("draftSettings", {})},
        on_conflict="season_id",
    ).execute()
    draft_id = sb.table("drafts").select("draft_id").eq("season_id", season_id) \
        .execute().data[0]["draft_id"]

    rows = []
    for p in picks:
        info = players.get(p.get("playerId"), {})
        rows.append({
            "draft_id": draft_id,
            "round": p.get("roundId"),
            "pick_no": p.get("overallPickNumber"),
            "team_id": team_by_roster.get(str(p.get("teamId"))),
            "player_name": info.get("name"),
            "position": info.get("pos"),
            "nfl_team": None,
            "amount": p.get("bidAmount") if p.get("bidAmount", 0) else None,
            "is_keeper": bool(p.get("keeper")),
        })
    for i in range(0, len(rows), 500):
        sb.table("draft_picks").upsert(rows[i:i + 500], on_conflict="draft_id,pick_no").execute()
    print(f"  picks upserted: {len(rows)}")


def main():
    years = sys.argv[1:] or [str(y) for y in range(2018, 2025)]
    sb = get_client()
    for y in years:
        try:
            pull_year(sb, int(y))
        except Exception as e:  # noqa: BLE001
            print(f"  {y}: error {e}")
    print("ESPN draft pull complete.")


if __name__ == "__main__":
    main()
