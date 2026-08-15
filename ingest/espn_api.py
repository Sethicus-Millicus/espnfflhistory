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


# Which positions each starting slot label can be filled by. Derived from the
# actual lineup, so we never assume a league's roster shape.
SLOT_ELIGIBLE = {
    "QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}, "TE": {"TE"},
    "K": {"K"}, "D/ST": {"D/ST"},
    "Flex": {"RB", "WR", "TE"},
    "OP": {"QB", "RB", "WR", "TE"},          # superflex, if ever used
}
BENCH_SLOTS = {"Bench", "IR"}


def _best_lineup(slate, slots, metric):
    """Optimally fill the given starting `slots` from the whole roster, ranking
    by `metric`, and return the ACTUAL points of the chosen players. Single-
    position slots are filled first, then flex-type slots take the best eligible
    player left. Because the actually-started lineup is one feasible filling of
    these same slots, the result is always >= the started lineup's score.
    """
    pools = {}  # pos -> [(metric_val, actual_val)] sorted desc by metric
    for _, r in slate.iterrows():
        pools.setdefault(r["Pos"], []).append((r[metric], r["Actual"]))
    for pos in pools:
        pools[pos].sort(key=lambda x: x[0], reverse=True)

    singles = [s for s in slots if len(SLOT_ELIGIBLE.get(s, ())) == 1]
    multis = [s for s in slots if len(SLOT_ELIGIBLE.get(s, ())) > 1]
    total = 0.0
    for slot in singles:
        pos = next(iter(SLOT_ELIGIBLE[slot]))
        if pools.get(pos):
            total += pools[pos].pop(0)[1]
    for slot in multis:
        best_pos, best_val = None, None
        for pos in SLOT_ELIGIBLE[slot]:
            if pools.get(pos) and (best_val is None or pools[pos][0][0] > best_val):
                best_pos, best_val = pos, pools[pos][0][0]
        if best_pos is not None:
            total += pools[best_pos].pop(0)[1]
    return total


def compute_pts(slates, *_ignored):
    """actual / optimal / projection-optimal points per team.

    The starting-slot structure is read from each team's actual lineup (the
    non-bench slots they started), so no roster assumptions are made and optimal
    is always >= actual. Extra positional args are ignored for back-compat.
    """
    data = {}
    for tmid, slate in slates.items():
        started = slate[~slate["Slot"].isin(BENCH_SLOTS)]
        apts = started["Actual"].sum()
        slots = list(started["Slot"])          # the exact slots they started
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
