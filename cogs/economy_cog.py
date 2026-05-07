# Economy Cog
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import utils.db as db
from utils.embeds import base_embed, wallet_line, COLOR_DEFAULT, COLOR_DEFEAT, COLOR_WARNING
from utils.items_data import WEAPONS, ARMOR, get_weapon_tier, get_armor_tier

# Upgrade costs: T1->T2, T2->T3, T3->T4
WEAPON_UPGRADE_COSTS = {
    2: {"raw_metals": 3,  "rare_metals": 0, "shimazu_steel": 0, "coin": 10},
    3: {"raw_metals": 5,  "rare_metals": 2, "shimazu_steel": 0, "coin": 20},
    4: {"raw_metals": 0,  "rare_metals": 4, "shimazu_steel": 1, "coin": 40},
}
ARMOR_UPGRADE_COSTS = {
    2: {"raw_metals": 2,  "rare_metals": 0, "shimazu_steel": 0, "coin": 8},
    3: {"raw_metals": 4,  "rare_metals": 1, "shimazu_steel": 0, "coin": 18},
    4: {"raw_metals": 0,  "rare_metals": 3, "shimazu_steel": 1, "coin": 35},
}
FORGE_COSTS = {
    "katana":           {"raw_metals": 4,  "rare_metals": 0, "shimazu_steel": 0, "coin": 15},
    "naginata":         {"raw_metals": 4,  "rare_metals": 0, "shimazu_steel": 0, "coin": 12},
    "yumi":             {"raw_metals": 3,  "rare_metals": 0, "shimazu_steel": 0, "coin": 10},
    "tanto":            {"raw_metals": 2,  "rare_metals": 0, "shimazu_steel": 0, "coin": 8},
    "kanabo":           {"raw_metals": 5,  "rare_metals": 0, "shimazu_steel": 0, "coin": 18},
    "ryukyuan_spear":   {"raw_metals": 3,  "rare_metals": 0, "shimazu_steel": 0, "coin": 10},
    "ashigaru_armor":   {"raw_metals": 4,  "rare_metals": 0, "shimazu_steel": 0, "coin": 12},
    "light_scout":      {"raw_metals": 2,  "rare_metals": 0, "shimazu_steel": 0, "coin": 8},
    "ryukyuan_lamellar":{"raw_metals": 3,  "rare_metals": 0, "shimazu_steel": 0, "coin": 10},
    "satsuma_officer":  {"raw_metals": 5,  "rare_metals": 1, "shimazu_steel": 0, "coin": 25},
}


def _can_afford(player: dict, costs: dict) -> bool:
    return all(player.get(k, 0) >= v for k, v in costs.items())


def _deduct(player: dict, costs: dict) -> dict:
    return {k: player.get(k, 0) - v for k, v in costs.items() if k in player}


class ForgeWeaponModal(Modal, title="Forge Weapon"):
    weapon_key = TextInput(
        label="Weapon Key",
        placeholder="katana / naginata / yumi / tanto / kanabo / ryukyuan_spear"
    )

    async def on_submit(self, i: discord.Interaction):
        key    = self.weapon_key.value.strip().lower().replace(" ","_")
        player = await db.get_player(i.guild_id, i.user.id)
        if not player:
            await i.response.send_message(
                embed=base_embed("No Campaign","",COLOR_DEFEAT), ephemeral=True); return
        if key not in WEAPONS:
            await i.response.send_message(
                embed=base_embed("Unknown Weapon",
                    f"Valid weapon keys:\n{', '.join(WEAPONS.keys())}", COLOR_DEFEAT),
                ephemeral=True); return
        if key == "takeda_blade":
            await i.response.send_message(
                embed=base_embed("Cannot Forge","Takeda's Blade is a relic. It cannot be forged.",COLOR_DEFEAT),
                ephemeral=True); return
        costs = FORGE_COSTS.get(key)
        if not costs:
            await i.response.send_message(
                embed=base_embed("Not Available","This weapon is not available at the forge.",COLOR_DEFEAT),
                ephemeral=True); return
        if not _can_afford(player, costs):
            cost_str = "  ".join(f"{v} {k.replace('_',' ')}" for k,v in costs.items() if v > 0)
            await i.response.send_message(
                embed=base_embed("Insufficient Resources",
                    f"Requires: {cost_str}\nYou have: {wallet_line(player)}", COLOR_DEFEAT),
                ephemeral=True); return
        updates = _deduct(player, costs)
        updates["equipped_weapon"]      = key
        updates["equipped_weapon_tier"] = 1
        w = get_weapon_tier(key, 1)
        updates["atk"] = (player.get("atk") or 8) + w["atk_bonus"]
        await db.update_player(i.guild_id, i.user.id, **updates)
        await i.response.send_message(
            embed=base_embed("Weapon Forged",
                f"{WEAPONS[key]['name']} (Tier 1) equipped.\n"
                f"ATK +{w['atk_bonus']}  |  {w['desc']}", COLOR_DEFAULT),
            ephemeral=True)


class UpgradeWeaponModal(Modal, title="Upgrade Equipped Weapon"):
    confirm = TextInput(label='Type "upgrade" to confirm', placeholder="upgrade")

    async def on_submit(self, i: discord.Interaction):
        if self.confirm.value.strip().lower() != "upgrade":
            await i.response.send_message(
                embed=base_embed("Cancelled","Type 'upgrade' to confirm.",COLOR_WARNING), ephemeral=True); return
        player = await db.get_player(i.guild_id, i.user.id)
        if not player:
            await i.response.send_message(
                embed=base_embed("No Campaign","",COLOR_DEFEAT), ephemeral=True); return
        wkey    = player.get("equipped_weapon")
        cur_tier = player.get("equipped_weapon_tier", 1)
        if not wkey or wkey == "takeda_blade":
            await i.response.send_message(
                embed=base_embed("Cannot Upgrade","No upgradeable weapon equipped.",COLOR_DEFEAT),
                ephemeral=True); return
        if cur_tier >= 4:
            await i.response.send_message(
                embed=base_embed("Max Tier","Weapon is already at Tier 4.",COLOR_WARNING), ephemeral=True); return
        new_tier = cur_tier + 1
        costs    = WEAPON_UPGRADE_COSTS[new_tier]
        if not _can_afford(player, costs):
            cost_str = "  ".join(f"{v} {k.replace('_',' ')}" for k,v in costs.items() if v > 0)
            await i.response.send_message(
                embed=base_embed("Insufficient Resources",
                    f"Requires: {cost_str}\nYou have: {wallet_line(player)}", COLOR_DEFEAT),
                ephemeral=True); return
        old_w = get_weapon_tier(wkey, cur_tier)
        new_w = get_weapon_tier(wkey, new_tier)
        atk_gain = new_w["atk_bonus"] - old_w["atk_bonus"]
        updates = _deduct(player, costs)
        updates["equipped_weapon_tier"] = new_tier
        updates["atk"] = (player.get("atk") or 8) + atk_gain
        await db.update_player(i.guild_id, i.user.id, **updates)
        await i.response.send_message(
            embed=base_embed(f"Weapon Upgraded — T{new_tier}",
                f"{WEAPONS[wkey]['name']} is now Tier {new_tier}.\n"
                f"ATK +{atk_gain}  |  {new_w['desc']}", COLOR_DEFAULT),
            ephemeral=True)


class ForgeArmorModal(Modal, title="Forge Armor"):
    armor_key = TextInput(
        label="Armor Key",
        placeholder="ashigaru_armor / light_scout / ryukyuan_lamellar / satsuma_officer"
    )

    async def on_submit(self, i: discord.Interaction):
        key    = self.armor_key.value.strip().lower().replace(" ","_")
        player = await db.get_player(i.guild_id, i.user.id)
        if not player:
            await i.response.send_message(
                embed=base_embed("No Campaign","",COLOR_DEFEAT), ephemeral=True); return
        if key not in ARMOR:
            await i.response.send_message(
                embed=base_embed("Unknown Armor",
                    f"Valid armor keys:\n{', '.join(ARMOR.keys())}", COLOR_DEFEAT),
                ephemeral=True); return
        if key == "satsuma_officer" and (player.get("path_choice") == "ghost"):
            await i.response.send_message(
                embed=base_embed("Unavailable","Satsuma Officer Armor unavailable on Ghost path.",COLOR_DEFEAT),
                ephemeral=True); return
        costs = FORGE_COSTS.get(key)
        if not costs:
            await i.response.send_message(
                embed=base_embed("Not Available","This armor is not available at the forge.",COLOR_DEFEAT),
                ephemeral=True); return
        if not _can_afford(player, costs):
            cost_str = "  ".join(f"{v} {k.replace('_',' ')}" for k,v in costs.items() if v > 0)
            await i.response.send_message(
                embed=base_embed("Insufficient Resources",
                    f"Requires: {cost_str}\nYou have: {wallet_line(player)}", COLOR_DEFEAT),
                ephemeral=True); return
        updates = _deduct(player, costs)
        updates["equipped_armor"]      = key
        updates["equipped_armor_tier"] = 1
        a = get_armor_tier(key, 1)
        updates["def"] = (player.get("def") or 8) + a["def_bonus"]
        if a.get("spd_penalty"):
            updates["spd"] = max(1, (player.get("spd") or 8) - a["spd_penalty"])
        await db.update_player(i.guild_id, i.user.id, **updates)
        await i.response.send_message(
            embed=base_embed("Armor Forged",
                f"{ARMOR[key]['name']} (Tier 1) equipped.\n"
                f"DEF +{a['def_bonus']}"
                + (f"  SPD -{a['spd_penalty']}" if a.get("spd_penalty") else "")
                + f"  |  {a['desc']}", COLOR_DEFAULT),
            ephemeral=True)


class UpgradeArmorModal(Modal, title="Upgrade Equipped Armor"):
    confirm = TextInput(label='Type "upgrade" to confirm', placeholder="upgrade")

    async def on_submit(self, i: discord.Interaction):
        if self.confirm.value.strip().lower() != "upgrade":
            await i.response.send_message(
                embed=base_embed("Cancelled","",COLOR_WARNING), ephemeral=True); return
        player = await db.get_player(i.guild_id, i.user.id)
        if not player:
            await i.response.send_message(
                embed=base_embed("No Campaign","",COLOR_DEFEAT), ephemeral=True); return
        akey     = player.get("equipped_armor")
        cur_tier = player.get("equipped_armor_tier", 1)
        if not akey:
            await i.response.send_message(
                embed=base_embed("No Armor","No armor equipped.",COLOR_DEFEAT), ephemeral=True); return
        if cur_tier >= 4:
            await i.response.send_message(
                embed=base_embed("Max Tier","Armor is already at Tier 4.",COLOR_WARNING), ephemeral=True); return
        new_tier = cur_tier + 1
        costs    = ARMOR_UPGRADE_COSTS[new_tier]
        if not _can_afford(player, costs):
            cost_str = "  ".join(f"{v} {k.replace('_',' ')}" for k,v in costs.items() if v > 0)
            await i.response.send_message(
                embed=base_embed("Insufficient Resources",
                    f"Requires: {cost_str}\nYou have: {wallet_line(player)}", COLOR_DEFEAT),
                ephemeral=True); return
        old_a   = get_armor_tier(akey, cur_tier)
        new_a   = get_armor_tier(akey, new_tier)
        def_gain = new_a["def_bonus"] - old_a["def_bonus"]
        spd_cost = new_a.get("spd_penalty",0) - old_a.get("spd_penalty",0)
        updates  = _deduct(player, costs)
        updates["equipped_armor_tier"] = new_tier
        updates["def"] = (player.get("def") or 8) + def_gain
        if spd_cost > 0:
            updates["spd"] = max(1, (player.get("spd") or 8) - spd_cost)
        await db.update_player(i.guild_id, i.user.id, **updates)
        await i.response.send_message(
            embed=base_embed(f"Armor Upgraded — T{new_tier}",
                f"{ARMOR[akey]['name']} is now Tier {new_tier}.\n"
                f"DEF +{def_gain}"
                + (f"  SPD -{spd_cost}" if spd_cost else "")
                + f"  |  {new_a['desc']}", COLOR_DEFAULT),
            ephemeral=True)


class ForgeView(View):
    def __init__(self, guild_id: int, owner_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.owner_id = owner_id

    def _guard(self, i: discord.Interaction) -> bool:
        return i.user.id == self.owner_id

    @discord.ui.button(label="Forge Weapon",   style=discord.ButtonStyle.secondary, row=0)
    async def forge_weapon(self, i: discord.Interaction, b: Button):
        if not self._guard(i): await i.response.send_message("Not your panel.", ephemeral=True); return
        await i.response.send_modal(ForgeWeaponModal())

    @discord.ui.button(label="Upgrade Weapon", style=discord.ButtonStyle.secondary, row=0)
    async def upg_weapon(self, i: discord.Interaction, b: Button):
        if not self._guard(i): await i.response.send_message("Not your panel.", ephemeral=True); return
        await i.response.send_modal(UpgradeWeaponModal())

    @discord.ui.button(label="Forge Armor",    style=discord.ButtonStyle.secondary, row=1)
    async def forge_armor(self, i: discord.Interaction, b: Button):
        if not self._guard(i): await i.response.send_message("Not your panel.", ephemeral=True); return
        await i.response.send_modal(ForgeArmorModal())

    @discord.ui.button(label="Upgrade Armor",  style=discord.ButtonStyle.secondary, row=1)
    async def upg_armor(self, i: discord.Interaction, b: Button):
        if not self._guard(i): await i.response.send_message("Not your panel.", ephemeral=True); return
        await i.response.send_modal(UpgradeArmorModal())

    @discord.ui.button(label="Forge Costs",    style=discord.ButtonStyle.secondary, row=2)
    async def costs(self, i: discord.Interaction, b: Button):
        embed = discord.Embed(title="Forge — Material Costs", color=COLOR_DEFAULT)
        lines = []
        for key, costs in FORGE_COSTS.items():
            cost_str = "  ".join(f"{v} {k.replace('_',' ')}" for k,v in costs.items() if v > 0)
            name     = (WEAPONS.get(key) or ARMOR.get(key) or {}).get("name", key.replace("_"," ").title())
            lines.append(f"**{name}**: {cost_str}")
        embed.description = "\n".join(lines)
        embed.add_field(name="Upgrade Costs (Weapon)", value=(
            "T2: 3 Raw Metals, 10 Coin\n"
            "T3: 5 Raw Metals, 2 Rare Metals, 20 Coin\n"
            "T4: 4 Rare Metals, 1 Shimazu Steel, 40 Coin"
        ), inline=True)
        embed.add_field(name="Upgrade Costs (Armor)", value=(
            "T2: 2 Raw Metals, 8 Coin\n"
            "T3: 4 Raw Metals, 1 Rare Metal, 18 Coin\n"
            "T4: 3 Rare Metals, 1 Shimazu Steel, 35 Coin"
        ), inline=True)
        await i.response.send_message(embed=embed, ephemeral=True)


class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
