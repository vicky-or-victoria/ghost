-- Ghost of Ryukyu — Complete Schema v1.0
-- All tables scoped by guild_id. No data crosses Discord servers.

-- Migrations: add missing columns to pre-existing guild_config tables
DO $$ BEGIN
    ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS announcement_channel_id BIGINT;
    ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS hall_of_fame_channel_id  BIGINT;
    ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS leaderboard_channel_id   BIGINT;
    ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS commands_channel_id      BIGINT;
    ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS menu_channel_id          BIGINT;
    ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS menu_message_id          BIGINT;
    ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS gm_role_id               BIGINT;
EXCEPTION WHEN undefined_table THEN
    NULL;
END $$;

CREATE TABLE IF NOT EXISTS guild_config (
    guild_id                BIGINT PRIMARY KEY,
    announcement_channel_id BIGINT,
    hall_of_fame_channel_id BIGINT,
    leaderboard_channel_id  BIGINT,
    commands_channel_id     BIGINT,
    menu_channel_id         BIGINT,
    menu_message_id         BIGINT,
    gm_role_id              BIGINT,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS players (
    guild_id             BIGINT NOT NULL,
    owner_id             BIGINT NOT NULL,
    mc_first_name        TEXT NOT NULL,
    mc_gender            TEXT NOT NULL CHECK (mc_gender IN ('male','female')),
    current_act          INTEGER DEFAULT 0,
    current_scene        TEXT DEFAULT 'act0_enlistment',
    path_choice          TEXT CHECK (path_choice IN ('ghost','blade',NULL)),
    current_hex          TEXT DEFAULT '30,85',
    hp                   INTEGER DEFAULT 60,
    max_hp               INTEGER DEFAULT 60,
    atk                  INTEGER DEFAULT 8,
    def                  INTEGER DEFAULT 8,
    spd                  INTEGER DEFAULT 8,
    resolve              INTEGER DEFAULT 8,
    recon                INTEGER DEFAULT 8,
    loyalty              INTEGER DEFAULT 8,
    xp                   INTEGER DEFAULT 0,
    level                INTEGER DEFAULT 1,
    coin                 INTEGER DEFAULT 0,
    raw_metals           INTEGER DEFAULT 0,
    rare_metals          INTEGER DEFAULT 0,
    shimazu_steel        INTEGER DEFAULT 0,
    traits               JSONB DEFAULT '[]',
    perks                JSONB DEFAULT '[]',
    equipped_weapon      TEXT,
    equipped_weapon_tier INTEGER DEFAULT 1,
    equipped_armor       TEXT,
    equipped_armor_tier  INTEGER DEFAULT 1,
    is_alive             BOOLEAN DEFAULT TRUE,
    campaign_complete    BOOLEAN DEFAULT FALSE,
    grief_counter        INTEGER DEFAULT 0,
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (guild_id, owner_id)
);

CREATE TABLE IF NOT EXISTS companions (
    guild_id       BIGINT NOT NULL,
    owner_id       BIGINT NOT NULL,
    companion_name TEXT NOT NULL,
    trust_tier     INTEGER DEFAULT 0 CHECK (trust_tier BETWEEN 0 AND 4),
    hp             INTEGER DEFAULT 50,
    max_hp         INTEGER DEFAULT 50,
    atk            INTEGER DEFAULT 6,
    def            INTEGER DEFAULT 6,
    spd            INTEGER DEFAULT 10,
    resolve        INTEGER DEFAULT 8,
    recon          INTEGER DEFAULT 14,
    loyalty        INTEGER DEFAULT 8,
    xp             INTEGER DEFAULT 0,
    level          INTEGER DEFAULT 1,
    traits         JSONB DEFAULT '[]',
    is_conscious   BOOLEAN DEFAULT TRUE,
    is_present     BOOLEAN DEFAULT TRUE,
    times_unconscious INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, owner_id),
    FOREIGN KEY (guild_id, owner_id) REFERENCES players ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS band_members (
    id                 SERIAL PRIMARY KEY,
    guild_id           BIGINT NOT NULL,
    owner_id           BIGINT NOT NULL,
    member_name        TEXT NOT NULL,
    archetype          TEXT NOT NULL,
    hp                 INTEGER DEFAULT 80,
    max_hp             INTEGER DEFAULT 80,
    atk                INTEGER DEFAULT 8,
    def                INTEGER DEFAULT 8,
    spd                INTEGER DEFAULT 8,
    resolve            INTEGER DEFAULT 8,
    recon              INTEGER DEFAULT 8,
    individual_loyalty INTEGER DEFAULT 50,
    xp                 INTEGER DEFAULT 0,
    level              INTEGER DEFAULT 1,
    traits             JSONB DEFAULT '[]',
    injuries           JSONB DEFAULT '[]',
    is_alive           BOOLEAN DEFAULT TRUE,
    is_downed          BOOLEAN DEFAULT FALSE,
    battles_survived   INTEGER DEFAULT 0,
    kills              INTEGER DEFAULT 0,
    joined_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_band_owner ON band_members (guild_id, owner_id);

CREATE TABLE IF NOT EXISTS band_memorial (
    id                SERIAL PRIMARY KEY,
    guild_id          BIGINT NOT NULL,
    owner_id          BIGINT NOT NULL,
    member_name       TEXT NOT NULL,
    archetype         TEXT NOT NULL,
    cause_of_death    TEXT,
    traits_at_death   JSONB DEFAULT '[]',
    injuries_at_death JSONB DEFAULT '[]',
    battles_survived  INTEGER DEFAULT 0,
    kills             INTEGER DEFAULT 0,
    eulogy            TEXT,
    died_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS band_loyalty (
    guild_id BIGINT NOT NULL,
    owner_id BIGINT NOT NULL,
    loyalty  INTEGER DEFAULT 60,
    PRIMARY KEY (guild_id, owner_id),
    FOREIGN KEY (guild_id, owner_id) REFERENCES players ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS player_saves (
    guild_id    BIGINT NOT NULL,
    owner_id    BIGINT NOT NULL,
    slot_number INTEGER NOT NULL CHECK (slot_number IN (1,2)),
    act_label   TEXT,
    band_size   INTEGER DEFAULT 0,
    snapshot    JSONB NOT NULL,
    saved_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (guild_id, owner_id, slot_number)
);

CREATE TABLE IF NOT EXISTS overworld_hexes (
    guild_id          BIGINT NOT NULL,
    owner_id          BIGINT NOT NULL,
    address           TEXT NOT NULL,
    terrain           TEXT NOT NULL DEFAULT 'jungle',
    controller        TEXT NOT NULL DEFAULT 'neutral'
        CHECK (controller IN ('player','satsuma','neutral','ryukyuan')),
    is_explored       BOOLEAN DEFAULT FALSE,
    is_named_location BOOLEAN DEFAULT FALSE,
    location_name     TEXT,
    PRIMARY KEY (guild_id, owner_id, address)
);
CREATE INDEX IF NOT EXISTS idx_overworld_owner ON overworld_hexes (guild_id, owner_id);

CREATE TABLE IF NOT EXISTS satsuma_units (
    id          SERIAL PRIMARY KEY,
    guild_id    BIGINT NOT NULL,
    owner_id    BIGINT NOT NULL,
    unit_type   TEXT NOT NULL,
    unit_name   TEXT,
    behavior    TEXT NOT NULL DEFAULT 'patrol',
    hex_address TEXT NOT NULL,
    hp          INTEGER DEFAULT 80,
    max_hp      INTEGER DEFAULT 80,
    atk         INTEGER DEFAULT 8,
    def         INTEGER DEFAULT 8,
    spd         INTEGER DEFAULT 8,
    resolve     INTEGER DEFAULT 8,
    is_active   BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_satsuma_owner ON satsuma_units (guild_id, owner_id);

CREATE TABLE IF NOT EXISTS tactical_maps (
    guild_id         BIGINT NOT NULL,
    owner_id         BIGINT NOT NULL,
    hex_grid         JSONB NOT NULL DEFAULT '{}',
    unit_positions   JSONB NOT NULL DEFAULT '{}',
    turn_number      INTEGER DEFAULT 1,
    initiative_order JSONB DEFAULT '[]',
    is_active        BOOLEAN DEFAULT TRUE,
    combat_type      TEXT DEFAULT 'encounter',
    map_size         INTEGER DEFAULT 9,
    PRIMARY KEY (guild_id, owner_id)
);

CREATE TABLE IF NOT EXISTS story_flags (
    guild_id           BIGINT NOT NULL,
    owner_id           BIGINT NOT NULL,
    current_act        INTEGER DEFAULT 0,
    current_scene      TEXT DEFAULT 'act0_enlistment',
    path_choice        TEXT,
    flags              JSONB DEFAULT '{}',
    relationship_tiers JSONB DEFAULT '{}',
    PRIMARY KEY (guild_id, owner_id),
    FOREIGN KEY (guild_id, owner_id) REFERENCES players ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contracts (
    id            SERIAL PRIMARY KEY,
    guild_id      BIGINT NOT NULL,
    owner_id      BIGINT NOT NULL,
    template_type TEXT NOT NULL,
    status        TEXT DEFAULT 'available'
        CHECK (status IN ('available','active','complete','failed','abandoned')),
    difficulty    TEXT DEFAULT 'standard'
        CHECK (difficulty IN ('standard','dangerous','deadly','story')),
    title         TEXT,
    description   TEXT,
    objective_hex TEXT,
    reward        JSONB DEFAULT '{}',
    turns_allowed INTEGER,
    turns_elapsed INTEGER DEFAULT 0,
    generated_at  TIMESTAMPTZ DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_contracts_owner ON contracts (guild_id, owner_id, status);

CREATE TABLE IF NOT EXISTS faction_standing (
    guild_id          BIGINT NOT NULL,
    owner_id          BIGINT NOT NULL,
    satsuma_standing  INTEGER DEFAULT 1 CHECK (satsuma_standing BETWEEN 0 AND 3),
    ryukyuan_standing INTEGER DEFAULT 0 CHECK (ryukyuan_standing BETWEEN 0 AND 3),
    village_standings JSONB DEFAULT '{}',
    PRIMARY KEY (guild_id, owner_id),
    FOREIGN KEY (guild_id, owner_id) REFERENCES players ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS items (
    id            SERIAL PRIMARY KEY,
    guild_id      BIGINT NOT NULL,
    owner_id      BIGINT NOT NULL,
    item_key      TEXT NOT NULL,
    quantity      INTEGER DEFAULT 1,
    is_relic      BOOLEAN DEFAULT FALSE,
    equipped_slot TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_owner ON items (guild_id, owner_id);

CREATE TABLE IF NOT EXISTS trait_tracker (
    id            SERIAL PRIMARY KEY,
    guild_id      BIGINT NOT NULL,
    owner_id      BIGINT NOT NULL,
    unit_id       TEXT NOT NULL,
    counter_key   TEXT NOT NULL,
    counter_value INTEGER DEFAULT 0,
    UNIQUE (guild_id, owner_id, unit_id, counter_key)
);
CREATE INDEX IF NOT EXISTS idx_trait_owner ON trait_tracker (guild_id, owner_id, unit_id);

CREATE TABLE IF NOT EXISTS pvp_records (
    id            SERIAL PRIMARY KEY,
    guild_id      BIGINT NOT NULL,
    challenger_id BIGINT NOT NULL,
    defender_id   BIGINT NOT NULL,
    winner_id     BIGINT,
    result        TEXT CHECK (result IN ('challenger','defender','draw')),
    occurred_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hall_of_fame (
    id                SERIAL PRIMARY KEY,
    guild_id          BIGINT NOT NULL,
    owner_id          BIGINT NOT NULL,
    mc_name           TEXT NOT NULL,
    mc_gender         TEXT NOT NULL,
    path_choice       TEXT,
    act_reached       INTEGER DEFAULT 0,
    total_kills       INTEGER DEFAULT 0,
    band_members_lost INTEGER DEFAULT 0,
    contracts_done    INTEGER DEFAULT 0,
    hall_traits       JSONB DEFAULT '[]',
    ended_by          TEXT CHECK (ended_by IN ('mc_death','campaign_complete')),
    ended_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leaderboard_cache (
    guild_id            BIGINT NOT NULL,
    owner_id            BIGINT NOT NULL,
    mc_name             TEXT,
    contracts_completed INTEGER DEFAULT 0,
    enemies_killed      INTEGER DEFAULT 0,
    act_reached         INTEGER DEFAULT 0,
    band_members_lost   INTEGER DEFAULT 0,
    pvp_wins            INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, owner_id)
);

CREATE TABLE IF NOT EXISTS movement_arrows (
    guild_id  BIGINT NOT NULL,
    owner_id  BIGINT NOT NULL,
    from_addr TEXT,
    to_addr   TEXT,
    side      TEXT,
    PRIMARY KEY (guild_id, owner_id)
);

CREATE TABLE IF NOT EXISTS combat_log (
    id                SERIAL PRIMARY KEY,
    guild_id          BIGINT NOT NULL,
    owner_id          BIGINT NOT NULL,
    participants      JSONB DEFAULT '{}',
    outcome           TEXT,
    casualties        JSONB DEFAULT '[]',
    xp_gained         INTEGER DEFAULT 0,
    loyalty_delta     INTEGER DEFAULT 0,
    tactical_map_seed TEXT,
    occurred_at       TIMESTAMPTZ DEFAULT NOW()
);