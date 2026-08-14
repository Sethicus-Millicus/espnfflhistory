# Ingestion scripts

All scripts load directly into Supabase. They must run **on your machine**
(this repo's cloud sessions are walled off from the ESPN and Sleeper APIs).

## One-time setup
```bash
pip install -r ingest/requirements.txt
cp .env.example .env      # then fill in the values
```

`.env` needs:
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — from Supabase Project Settings → API
- `ESPN_LEAGUE_ID`, `ESPN_SWID`, `ESPN_S2` — for ESPN pulls (SWID + espn_s2 from a
  logged-in browser session's cookies)
- `SLEEPER_LEAGUE_ID` — your current Sleeper league id

The `SUPABASE_SERVICE_ROLE_KEY` and ESPN cookies are secrets — `.env` is gitignored.

## What to run

| Command | Loads |
|---|---|
| `python ingest/load_espn_csv.py` | ESPN 2018–2023 from the repo CSVs (already loaded once) |
| `python ingest/pull_espn.py 2024` | ESPN 2024 scores + optimal/expected points (live API) |
| `python ingest/pull_espn_draft.py` | ESPN drafts 2018–2024 |
| `python ingest/pull_sleeper.py` | All Sleeper seasons: scores, optimal points, drafts |

All are idempotent — re-run any time (e.g. weekly) and they upsert.

## After loading Sleeper
Sleeper users come in as their own owner rows. Map each Sleeper account to its
existing ESPN owner so all-time stats span both platforms — tell me the
Sleeper-handle → person pairings and I'll merge them (same step we did for the
duplicate ESPN accounts).
