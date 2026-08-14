#!/usr/bin/env python3
"""
Pull a Sleeper league's full history into Supabase: owners/identities, teams,
per-team-week scores (with computed optimal lineup), and drafts.

    pip install -r ingest/requirements.txt
    # .env needs SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SLEEPER_LEAGUE_ID
    python ingest/pull_sleeper.py                 # uses SLEEPER_LEAGUE_ID
    python ingest/pull_sleeper.py <league_id>

Walks previous_league_id to capture every season. Sleeper's read API needs no
auth. Owners are created per Sleeper account; afterwards you map Sleeper users
to their ESPN owners (same merge step used for ESPN).

Note: Sleeper doesn't expose historical projections, so expected_points is left
null for Sleeper seasons (optimal and actual are still computed).
"""
import json
import os
import sys
import time

import requests

from db import ensure_owner, get_client, owner_map, upsert_season

BASE = "https://api.sleeper.app/v1"
PLATFORM = "sleeper"
PLAYERS_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sleeper_players.json")

# Which roster slots are "flex" and what they accept.
FLEX = {
    "FLEX": {"RB", "WR", "TE"},
    "WRRB_FLEX": {"RB", "WR"},
    "REC_FLEX": {"WR", "TE"},
    "SUPER_FLEX": {"QB", "RB", "WR", "TE"},
}
BENCH = {"BN", "IR", "TAXI"}


def get(path):
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{path}", timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                print(f"  ! {path}: {e}")
                return None
            time.sleep(2 ** attempt)


def load_players():
    if os.path.exists(PLAYERS_CACHE):
        with open(PLAYERS_CACHE) as f:
            return json.load(f)
    print("Fetching Sleeper player map (~5MB, once)...")
    data = get("players/nfl") or {}
    with open(PLAYERS_CACHE, "w") as f:
        json.dump(data, f)
    return data


def optimal_points(players_points, positions, slots):
    """Best starting lineup total given each rostered player's points+position."""
    avail = {}  # pos -> sorted list of points desc
    for pid, pts in players_points.items():
        pos = positions.get(pid)
        if pos:
            avail.setdefault(pos, []).append(pts)
    for pos in avail:
        avail[pos].sort(reverse=True)

    total = 0.0
    flex_slots = []
    for slot in slots:
        if slot in BENCH:
            continue
        if slot in FLEX:
            flex_slots.append(slot)
            continue
        pool = avail.get(slot)          # QB/RB/WR/TE/K/DEF
        if pool:
            total += pool.pop(0)
    for slot in flex_slots:
        elig = FLEX[slot]
        best_pos, best_val = None, None
        for pos in elig:
            if avail.get(pos) and (best_val is None or avail[pos][0] > best_val):
                best_pos, best_val = pos, avail[pos][0]
        if best_pos is not None:
            total += avail[best_pos].pop(0)
    return round(total, 2)


def pull_season(sb, league, players, cache):
    season = int(league["season"])
    lid = league["league_id"]
    slots = league.get("roster_positions", [])
    playoff_start = league.get("settings", {}).get("playoff_week_start") or 15
    print(f"== Sleeper {season} (league {lid}) ==")

    season_id = upsert_season(sb, PLATFORM, lid, season,
                              league.get("name") or f"Sleeper {season}", league.get("settings", {}))

    users = {u["user_id"]: u for u in (get(f"league/{lid}/users") or [])}
    rosters = get(f"league/{lid}/rosters") or []

    team_rows, owner_by_roster = [], {}
    for r in rosters:
        uid = r.get("owner_id")
        u = users.get(uid, {})
        name = u.get("display_name") or (uid and f"Sleeper {uid}")
        owner_id = ensure_owner(sb, PLATFORM, uid, name, cache) if uid else None
        owner_by_roster[r["roster_id"]] = owner_id
        team_rows.append({
            "season_id": season_id, "owner_id": owner_id,
            "platform_roster_id": str(r["roster_id"]),
            "team_name": (u.get("metadata") or {}).get("team_name") or name,
            "abbr": None,
        })
    sb.table("teams").upsert(team_rows, on_conflict="season_id,platform_roster_id").execute()
    team_by_roster = {
        str(t["platform_roster_id"]): t["team_id"]
        for t in sb.table("teams").select("team_id, platform_roster_id")
        .eq("season_id", season_id).execute().data
    }
    positions = {pid: (p or {}).get("position") for pid, p in players.items()}

    rows = []
    for week in range(1, 19):
        mus = get(f"league/{lid}/matchups/{week}")
        if not mus:
            continue
        by_mid = {}
        for m in mus:
            if m.get("points") is None:
                continue
            by_mid.setdefault(m.get("matchup_id"), []).append(m)
        for m in mus:
            if m.get("points") is None:
                continue
            rid = str(m["roster_id"])
            tid = team_by_roster.get(rid)
            if not tid:
                continue
            opp = next((x for x in by_mid.get(m.get("matchup_id"), []) if x is not m), None)
            pa = opp.get("points") if opp else None
            res = None
            if opp is not None:
                res = "T" if m["points"] == pa else ("W" if m["points"] > pa else "L")
            opt = optimal_points(m.get("players_points") or {}, positions, slots)
            rows.append({
                "team_id": tid, "week": week, "is_playoff": week >= playoff_start,
                "points_for": m["points"], "points_against": pa,
                "opponent_team_id": team_by_roster.get(str(opp["roster_id"])) if opp else None,
                "result": res, "optimal_points": opt, "expected_points": None,
            })
    for i in range(0, len(rows), 500):
        sb.table("team_weeks").upsert(rows[i:i + 500], on_conflict="team_id,week").execute()
    print(f"  team_weeks: {len(rows)}")

    pull_draft(sb, league, season_id, team_by_roster)
    return league.get("previous_league_id")


def pull_draft(sb, league, season_id, team_by_roster):
    draft_id = league.get("draft_id")
    if not draft_id:
        return
    draft = get(f"draft/{draft_id}") or {}
    picks = get(f"draft/{draft_id}/picks") or []
    if not picks:
        return
    sb.table("drafts").upsert(
        {"season_id": season_id, "platform_draft_id": str(draft_id),
         "type": draft.get("type"), "rounds": draft.get("settings", {}).get("rounds"),
         "settings": draft.get("settings", {})},
        on_conflict="season_id",
    ).execute()
    did = sb.table("drafts").select("draft_id").eq("season_id", season_id) \
        .execute().data[0]["draft_id"]
    rows = []
    for p in picks:
        meta = p.get("metadata") or {}
        name = f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip() or None
        rows.append({
            "draft_id": did, "round": p.get("round"), "pick_no": p.get("pick_no"),
            "team_id": team_by_roster.get(str(p.get("roster_id"))),
            "player_name": name, "position": meta.get("position"), "nfl_team": meta.get("team"),
            "amount": int(meta["amount"]) if meta.get("amount") else None,
            "is_keeper": bool(p.get("is_keeper")),
        })
    for i in range(0, len(rows), 500):
        sb.table("draft_picks").upsert(rows[i:i + 500], on_conflict="draft_id,pick_no").execute()
    print(f"  draft picks: {len(rows)}")


def main():
    lid = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SLEEPER_LEAGUE_ID")
    if not lid:
        raise SystemExit("Pass a league id or set SLEEPER_LEAGUE_ID in .env")
    sb = get_client()
    cache = owner_map(sb, PLATFORM)
    players = load_players()
    seen = set()
    while lid and lid not in seen:
        seen.add(lid)
        league = get(f"league/{lid}")
        if not league:
            break
        lid = pull_season(sb, league, players, cache)
    print(f"Sleeper pull complete ({len(seen)} season(s)).")


if __name__ == "__main__":
    main()
