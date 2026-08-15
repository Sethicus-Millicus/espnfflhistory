-- Final finishing position + playoff appearance per team-season, so champions,
-- runners-up, last place, and "made playoffs %" derive from data.
-- ESPN provides rankCalculatedFinal directly; Sleeper is derived from its
-- winners/losers bracket endpoints.
alter table teams add column if not exists final_rank int;
alter table teams add column if not exists made_playoffs boolean;
