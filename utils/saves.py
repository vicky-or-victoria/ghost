import utils.db as db
import datetime


async def build_snapshot(guild_id: int, owner_id: int) -> dict:
    player    = await db.get_player(guild_id, owner_id)
    companion = await db.get_companion(guild_id, owner_id)
    band      = await db.get_band(guild_id, owner_id)
    loyalty   = await db.get_loyalty(guild_id, owner_id)
    items     = await db.get_items(guild_id, owner_id)
    flags     = await db.get_story_flags(guild_id, owner_id)
    faction   = await db.get_faction_standing(guild_id, owner_id)
    return {
        "player":      _clean(player),
        "companion":   _clean(companion),
        "band":        [_clean(m) for m in band],
        "loyalty":     loyalty,
        "items":       [_clean(i) for i in items],
        "story_flags": _clean(flags),
        "faction":     _clean(faction),
    }


def _clean(d: dict | None) -> dict:
    if not d:
        return {}
    out = {}
    for k, v in d.items():
        if isinstance(v, (datetime.datetime, datetime.date)):
            out[k] = v.isoformat()
        elif isinstance(v, bytes):
            pass
        else:
            out[k] = v
    return out
