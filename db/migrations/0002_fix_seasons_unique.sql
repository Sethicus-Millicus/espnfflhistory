-- ESPN reuses the same league_id across every season, so uniqueness must
-- include the year. (Sleeper uses a distinct league_id per season, so this
-- is still correct for Sleeper too.)
alter table seasons drop constraint if exists seasons_platform_league_id_key;
alter table seasons add constraint seasons_platform_league_year_key unique (platform, league_id, year);
