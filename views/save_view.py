import discord
from discord.ui import View, Button
import json
import utils.db as db
from utils.embeds import base_embed, COLOR_NEUTRAL, COLOR_WARNING, COLOR_DEFEAT


class SaveView(View):
    def __init__(self, player, guild_id, owner_id, parent_view=None):
        super().__init__(timeout=120)
        self.player      = player
        self.guild_id    = guild_id
        self.owner_id    = owner_id
        self.parent_view = parent_view

    @discord.ui.button(label="Save to Slot 1", style=discord.ButtonStyle.secondary, row=0)
    async def save1(self, i, b): await self._try_save(i, 1)

    @discord.ui.button(label="Save to Slot 2", style=discord.ButtonStyle.secondary, row=0)
    async def save2(self, i, b): await self._try_save(i, 2)

    @discord.ui.button(label="Load Slot 1",    style=discord.ButtonStyle.danger,     row=1)
    async def load1(self, i, b): await self._try_load(i, 1)

    @discord.ui.button(label="Load Slot 2",    style=discord.ButtonStyle.danger,     row=1)
    async def load2(self, i, b): await self._try_load(i, 2)

    @discord.ui.button(label="Back",           style=discord.ButtonStyle.secondary,  row=2)
    async def back(self, i, b):
        if self.parent_view:
            e, f = await self.parent_view.build_main_embed()
            await i.response.edit_message(embed=e, attachments=f, view=self.parent_view)
        else:
            await i.response.edit_message(embed=base_embed("Done","",COLOR_NEUTRAL), view=None)

    async def _try_save(self, i, slot):
        saves    = await db.get_saves(self.guild_id, self.owner_id)
        save_map = {s["slot_number"]: s for s in saves}
        if slot in save_map:
            s  = save_map[slot]
            ts = s["saved_at"].strftime("%Y-%m-%d %H:%M") if s.get("saved_at") else "?"
            embed = base_embed(f"Overwrite Slot {slot}?",
                f"{s.get('act_label','?')} — Band {s.get('band_size',0)}\nSaved: {ts}",
                COLOR_WARNING)
            await i.response.edit_message(embed=embed,
                view=ConfirmSaveView(self.guild_id, self.owner_id, slot, self))
        else:
            await self._do_save(i, slot)

    async def _do_save(self, i, slot):
        from utils.saves import build_snapshot
        from utils.embeds import act_label
        player    = await db.get_player(self.guild_id, self.owner_id)
        band_size = await db.get_band_size(self.guild_id, self.owner_id)
        label     = act_label(player.get("current_act",0))
        snapshot  = await build_snapshot(self.guild_id, self.owner_id)
        await db.write_save(self.guild_id, self.owner_id, slot, snapshot, label, band_size)
        await i.response.edit_message(
            embed=base_embed(f"Saved — Slot {slot}", f"{label}  |  Band: {band_size}", COLOR_NEUTRAL),
            view=self)

    async def _try_load(self, i, slot):
        save = await db.load_save(self.guild_id, self.owner_id, slot)
        if not save:
            await i.response.send_message(
                embed=base_embed(f"Slot {slot} Empty","Nothing to load.",COLOR_DEFEAT), ephemeral=True)
            return
        ts = save["saved_at"].strftime("%Y-%m-%d %H:%M") if save.get("saved_at") else "?"
        await i.response.edit_message(
            embed=base_embed(f"Load Slot {slot}?",
                f"{save.get('act_label','?')}  |  Band: {save.get('band_size',0)}\nSaved: {ts}\n\n"
                "Progress since last save will be lost.", COLOR_WARNING),
            view=ConfirmLoadView(self.guild_id, self.owner_id, slot, save, self))


class ConfirmSaveView(View):
    def __init__(self, guild_id, owner_id, slot, parent):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.owner_id = owner_id
        self.slot     = slot
        self.parent   = parent

    @discord.ui.button(label="Confirm Save", style=discord.ButtonStyle.danger)
    async def confirm(self, i, b):
        await self.parent._do_save(i, self.slot)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, i, b):
        if hasattr(self.parent, "build_save_embed"):
            e, _ = await self.parent.build_save_embed()
        else:
            e = base_embed("Cancelled","",COLOR_NEUTRAL)
        await i.response.edit_message(embed=e, view=self.parent)


class ConfirmLoadView(View):
    def __init__(self, guild_id, owner_id, slot, save_row, parent):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.owner_id = owner_id
        self.slot     = slot
        self.save_row = save_row
        self.parent   = parent

    @discord.ui.button(label="Confirm Load", style=discord.ButtonStyle.danger)
    async def confirm(self, i, b):
        snapshot = self.save_row.get("snapshot") or {}
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        pd = snapshot.get("player")
        if not pd:
            await i.response.send_message(
                embed=base_embed("Load Failed","Save data corrupted.",COLOR_DEFEAT), ephemeral=True)
            return
        keep = [
            "current_act","current_scene","path_choice","current_hex",
            "hp","max_hp","atk","def","spd","resolve","recon","loyalty",
            "xp","level","coin","raw_metals","rare_metals","shimazu_steel",
            "traits","perks","equipped_weapon","equipped_weapon_tier",
            "equipped_armor","equipped_armor_tier","is_alive","grief_counter",
        ]
        kw = {k: pd[k] for k in keep if k in pd}
        await db.update_player(self.guild_id, self.owner_id, **kw)
        if "loyalty" in snapshot:
            pool = await db.get_pool()
            async with pool.acquire() as c:
                await c.execute(
                    "UPDATE band_loyalty SET loyalty=$3 WHERE guild_id=$1 AND owner_id=$2",
                    self.guild_id, self.owner_id, snapshot["loyalty"])
        current = await db.get_player(self.guild_id, self.owner_id)
        if not current.get("is_alive", True):
            traits = list(current.get("traits") or [])
            if "Haunted" not in traits:
                traits.append("Haunted")
            from utils.traits import TRAIT_DEFS
            updates = {"traits": traits, "is_alive": True}
            for stat, val in TRAIT_DEFS["Haunted"].get("stats",{}).items():
                updates[stat] = max(1, (current.get(stat,8) or 8) + val)
            await db.update_player(self.guild_id, self.owner_id, **updates)
        await i.response.edit_message(
            embed=base_embed(f"Slot {self.slot} Loaded",
                f"Restored: {self.save_row.get('act_label','?')}",COLOR_NEUTRAL),
            view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, i, b):
        if hasattr(self.parent, "build_save_embed"):
            e, _ = await self.parent.build_save_embed()
        else:
            e = base_embed("Cancelled","",COLOR_NEUTRAL)
        await i.response.edit_message(embed=e, view=self.parent)
