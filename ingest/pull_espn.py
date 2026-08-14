#!/usr/bin/env python3
"""
Pull an ESPN season (default 2024) from the live API into Supabase:
owners/identities, teams, and per-team-week scores with Optimal/Expected
points computed the same way as the historical CSVs.

    pip install -r ingest/requirements.txt
    # .env needs SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
    #            ESPN_LEAGUE_ID, ESPN_SWID, ESPN_S2
    python ingest/pull_espn.py 2024          # one year
    python ingest/pull_espn.py 2024 2025     # several

Re-running upserts; it won't duplicate rows.
"""
import os
import sys

from db import ensure_owner, get_client, owner_map, upsert_season
from espn_api import compute_pts, get_matchups, get_slates, get_view, structure_for

LEAGUE_ID = os.environ.get("ESPN_LEAGUE_ID", "564698")
PLATFORM = "espn"


def result_of(winner, home, is_home):
    if winner == "TIE":
        return "T"
    if winner in ("HOME", "AWAY"):
        return "W" if (winner == "HOME") == is_home else "L"
    return None  # undecided / no matchup


def pull_year(sb, year, cache):
    print(f"== ESPN {year} ==")
    team_json = get_view(LEAGUE_ID, year, "mTeam")
    members = {m["id"]: m for m in team_json["members"]}  # id is the SWID
    settings = team_json.get("settings", {})
    playoff_start = settings.get("scheduleSettings", {}).get("matchupPeriodCount", 14) + 1
    season_id = upsert_season(sb, PLATFORM, LEAGUE_ID, year,
                              settings.get("name") or f"ESPN League {year}", settings)

    # owners + teams
    team_rows = []
    for team in team_json["teams"]:
        swid = (team.get("owners") or [None])[0]
        name = None
        if swid and swid in members:
            m = members[swid]
            name = f"{(m.get('firstName') or '').strip()} {(m.get('lastName') or '').strip()}".strip() \
                or m.get("displayName")
        owner_id = ensure_owner(sb, PLATFORM, swid, name or f"ESPN {swid}", cache) if swid else None
        team_rows.append({
            "season_id": season_id, "owner_id": owner_id,
            "platform_roster_id": str(team["id"]),
            "team_name": (team.get("name") or name),
            "abbr": team.get("abbrev"),
        })
    sb.table("teams").upsert(team_rows, on_conflict="season_id,platform_roster_id").execute()
    team_by_roster = {
        str(t["platform_roster_id"]): t["team_id"]
        for t in sb.table("teams").select("team_id, platform_roster_id")
        .eq("season_id", season_id).execute().data
    }

    # schedule (opponent / points-against / result / playoff flag)
    sched = get_view(LEAGUE_ID, year, "mMatchupScore").get("schedule", [])
    meta = {}  # (week, roster_id) -> (opp_roster, pa, result, is_playoff)
    for g in sched:
        wk = g.get("matchupPeriodId")
        is_playoff = g.get("playoffTierType", "NONE") not in ("NONE", None)
        winner = g.get("winner")
        home, away = g.get("home"), g.get("away")
        if not home:
            continue
        h_id, h_pts = str(home["teamId"]), home.get("totalPoints", 0)
        if away:
            a_id, a_pts = str(away["teamId"]), away.get("totalPoints", 0)
            meta[(wk, h_id)] = (a_id, a_pts, result_of(winner, home, True), is_playoff)
            meta[(wk, a_id)] = (h_id, h_pts, result_of(winner, home, False), is_playoff)
        else:  # bye
            meta[(wk, h_id)] = (None, None, "W", is_playoff)

    # weekly optimal/expected/actual
    posns, struc = structure_for(year)
    rows = []
    for week in range(1, 18):
        try:
            d = get_matchups(LEAGUE_ID, year, week)
        except Exception as e:  # noqa: BLE001
            print(f"  week {week}: skip ({e})")
            continue
        if not d.get("teams"):
            continue
        pts = compute_pts(get_slates(d, year, week), posns, struc)
        got = False
        for roster_id, p in pts.items():
            rid = str(roster_id)
            tid = team_by_roster.get(rid)
            if not tid or (p["apts"] == 0 and p["opts"] == 0):
                continue
            opp_r, pa, res, is_playoff = meta.get((week, rid), (None, None, None, False))
            rows.append({
                "team_id": tid, "week": week, "is_playoff": is_playoff,
                "points_for": p["apts"], "points_against": pa,
                "opponent_team_id": team_by_roster.get(opp_r) if opp_r else None,
                "result": res, "optimal_points": p["opts"], "expected_points": p["epts"],
            })
            got = True
        if got:
            print(f"  week {week}: {len(pts)} teams")
    for i in range(0, len(rows), 500):
        sb.table("team_weeks").upsert(rows[i:i + 500], on_conflict="team_id,week").execute()
    print(f"  team_weeks upserted: {len(rows)}")


def main():
    years = sys.argv[1:] or ["2024"]
    sb = get_client()
    cache = owner_map(sb, PLATFORM)
    for y in years:
        pull_year(sb, int(y), cache)
    print("ESPN pull complete.")


if __name__ == "__main__":
    main()
