"""ESPN fantasy API client + the optimal/expected points logic, ported
verbatim (in behavior) from FFL_Analysis.ipynb so new seasons are computed
the same way as the 2018-2023 history already in the database.
"""
import os

import pandas as pd
import requests

READ_HOST = "https://lm-api-reads.fantasy.espn.com"

SLOTCODES = {
    0: "QB", 1: "QB", 2: "RB", 3: "RB", 4: "WR", 5: "WR",
    6: "TE", 7: "TE", 16: "D/ST", 17: "K", 20: "Bench", 21: "IR", 23: "Flex",
}

# Roster structures by era (posns / slots-per-position), matching the notebook.
# 2018-2020 carried a kicker; 2021+ replaced K with a second flex.
STRUCTURE_WITH_K = (["QB", "RB", "WR", "Flex", "TE", "D/ST", "K"], [1, 2, 2, 1, 1, 1, 1])
STRUCTURE_NO_K = (["QB", "RB", "WR", "Flex", "TE", "D/ST"], [1, 2, 2, 2, 1, 1, 1])


def structure_for(year):
    return STRUCTURE_WITH_K if int(year) <= 2020 else STRUCTURE_NO_K


def _cookies():
    return {"SWID": os.environ.get("ESPN_SWID", ""),
            "espn_s2": os.environ.get("ESPN_S2", "")}


def get_view(league_id, season, view, week=None):
    url = f"{READ_HOST}/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{league_id}"
    params = {"view": view}
    if week is not None:
        params["scoringPeriodId"] = week
    r = requests.get(url, params=params, cookies=_cookies(), timeout=30)
    r.raise_for_status()
    return r.json()


def get_matchups(league_id, season, week):
    url = (f"{READ_HOST}/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/"
           f"{league_id}?scoringPeriodId={week}&view=mMatchup&view=mMatchupScore")
    r = requests.get(url, cookies=_cookies(), timeout=30)
    r.raise_for_status()
    return r.json()


def get_slates(d, season, week):
    """Per-team DataFrame of players with slot, position, actual & projected pts."""
    slates = {}
    for team in d["teams"]:
        slate = []
        for p in team["roster"]["entries"]:
            ppe = p.get("playerPoolEntry")
            if not (ppe and ppe.get("player")):
                continue
            player = ppe["player"]
            name = player["fullName"]
            slotid = p["lineupSlotId"]
            slot = SLOTCODES.get(slotid, "Unk")

            act, proj = 0, 0
            for stat in player["stats"]:
                if stat["scoringPeriodId"] != week:
                    continue
                if stat["statSourceId"] == 0:
                    act = stat["appliedTotal"]
                elif stat["statSourceId"] == 1:
                    proj = stat["appliedTotal"]

            ess = player["eligibleSlots"]
            pos = "Unk"
            for slot_id, label in [(0, "QB"), (2, "RB"), (4, "WR"), (6, "TE"),
                                   (16, "D/ST"), (17, "K")]:
                if slot_id in ess:
                    pos = label
                    break

            slate.append([name, season, week, slotid, slot, pos, act, proj])
        slates[team["id"]] = pd.DataFrame(
            slate, columns=["Name", "Year", "Week", "SlotID", "Slot", "Pos", "Actual", "Proj"])
    return slates


FLEX_ELIGIBLE = ("RB", "WR", "TE")


def _best_lineup(slate, slots, metric):
    """Fill the starting `slots` greedily by `metric`, return the ACTUAL points
    of the chosen players. Fixed slots take the best of their position; Flex
    takes the best remaining RB/WR/TE. For standard nested flex this yields the
    true optimum, so the result is always >= the actual lineup's score.
    """
    pools = {}  # pos -> list of (metric_val, actual_val) sorted desc by metric
    for _, r in slate.iterrows():
        pools.setdefault(r["Pos"], []).append((r[metric], r["Actual"]))
    for pos in pools:
        pools[pos].sort(key=lambda x: x[0], reverse=True)

    total, flex_slots = 0.0, []
    for slot in slots:
        if slot == "Flex":
            flex_slots.append(slot)
            continue
        pool = pools.get(slot)  # QB / RB / WR / TE / K / D/ST
        if pool:
            total += pool.pop(0)[1]
    for _ in flex_slots:
        best_pos, best_val = None, None
        for pos in FLEX_ELIGIBLE:
            if pools.get(pos) and (best_val is None or pools[pos][0][0] > best_val):
                best_pos, best_val = pos, pools[pos][0][0]
        if best_pos is not None:
            total += pools[best_pos].pop(0)[1]
    return total


def compute_pts(slates, posns, struc):
    """actual / optimal / projection-optimal points per team.

    - apts: points from the lineup actually started
    - opts: points from the best-possible lineup (chosen by actual points)
    - epts: points from the lineup the ESPN projections would have set
    """
    slots = []
    for pos, n in zip(posns, struc):
        slots += [pos] * n
    data = {}
    for tmid, slate in slates.items():
        apts = slate.query('Slot not in ["Bench", "IR"]')["Actual"].sum()
        data[tmid] = {
            "apts": round(float(apts), 1),
            "opts": round(float(_best_lineup(slate, slots, "Actual")), 1),
            "epts": round(float(_best_lineup(slate, slots, "Proj")), 1),
        }
    return data


def get_players(league_id, season):
    """id -> {name, pos, pro_team} for every player in a season (for drafts)."""
    url = f"{READ_HOST}/apis/v3/games/ffl/seasons/{season}/players?view=players_wl"
    headers = {"x-fantasy-filter": '{"filterActive":{"value":true}}'}
    r = requests.get(url, params={"scoringPeriodId": 0, "view": "players_wl"},
                     headers=headers, cookies=_cookies(), timeout=60)
    r.raise_for_status()
    pos_map = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "D/ST"}
    out = {}
    for p in r.json():
        out[p["id"]] = {
            "name": p.get("fullName"),
            "pos": pos_map.get(p.get("defaultPositionId")),
            "pro_team": p.get("proTeamId"),
        }
    return out
