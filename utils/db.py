import asyncpg
import os
import json
import logging

log = logging.getLogger(__name__)
_pool: asyncpg.Pool | None = None


async def init_pool():
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=os.environ["DATABASE_URL"],
        min_size=2, max_size=10, command_timeout=30
    )
    await _apply_schema()
    log.info("DB pool ready.")


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Pool not initialised.")
    return _pool


async def _apply_schema():
    path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
    sql  = open(path).read()
    async with _pool.acquire() as c:
        statements = _split_sql(sql)
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                await c.execute(stmt)
            except Exception as e:
                log.warning("Schema stmt warning: %s", e)
    log.info("Schema applied.")


def _split_sql(sql: str) -> list:
    """Split SQL on semicolons, respecting $$ dollar-quote blocks."""
    statements = []
    current    = []
    in_dollar  = False
    i          = 0
    while i < len(sql):
        if sql[i:i+2] == "$$":
            in_dollar = not in_dollar
            current.append("$$")
            i += 2
            continue
        if sql[i] == ";" and not in_dollar:
            current.append(";")
            statements.append("".join(current))
            current = []
            i += 1
            continue
        current.append(sql[i])
        i += 1
    if "".join(current).strip():
        statements.append("".join(current))
    return statements


# JSONB normalisation helper
_JSONB_COLS = {
    "players":          ("traits","perks"),
    "companions":       ("traits",),
    "band_members":     ("traits","injuries"),
    "band_memorial":    ("traits_at_death","injuries_at_death"),
    "story_flags":      ("flags","relationship_tiers"),
    "contracts":        ("reward",),
    "faction_standing": ("village_standings",),
    "items":            (),
    "player_saves":     ("snapshot",),
    "tactical_maps":    ("hex_grid","unit_positions","initiative_order"),
    "hall_of_fame":     ("hall_traits",),
    "leaderboard_cache":(),
}

def _norm(row: dict, cols: tuple) -> dict:
    """Parse any JSONB columns that asyncpg returned as strings."""
    for col in cols:
        val = row.get(col)
        if isinstance(val, str):
            try:
                row[col] = json.loads(val)
            except Exception:
                row[col] = {}
        elif val is None:
            row[col] = [] if col in ("traits","perks","injuries","traits_at_death",
                                      "injuries_at_death","hall_traits","initiative_order") else {}
    return row


# Guild config

async def get_guild_config(guild_id: int) -> dict | None:
    async with _pool.acquire() as c:
        r = await c.fetchrow("SELECT * FROM guild_config WHERE guild_id=$1", guild_id)
        return dict(r) if r else None


async def upsert_guild_config(guild_id: int, **kw):
    fields = list(kw.keys())
    values = list(kw.values())
    cols   = ",".join(fields)
    phs    = ",".join(f"${i+2}" for i in range(len(fields)))
    sets   = ",".join(f"{f}=${i+2}" for i, f in enumerate(fields))
    async with _pool.acquire() as c:
        await c.execute(
            f"INSERT INTO guild_config (guild_id,{cols}) VALUES ($1,{phs}) "
            f"ON CONFLICT (guild_id) DO UPDATE SET {sets}",
            guild_id, *values
        )


# Players

async def get_player(guild_id: int, owner_id: int) -> dict | None:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT * FROM players WHERE guild_id=$1 AND owner_id=$2", guild_id, owner_id
        )
        return _norm(dict(r), _JSONB_COLS["players"]) if r else None


async def create_player(guild_id: int, owner_id: int, first_name: str, gender: str) -> dict:
    comp = "Nabi" if gender == "male" else "Kenji"
    async with _pool.acquire() as c:
        async with c.transaction():
            r = await c.fetchrow(
                "INSERT INTO players (guild_id,owner_id,mc_first_name,mc_gender) "
                "VALUES ($1,$2,$3,$4) RETURNING *",
                guild_id, owner_id, first_name, gender
            )
            await c.execute(
                "INSERT INTO companions (guild_id,owner_id,companion_name) VALUES ($1,$2,$3)",
                guild_id, owner_id, comp
            )
            await c.execute(
                "INSERT INTO band_loyalty (guild_id,owner_id) VALUES ($1,$2)", guild_id, owner_id
            )
            await c.execute(
                "INSERT INTO story_flags (guild_id,owner_id) VALUES ($1,$2)", guild_id, owner_id
            )
            await c.execute(
                "INSERT INTO faction_standing (guild_id,owner_id) VALUES ($1,$2)", guild_id, owner_id
            )
            await c.execute(
                "INSERT INTO leaderboard_cache (guild_id,owner_id,mc_name) VALUES ($1,$2,$3) "
                "ON CONFLICT DO NOTHING",
                guild_id, owner_id, f"Shimazu {first_name}"
            )
    return dict(r)


_PLAYER_JSONB = {"traits", "perks"}
_PLAYER_COL_MAP = {"def_": "def"}  # Python keyword workaround

async def update_player(guild_id: int, owner_id: int, **kw):
    if not kw:
        return
    # Remap reserved keyword aliases and serialize JSONB columns
    clean = {}
    for k, v in kw.items():
        col = _PLAYER_COL_MAP.get(k, k)
        if col in _PLAYER_JSONB and not isinstance(v, str):
            v = json.dumps(v)
        clean[col] = v
    fields = list(clean.keys())
    values = list(clean.values())
    sets   = ",".join(f'"{f}"=${i+3}' for i, f in enumerate(fields))
    async with _pool.acquire() as c:
        await c.execute(
            f"UPDATE players SET {sets} WHERE guild_id=$1 AND owner_id=$2",
            guild_id, owner_id, *values
        )


async def update_scene(guild_id: int, owner_id: int, act: int, scene: str):
    async with _pool.acquire() as c:
        await c.execute(
            "UPDATE players SET current_act=$3,current_scene=$4 WHERE guild_id=$1 AND owner_id=$2",
            guild_id, owner_id, act, scene
        )
        await c.execute(
            "UPDATE story_flags SET current_act=$3,current_scene=$4 WHERE guild_id=$1 AND owner_id=$2",
            guild_id, owner_id, act, scene
        )


# Companions

async def get_companion(guild_id: int, owner_id: int) -> dict | None:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT * FROM companions WHERE guild_id=$1 AND owner_id=$2", guild_id, owner_id
        )
        return _norm(dict(r), _JSONB_COLS["companions"]) if r else None


_COMPANION_JSONB = {"traits"}

async def update_companion(guild_id: int, owner_id: int, **kw):
    if not kw:
        return
    clean = {}
    for k, v in kw.items():
        if k in _COMPANION_JSONB and not isinstance(v, str):
            v = json.dumps(v)
        clean[k] = v
    fields = list(clean.keys())
    values = list(clean.values())
    sets   = ",".join(f'"{f}"=${i+3}' for i, f in enumerate(fields))
    async with _pool.acquire() as c:
        await c.execute(
            f"UPDATE companions SET {sets} WHERE guild_id=$1 AND owner_id=$2",
            guild_id, owner_id, *values
        )


# Band

async def get_band(guild_id: int, owner_id: int) -> list:
    async with _pool.acquire() as c:
        rs = await c.fetch(
            "SELECT * FROM band_members WHERE guild_id=$1 AND owner_id=$2 AND is_alive=TRUE ORDER BY id",
            guild_id, owner_id
        )
        return [_norm(dict(r), _JSONB_COLS["band_members"]) for r in rs]


async def get_band_size(guild_id: int, owner_id: int) -> int:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT COUNT(*) AS n FROM band_members WHERE guild_id=$1 AND owner_id=$2 AND is_alive=TRUE",
            guild_id, owner_id
        )
        return r["n"]


async def get_band_member(member_id: int) -> dict | None:
    async with _pool.acquire() as c:
        r = await c.fetchrow("SELECT * FROM band_members WHERE id=$1", member_id)
        return _norm(dict(r), _JSONB_COLS["band_members"]) if r else None


async def add_band_member(guild_id: int, owner_id: int, name: str, archetype: str, stats: dict) -> dict:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "INSERT INTO band_members "
            "(guild_id,owner_id,member_name,archetype,hp,max_hp,atk,def,spd,resolve,recon,individual_loyalty) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) RETURNING *",
            guild_id, owner_id, name, archetype,
            stats.get("hp",80), stats.get("max_hp",80),
            stats.get("atk",8), stats.get("def",8),
            stats.get("spd",8), stats.get("resolve",8),
            stats.get("recon",8), stats.get("individual_loyalty",50)
        )
        return dict(r)


_BAND_JSONB = {"traits", "injuries"}

async def update_band_member(member_id: int, **kw):
    if not kw:
        return
    clean = {}
    for k, v in kw.items():
        if k in _BAND_JSONB and not isinstance(v, str):
            v = json.dumps(v)
        clean[k] = v
    fields = list(clean.keys())
    values = list(clean.values())
    sets   = ",".join(f'"{f}"=${i+2}' for i, f in enumerate(fields))
    async with _pool.acquire() as c:
        await c.execute(f"UPDATE band_members SET {sets} WHERE id=$1", member_id, *values)


async def down_band_member(member_id: int):
    async with _pool.acquire() as c:
        await c.execute("UPDATE band_members SET is_downed=TRUE,hp=0 WHERE id=$1", member_id)


async def stabilize_band_member(member_id: int):
    async with _pool.acquire() as c:
        await c.execute("UPDATE band_members SET is_downed=FALSE,hp=5 WHERE id=$1", member_id)


async def kill_band_member(guild_id: int, owner_id: int, member_id: int, cause: str = "killed in battle"):
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT * FROM band_members WHERE id=$1 AND guild_id=$2 AND owner_id=$3",
            member_id, guild_id, owner_id
        )
        if not r:
            return
        m = dict(r)
        await c.execute("UPDATE band_members SET is_alive=FALSE,is_downed=FALSE WHERE id=$1", member_id)
        eulogy = _gen_eulogy(m)
        await c.execute(
            "INSERT INTO band_memorial "
            "(guild_id,owner_id,member_name,archetype,cause_of_death,"
            "traits_at_death,injuries_at_death,battles_survived,kills,eulogy) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)",
            guild_id, owner_id, m["member_name"], m["archetype"], cause,
            json.dumps(m.get("traits") or []), json.dumps(m.get("injuries") or []),
            m["battles_survived"], m["kills"], eulogy
        )
        await increment_leaderboard(guild_id, owner_id, "band_members_lost")


def _gen_eulogy(m: dict) -> str:
    traits = m.get("traits") or []
    lines  = [f"{m['member_name']} — {m['archetype']}."]
    if m["battles_survived"]:
        lines.append(f"Survived {m['battles_survived']} battle{'s' if m['battles_survived']!=1 else ''}. "
                     f"Killed {m['kills']} {'enemies' if m['kills']!=1 else 'enemy'}.")
    if "Veteran"  in traits: lines.append("A veteran. The band felt it when they fell.")
    if "Fearless" in traits: lines.append("Never routed. Not once.")
    if "Iron Will" in traits: lines.append("Survived things that should have finished them. Until they didn't.")
    if "Beloved"  in traits: lines.append("They were beloved. The gap they left was that wide.")
    lines.append("They are not forgotten.")
    return " ".join(lines)


async def get_memorial(guild_id: int, owner_id: int) -> list:
    async with _pool.acquire() as c:
        rs = await c.fetch(
            "SELECT * FROM band_memorial WHERE guild_id=$1 AND owner_id=$2 ORDER BY died_at DESC",
            guild_id, owner_id
        )
        return [dict(r) for r in rs]


# Band loyalty

async def get_loyalty(guild_id: int, owner_id: int) -> int:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT loyalty FROM band_loyalty WHERE guild_id=$1 AND owner_id=$2", guild_id, owner_id
        )
        return r["loyalty"] if r else 60


async def adjust_loyalty(guild_id: int, owner_id: int, delta: int) -> int:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "UPDATE band_loyalty SET loyalty=GREATEST(0,LEAST(100,loyalty+$3)) "
            "WHERE guild_id=$1 AND owner_id=$2 RETURNING loyalty",
            guild_id, owner_id, delta
        )
        return r["loyalty"] if r else 0


async def set_loyalty(guild_id: int, owner_id: int, value: int):
    async with _pool.acquire() as c:
        await c.execute(
            "UPDATE band_loyalty SET loyalty=GREATEST(0,LEAST(100,$3)) WHERE guild_id=$1 AND owner_id=$2",
            guild_id, owner_id, value
        )


# Story flags

async def get_story_flags(guild_id: int, owner_id: int) -> dict:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT * FROM story_flags WHERE guild_id=$1 AND owner_id=$2", guild_id, owner_id
        )
        if not r:
            return {}
        row = dict(r)
        # asyncpg may return JSONB columns as strings — normalise here
        for col in ("flags", "relationship_tiers"):
            val = row.get(col)
            if isinstance(val, str):
                row[col] = json.loads(val)
            elif val is None:
                row[col] = {}
        return row


async def update_story_flags(guild_id: int, owner_id: int, **kw):
    row   = await get_story_flags(guild_id, owner_id)
    flags = dict(row.get("flags") or {})
    flags.update(kw)
    async with _pool.acquire() as c:
        await c.execute(
            "UPDATE story_flags SET flags=$3 WHERE guild_id=$1 AND owner_id=$2",
            guild_id, owner_id, json.dumps(flags)
        )


# Items / inventory

async def get_items(guild_id: int, owner_id: int) -> list:
    async with _pool.acquire() as c:
        rs = await c.fetch(
            "SELECT * FROM items WHERE guild_id=$1 AND owner_id=$2 ORDER BY is_relic DESC,item_key",
            guild_id, owner_id
        )
        return [dict(r) for r in rs]


async def add_item(guild_id: int, owner_id: int, item_key: str, qty: int = 1, is_relic: bool = False):
    async with _pool.acquire() as c:
        # Always deduplicate by item_key — relics are unique, stackables accumulate qty
        ex = await c.fetchrow(
            "SELECT id,quantity FROM items WHERE guild_id=$1 AND owner_id=$2 AND item_key=$3",
            guild_id, owner_id, item_key
        )
        if ex:
            if not is_relic:
                await c.execute("UPDATE items SET quantity=quantity+$2 WHERE id=$1", ex["id"], qty)
            return  # Relic already exists — never duplicate
        await c.execute(
            "INSERT INTO items (guild_id,owner_id,item_key,quantity,is_relic) VALUES ($1,$2,$3,$4,$5)",
            guild_id, owner_id, item_key, qty, is_relic
        )


async def remove_item(guild_id: int, owner_id: int, item_key: str, qty: int = 1) -> bool:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT id,quantity FROM items WHERE guild_id=$1 AND owner_id=$2 AND item_key=$3",
            guild_id, owner_id, item_key
        )
        if not r or r["quantity"] < qty:
            return False
        if r["quantity"] == qty:
            await c.execute("DELETE FROM items WHERE id=$1", r["id"])
        else:
            await c.execute("UPDATE items SET quantity=quantity-$2 WHERE id=$1", r["id"], qty)
        return True


async def has_item(guild_id: int, owner_id: int, item_key: str) -> bool:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT id FROM items WHERE guild_id=$1 AND owner_id=$2 AND item_key=$3",
            guild_id, owner_id, item_key
        )
        return r is not None


# Faction standing

async def get_faction_standing(guild_id: int, owner_id: int) -> dict:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT * FROM faction_standing WHERE guild_id=$1 AND owner_id=$2", guild_id, owner_id
        )
        return dict(r) if r else {}


async def adjust_faction_standing(guild_id: int, owner_id: int, faction: str, delta: int):
    field = "satsuma_standing" if faction == "satsuma" else "ryukyuan_standing"
    async with _pool.acquire() as c:
        await c.execute(
            f"UPDATE faction_standing SET {field}=GREATEST(0,LEAST(3,{field}+$3)) "
            f"WHERE guild_id=$1 AND owner_id=$2",
            guild_id, owner_id, delta
        )


async def set_village_standing(guild_id: int, owner_id: int, village: str, value: int):
    row = await get_faction_standing(guild_id, owner_id)
    standings = dict(row.get("village_standings") or {})
    standings[village] = max(0, min(3, value))
    async with _pool.acquire() as c:
        await c.execute(
            "UPDATE faction_standing SET village_standings=$3 WHERE guild_id=$1 AND owner_id=$2",
            guild_id, owner_id, json.dumps(standings)
        )


# Trait tracker

async def increment_trait_counter(guild_id: int, owner_id: int, unit_id: str, key: str, amt: int = 1):
    async with _pool.acquire() as c:
        await c.execute(
            "INSERT INTO trait_tracker (guild_id,owner_id,unit_id,counter_key,counter_value) "
            "VALUES ($1,$2,$3,$4,$5) ON CONFLICT (guild_id,owner_id,unit_id,counter_key) "
            "DO UPDATE SET counter_value=trait_tracker.counter_value+$5",
            guild_id, owner_id, unit_id, key, amt
        )


async def get_trait_counters(guild_id: int, owner_id: int, unit_id: str) -> dict:
    async with _pool.acquire() as c:
        rs = await c.fetch(
            "SELECT counter_key,counter_value FROM trait_tracker "
            "WHERE guild_id=$1 AND owner_id=$2 AND unit_id=$3",
            guild_id, owner_id, unit_id
        )
        return {r["counter_key"]: r["counter_value"] for r in rs}


# Contracts

_CONTRACT_JSONB = ("reward",)

def _norm_contract(d: dict) -> dict:
    for col in _CONTRACT_JSONB:
        val = d.get(col)
        if isinstance(val, str):
            try:
                d[col] = json.loads(val)
            except Exception:
                d[col] = {}
        elif val is None:
            d[col] = {}
    return d

async def get_contracts(guild_id: int, owner_id: int, status: str = "available") -> list:
    async with _pool.acquire() as c:
        rs = await c.fetch(
            "SELECT * FROM contracts WHERE guild_id=$1 AND owner_id=$2 AND status=$3 ORDER BY generated_at DESC",
            guild_id, owner_id, status
        )
        return [_norm_contract(dict(r)) for r in rs]


async def get_active_contract(guild_id: int, owner_id: int) -> dict | None:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT * FROM contracts WHERE guild_id=$1 AND owner_id=$2 AND status='active'",
            guild_id, owner_id
        )
        return _norm_contract(dict(r)) if r else None


async def create_contract(guild_id: int, owner_id: int, data: dict) -> dict:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "INSERT INTO contracts (guild_id,owner_id,template_type,status,difficulty,"
            "title,description,objective_hex,reward,turns_allowed) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING *",
            guild_id, owner_id,
            data["template_type"], data.get("status","available"),
            data.get("difficulty","standard"), data.get("title",""),
            data.get("description",""), data.get("objective_hex"),
            json.dumps(data.get("reward",{})), data.get("turns_allowed")
        )
        return dict(r)


async def update_contract(contract_id: int, **kw):
    if not kw:
        return
    fields = list(kw.keys())
    values = list(kw.values())
    sets   = ",".join(f"{f}=${i+2}" for i, f in enumerate(fields))
    async with _pool.acquire() as c:
        await c.execute(f"UPDATE contracts SET {sets} WHERE id=$1", contract_id, *values)


async def complete_contract(contract_id: int):
    async with _pool.acquire() as c:
        await c.execute(
            "UPDATE contracts SET status='complete',completed_at=NOW() WHERE id=$1", contract_id
        )


# Saves

async def get_saves(guild_id: int, owner_id: int) -> list:
    async with _pool.acquire() as c:
        rs = await c.fetch(
            "SELECT slot_number,act_label,band_size,saved_at FROM player_saves "
            "WHERE guild_id=$1 AND owner_id=$2 ORDER BY slot_number",
            guild_id, owner_id
        )
        return [dict(r) for r in rs]


async def write_save(guild_id: int, owner_id: int, slot: int, snapshot: dict, act_label: str, band_size: int):
    async with _pool.acquire() as c:
        await c.execute(
            "INSERT INTO player_saves (guild_id,owner_id,slot_number,snapshot,act_label,band_size,saved_at) "
            "VALUES ($1,$2,$3,$4,$5,$6,NOW()) ON CONFLICT (guild_id,owner_id,slot_number) "
            "DO UPDATE SET snapshot=$4,act_label=$5,band_size=$6,saved_at=NOW()",
            guild_id, owner_id, slot, json.dumps(snapshot), act_label, band_size
        )


async def load_save(guild_id: int, owner_id: int, slot: int) -> dict | None:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT * FROM player_saves WHERE guild_id=$1 AND owner_id=$2 AND slot_number=$3",
            guild_id, owner_id, slot
        )
        return dict(r) if r else None


# Tactical maps

async def get_tactical_map(guild_id: int, owner_id: int) -> dict | None:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT * FROM tactical_maps WHERE guild_id=$1 AND owner_id=$2 AND is_active=TRUE",
            guild_id, owner_id
        )
        return dict(r) if r else None


async def save_tactical_map(guild_id: int, owner_id: int, data: dict):
    async with _pool.acquire() as c:
        await c.execute(
            "INSERT INTO tactical_maps (guild_id,owner_id,hex_grid,unit_positions,"
            "turn_number,initiative_order,is_active,combat_type,map_size) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) "
            "ON CONFLICT (guild_id,owner_id) DO UPDATE SET "
            "hex_grid=$3,unit_positions=$4,turn_number=$5,"
            "initiative_order=$6,is_active=$7,combat_type=$8,map_size=$9",
            guild_id, owner_id,
            json.dumps(data.get("hex_grid",{})),
            json.dumps(data.get("unit_positions",{})),
            data.get("turn_number",1),
            json.dumps(data.get("initiative_order",[])),
            data.get("is_active",True),
            data.get("combat_type","encounter"),
            data.get("map_size",9)
        )


async def clear_tactical_map(guild_id: int, owner_id: int):
    async with _pool.acquire() as c:
        await c.execute(
            "UPDATE tactical_maps SET is_active=FALSE WHERE guild_id=$1 AND owner_id=$2",
            guild_id, owner_id
        )


# Satsuma units

async def get_satsuma_units(guild_id: int, owner_id: int) -> list:
    async with _pool.acquire() as c:
        rs = await c.fetch(
            "SELECT * FROM satsuma_units WHERE guild_id=$1 AND owner_id=$2 AND is_active=TRUE",
            guild_id, owner_id
        )
        return [dict(r) for r in rs]


async def spawn_satsuma_unit(guild_id: int, owner_id: int, data: dict) -> int:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "INSERT INTO satsuma_units "
            "(guild_id,owner_id,unit_type,unit_name,behavior,hex_address,"
            "hp,max_hp,atk,def,spd,resolve,is_active) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,TRUE) RETURNING id",
            guild_id, owner_id,
            data["unit_type"], data.get("unit_name"),
            data.get("behavior","patrol"), data["hex_address"],
            data.get("hp",80), data.get("max_hp",80),
            data.get("atk",8), data.get("def",8),
            data.get("spd",8), data.get("resolve",8)
        )
        return r["id"]


async def update_satsuma_unit(unit_id: int, **kw):
    if not kw:
        return
    fields = list(kw.keys())
    values = list(kw.values())
    sets   = ",".join(f"{f}=${i+2}" for i, f in enumerate(fields))
    async with _pool.acquire() as c:
        await c.execute(f"UPDATE satsuma_units SET {sets} WHERE id=$1", unit_id, *values)


async def deactivate_satsuma_unit(unit_id: int):
    async with _pool.acquire() as c:
        await c.execute("UPDATE satsuma_units SET is_active=FALSE WHERE id=$1", unit_id)


# Hall of fame

async def get_hall_of_fame(guild_id: int) -> list:
    async with _pool.acquire() as c:
        rs = await c.fetch(
            "SELECT * FROM hall_of_fame WHERE guild_id=$1 ORDER BY ended_at DESC LIMIT 50", guild_id
        )
        return [dict(r) for r in rs]


async def add_hall_of_fame_entry(guild_id: int, owner_id: int, player: dict, ended_by: str):
    async with _pool.acquire() as c:
        cache = await c.fetchrow(
            "SELECT enemies_killed,band_members_lost,contracts_completed FROM leaderboard_cache "
            "WHERE guild_id=$1 AND owner_id=$2", guild_id, owner_id
        )
        kills     = cache["enemies_killed"]     if cache else 0
        lost      = cache["band_members_lost"]  if cache else 0
        contracts = cache["contracts_completed"] if cache else 0
        hall_traits = [t for t in (player.get("traits") or [])
                       if t in ("Ghost King","Conqueror","The Unbroken","Blood and Ash")]
        await c.execute(
            "INSERT INTO hall_of_fame "
            "(guild_id,owner_id,mc_name,mc_gender,path_choice,act_reached,"
            "total_kills,band_members_lost,contracts_done,hall_traits,ended_by) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)",
            guild_id, owner_id,
            f"Shimazu {player['mc_first_name']}", player["mc_gender"],
            player.get("path_choice"), player.get("current_act",0),
            kills, lost, contracts, json.dumps(hall_traits), ended_by
        )


# Leaderboard

async def get_leaderboard(guild_id: int) -> list:
    async with _pool.acquire() as c:
        rs = await c.fetch(
            "SELECT * FROM leaderboard_cache WHERE guild_id=$1 ORDER BY enemies_killed DESC", guild_id
        )
        return [dict(r) for r in rs]


async def increment_leaderboard(guild_id: int, owner_id: int, field: str, amt: int = 1):
    async with _pool.acquire() as c:
        await c.execute(
            f"INSERT INTO leaderboard_cache (guild_id,owner_id,{field}) VALUES ($1,$2,$3) "
            f"ON CONFLICT (guild_id,owner_id) DO UPDATE SET {field}=leaderboard_cache.{field}+$3",
            guild_id, owner_id, amt
        )


async def set_leaderboard_act(guild_id: int, owner_id: int, act: int):
    async with _pool.acquire() as c:
        await c.execute(
            "INSERT INTO leaderboard_cache (guild_id,owner_id,act_reached) VALUES ($1,$2,$3) "
            "ON CONFLICT (guild_id,owner_id) DO UPDATE SET "
            "act_reached=GREATEST(leaderboard_cache.act_reached,$3)",
            guild_id, owner_id, act
        )


# PvP

async def record_pvp(guild_id: int, challenger_id: int, defender_id: int, winner_id, result: str):
    async with _pool.acquire() as c:
        await c.execute(
            "INSERT INTO pvp_records (guild_id,challenger_id,defender_id,winner_id,result) "
            "VALUES ($1,$2,$3,$4,$5)",
            guild_id, challenger_id, defender_id, winner_id, result
        )
    if winner_id:
        await increment_leaderboard(guild_id, winner_id, "pvp_wins")


async def get_pvp_record(guild_id: int, owner_id: int) -> dict:
    async with _pool.acquire() as c:
        wins = await c.fetchval(
            "SELECT COUNT(*) FROM pvp_records WHERE guild_id=$1 AND winner_id=$2", guild_id, owner_id
        )
        total = await c.fetchval(
            "SELECT COUNT(*) FROM pvp_records WHERE guild_id=$1 "
            "AND (challenger_id=$2 OR defender_id=$2)", guild_id, owner_id
        )
    return {"wins": wins or 0, "total": total or 0}


# Overworld hexes

async def get_hex(guild_id: int, owner_id: int, address: str) -> dict | None:
    async with _pool.acquire() as c:
        r = await c.fetchrow(
            "SELECT * FROM overworld_hexes WHERE guild_id=$1 AND owner_id=$2 AND address=$3",
            guild_id, owner_id, address
        )
        return dict(r) if r else None


async def get_viewport_hexes(guild_id: int, owner_id: int, cx: int, cy: int, half: int = 8) -> list:
    async with _pool.acquire() as c:
        rs = await c.fetch(
            "SELECT * FROM overworld_hexes WHERE guild_id=$1 AND owner_id=$2 "
            "AND CAST(SPLIT_PART(address,',',1) AS INTEGER) BETWEEN $3 AND $4 "
            "AND CAST(SPLIT_PART(address,',',2) AS INTEGER) BETWEEN $5 AND $6",
            guild_id, owner_id,
            max(0, cx-half), min(59, cx+half),
            max(0, cy-half), min(119, cy+half)
        )
        return [dict(r) for r in rs]


async def set_hex_explored(guild_id: int, owner_id: int, address: str):
    async with _pool.acquire() as c:
        await c.execute(
            "UPDATE overworld_hexes SET is_explored=TRUE WHERE guild_id=$1 AND owner_id=$2 AND address=$3",
            guild_id, owner_id, address
        )


async def bulk_set_explored(guild_id: int, owner_id: int, addresses: list):
    async with _pool.acquire() as c:
        await c.execute(
            "UPDATE overworld_hexes SET is_explored=TRUE WHERE guild_id=$1 AND owner_id=$2 "
            "AND address=ANY($3)",
            guild_id, owner_id, addresses
        )


async def set_hex_controller(guild_id: int, owner_id: int, address: str, controller: str):
    async with _pool.acquire() as c:
        await c.execute(
            "UPDATE overworld_hexes SET controller=$4 WHERE guild_id=$1 AND owner_id=$2 AND address=$3",
            guild_id, owner_id, address, controller
        )


async def bulk_insert_hexes(guild_id: int, owner_id: int, rows: list):
    async with _pool.acquire() as c:
        await c.executemany(
            "INSERT INTO overworld_hexes "
            "(guild_id,owner_id,address,terrain,controller,is_explored,is_named_location,location_name) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT DO NOTHING",
            rows
        )