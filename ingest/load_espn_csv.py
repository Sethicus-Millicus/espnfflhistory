#!/usr/bin/env python3
"""
Load the historical ESPN CSVs (df_tm, df_tm1, df_pts, df_sch) into Supabase.

Idempotent: creates one owner per ESPN account (SWID), then upserts seasons,
teams, and the per-team-week fact rows. Re-running only updates existing rows.

Setup:
    pip install -r ingest/requirements.txt
    cp .env.example .env   # fill in SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
    python ingest/load_espn_csv.py

The service_role key bypasses row-level security for writes; keep it in .env
(never commit it). The public web app only ever uses the anon key.
"""
import csv
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
LEAGUE_ID = os.environ.get("ESPN_LEAGUE_ID", "564698")
PLATFORM = "espn"

if not URL or not KEY:
    sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")

sb = create_client(URL, KEY)
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(name):
    with open(os.path.join(HERE, name)) as fh:
        return list(csv.DictReader(fh))


def num(v):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def main():
    tm = read("df_tm.csv")
    tm1 = read("df_tm1.csv")
    pts = read("df_pts.csv")
    sch = read("df_sch.csv")

    # ---- owners + identities (one owner per SWID) -------------------------
    name_by_swid, persona_by_swid = {}, {}
    for r in sorted(tm1, key=lambda r: r["Year"]):
        nm = f"{(r['First'] or '').strip()} {(r['Last'] or '').strip()}".strip()
        nm = " ".join(w.capitalize() for w in nm.split()) or r["DisplayName"] or r["OwnerID"]
        name_by_swid[r["OwnerID"]] = nm
    for r in sorted(tm, key=lambda r: r["Year"]):
        persona_by_swid[r["OwnerID"]] = r["displayName"]

    owner_by_swid = {}
    existing = sb.table("owner_identities").select("owner_id, platform_user_id") \
        .eq("platform", PLATFORM).execute().data
    for row in existing:
        owner_by_swid[row["platform_user_id"]] = row["owner_id"]

    for swid, name in name_by_swid.items():
        if swid in owner_by_swid:
            continue
        oid = sb.table("owners").insert({"display_name": name}).execute().data[0]["owner_id"]
        sb.table("owner_identities").insert({
            "owner_id": oid, "platform": PLATFORM,
            "platform_user_id": swid, "platform_name": name,
        }).execute()
        owner_by_swid[swid] = oid
    print(f"owners: {len(owner_by_swid)}")

    # ---- seasons ----------------------------------------------------------
    years = sorted({r["Year"] for r in tm})
    sb.table("seasons").upsert(
        [{"platform": PLATFORM, "league_id": LEAGUE_ID, "year": int(y),
          "name": f"ESPN League {y}"} for y in years],
        on_conflict="platform,league_id,year",
    ).execute()
    season_by_year = {
        int(s["year"]): s["season_id"]
        for s in sb.table("seasons").select("season_id, year")
        .eq("platform", PLATFORM).eq("league_id", LEAGUE_ID).execute().data
    }
    print(f"seasons: {len(season_by_year)}")

    # ---- teams (dedup co-managed teams: keep first manager as primary) ----
    team_rows, seen = [], set()
    for r in tm:
        key = (season_by_year[int(r["Year"])], str(r["TeamID"]))
        if key in seen:
            continue  # secondary co-owner of the same team; skipped for now
        seen.add(key)
        team_rows.append({
            "season_id": key[0],
            "owner_id": owner_by_swid.get(r["OwnerID"]),
            "platform_roster_id": key[1],
            "team_name": persona_by_swid.get(r["OwnerID"]) or r["displayName"],
            "abbr": r["Abbr"],
        })
    sb.table("teams").upsert(team_rows, on_conflict="season_id,platform_roster_id").execute()
    team_by_key = {}  # (season_id, roster_id) -> team_id
    for s_id in season_by_year.values():
        for t in sb.table("teams").select("team_id, season_id, platform_roster_id") \
                .eq("season_id", s_id).execute().data:
            team_by_key[(t["season_id"], t["platform_roster_id"])] = t["team_id"]
    print(f"teams: {len(team_by_key)}")

    # ---- schedule lookup: (year, week, teamid) -> opp, pa, result, playoff -
    schmap = {}
    for r in sch:
        hp, ap = num(r["HomeTotalPoints"]) or 0, num(r["AwayTotalPoints"]) or 0
        isp = (r["Type"] or "").lower() != "regular"
        h, a = str(r["HomeTeamId"]), str(r["AwayTeamId"])
        res = lambda x, y: "T" if x == y else ("W" if x > y else "L")
        schmap[(r["Year"], r["Week"], h)] = (a, ap, res(hp, ap), isp)
        schmap[(r["Year"], r["Week"], a)] = (h, hp, res(ap, hp), isp)

    # ---- team_weeks -------------------------------------------------------
    rows = []
    for r in pts:
        s_id = season_by_year[int(r["Year"])]
        tid = team_by_key.get((s_id, str(r["TeamID"])))
        if not tid:
            continue
        opp, pa, result, isp = schmap.get((r["Year"], r["Week"], str(r["TeamID"])),
                                          (None, None, None, False))
        opp_tid = team_by_key.get((s_id, opp)) if opp else None
        rows.append({
            "team_id": tid, "week": int(r["Week"]), "is_playoff": isp,
            "points_for": num(r["Apts"]), "points_against": pa,
            "opponent_team_id": opp_tid, "result": result,
            "optimal_points": num(r["Opts"]), "expected_points": num(r["Epts"]),
        })
    for i in range(0, len(rows), 500):
        sb.table("team_weeks").upsert(rows[i:i + 500], on_conflict="team_id,week").execute()
    print(f"team_weeks: {len(rows)}")
    print("ESPN load complete.")


if __name__ == "__main__":
    main()
