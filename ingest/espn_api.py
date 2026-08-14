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


def compute_pts(slates, posns, struc):
    """actual / optimal / projected-optimal points per team (see notebook)."""
    data = {}
    for tmid, slate in slates.items():
        pts = {"opts": 0, "epts": 0, "apts": 0}
        pts["apts"] = slate.query('Slot not in ["Bench", "IR"]').filter(["Actual"]).sum().values[0]

        for method, cat in [("Actual", "opts"), ("Proj", "epts")]:
            flex_candidates_act = []
            flex_candidates_proj = []
            fcp = []
            num = 0
            for pos, num in zip(posns, struc):
                sorted_slate = slate.query("Pos == @pos").sort_values(by=method, ascending=False)
                pts[cat] += sorted_slate.iloc[:num].filter(["Actual"]).sum().values[0]
                if pos in ["RB", "WR", "TE"] and len(sorted_slate) > num:
                    if method == "Proj":
                        flex_candidates_proj.append(sorted_slate.iloc[num:])
                    else:
                        flex_candidates_act.extend(sorted_slate.iloc[num:].filter(["Actual"]).values[:, 0])
            if flex_candidates_proj:
                fcp.extend(pd.concat(flex_candidates_proj).sort_values(by="Proj").iloc[num:]
                           .filter(["Actual"]).values[:, 0])
                pts[cat] += sum(fcp[-num:])
            if flex_candidates_act:
                pts[cat] += sum(sorted(flex_candidates_act, reverse=True)[:num])
        data[tmid] = {k: round(float(v), 1) for k, v in pts.items()}
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
