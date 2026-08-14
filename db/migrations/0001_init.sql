-- Fantasy Football History — core schema
-- One person = one `owner`, across every platform and season.
-- Public dashboard: anon role gets read-only; writes happen via the
-- service_role key used by the ingestion scripts.

-- ---------------------------------------------------------------------------
-- WHO
-- ---------------------------------------------------------------------------
create table if not exists owners (
    owner_id     bigint generated always as identity primary key,
    display_name text not null,          -- canonical name shown to the league
    notes        text,
    created_at   timestamptz not null default now()
);

-- Links a person to each platform account they've used. This is the keystone
-- that makes cross-platform (ESPN + Sleeper) all-time stats possible.
create table if not exists owner_identities (
    owner_id         bigint not null references owners(owner_id) on delete cascade,
    platform         text   not null check (platform in ('espn', 'sleeper')),
    platform_user_id text   not null,    -- ESPN SWID or Sleeper user_id
    platform_name    text,               -- what that platform called them
    primary key (platform, platform_user_id)
);
create index if not exists owner_identities_owner_idx on owner_identities(owner_id);

-- ---------------------------------------------------------------------------
-- WHEN / WHERE
-- ---------------------------------------------------------------------------
create table if not exists seasons (
    season_id  bigint generated always as identity primary key,
    platform   text not null check (platform in ('espn', 'sleeper')),
    league_id  text not null,            -- the platform's league id
    year       int  not null,
    name       text,
    settings   jsonb not null default '{}'::jsonb,   -- playoff weeks, scoring, roster slots
    unique (platform, league_id)
);
create index if not exists seasons_year_idx on seasons(year);

-- ---------------------------------------------------------------------------
-- A team = an owner's entry in one season
-- ---------------------------------------------------------------------------
create table if not exists teams (
    team_id            bigint generated always as identity primary key,
    season_id          bigint not null references seasons(season_id) on delete cascade,
    owner_id           bigint references owners(owner_id) on delete set null,  -- filled once identities are mapped
    platform_roster_id text not null,    -- Sleeper roster_id / ESPN teamId
    team_name          text,
    abbr               text,
    unique (season_id, platform_roster_id)
);
create index if not exists teams_owner_idx  on teams(owner_id);
create index if not exists teams_season_idx on teams(season_id);

-- ---------------------------------------------------------------------------
-- THE FACT TABLE: one row per team, per week (unifies matchups + points)
-- ---------------------------------------------------------------------------
create table if not exists team_weeks (
    team_id          bigint not null references teams(team_id) on delete cascade,
    week             int    not null,
    is_playoff       boolean not null default false,
    points_for       numeric,
    points_against   numeric,
    opponent_team_id bigint references teams(team_id) on delete set null,
    result           text check (result in ('W', 'L', 'T')),
    optimal_points   numeric,            -- best-possible lineup that week
    expected_points  numeric,            -- expected-points metric
    primary key (team_id, week)
);
create index if not exists team_weeks_opponent_idx on team_weeks(opponent_team_id);

-- ---------------------------------------------------------------------------
-- DRAFTS
-- ---------------------------------------------------------------------------
create table if not exists drafts (
    draft_id          bigint generated always as identity primary key,
    season_id         bigint not null references seasons(season_id) on delete cascade,
    platform_draft_id text,
    type              text,              -- snake | auction | linear
    rounds            int,
    settings          jsonb not null default '{}'::jsonb,
    unique (season_id)
);

create table if not exists draft_picks (
    draft_id    bigint not null references drafts(draft_id) on delete cascade,
    round       int    not null,
    pick_no     int    not null,         -- overall pick number
    team_id     bigint references teams(team_id) on delete set null,  -- who drafted
    player_name text,
    position    text,
    nfl_team    text,
    amount      int,                     -- auction $ (null for snake)
    is_keeper   boolean not null default false,
    primary key (draft_id, pick_no)
);
create index if not exists draft_picks_team_idx on draft_picks(team_id);

-- ---------------------------------------------------------------------------
-- Row-level security: public read, service-role write
-- ---------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array[
    'owners','owner_identities','seasons','teams','team_weeks','drafts','draft_picks'
  ]
  loop
    execute format('alter table %I enable row level security;', t);
    execute format(
      'drop policy if exists "public read" on %I;', t);
    execute format(
      'create policy "public read" on %I for select to anon, authenticated using (true);', t);
  end loop;
end $$;
