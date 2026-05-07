import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import utils.db as db
from utils.embeds import base_embed, COLOR_GM, COLOR_DEFEAT, COLOR_WARNING


class SetChannelModal(Modal, title="Set Channel"):
    channel_id = TextInput(label="Channel ID", placeholder="Right-click channel > Copy ID")
    role_name  = TextInput(label="Role", placeholder="menu / commands / announcements / hall_of_fame / leaderboard")

    async def on_submit(self, i: discord.Interaction):
        field_map = {
            "menu":          "menu_channel_id",
            "commands":      "commands_channel_id",
            "announcements": "announcement_channel_id",
            "hall_of_fame":  "hall_of_fame_channel_id",
            "leaderboard":   "leaderboard_channel_id",
        }
        role  = self.role_name.value.strip().lower()
        field = field_map.get(role)
        if not field:
            await i.response.send_message(
                embed=base_embed("Invalid Role", f"Valid: {', '.join(field_map)}", COLOR_DEFEAT),
                ephemeral=True); return
        try:
            cid = int(self.channel_id.value.strip())
        except ValueError:
            await i.response.send_message(
                embed=base_embed("Invalid ID","Channel ID must be a number.",COLOR_DEFEAT),
                ephemeral=True); return
        await db.upsert_guild_config(i.guild_id, **{field: cid})
        ch = i.guild.get_channel(cid)
        await i.response.send_message(
            embed=base_embed("Channel Set", f"{role} -> {ch.mention if ch else cid}", COLOR_GM),
            ephemeral=True)


class SetGMRoleModal(Modal, title="Set GM Role"):
    role_id = TextInput(label="Role ID", placeholder="Right-click role > Copy ID")

    async def on_submit(self, i: discord.Interaction):
        try:
            rid = int(self.role_id.value.strip())
        except ValueError:
            await i.response.send_message(
                embed=base_embed("Invalid ID","Role ID must be a number.",COLOR_DEFEAT),
                ephemeral=True); return
        await db.upsert_guild_config(i.guild_id, gm_role_id=rid)
        r = i.guild.get_role(rid)
        await i.response.send_message(
            embed=base_embed("GM Role Set", f"GM role -> {r.mention if r else rid}", COLOR_GM),
            ephemeral=True)


class ResetPlayerModal(Modal, title="Reset Player Campaign"):
    user_id = TextInput(label="User ID", placeholder="Right-click user > Copy ID")

    async def on_submit(self, i: discord.Interaction):
        try:
            uid = int(self.user_id.value.strip())
        except ValueError:
            await i.response.send_message(
                embed=base_embed("Invalid ID","User ID must be a number.",COLOR_DEFEAT),
                ephemeral=True); return
        pool = await db.get_pool()
        async with pool.acquire() as c:
            await c.execute("DELETE FROM players WHERE guild_id=$1 AND owner_id=$2", i.guild_id, uid)
        m = i.guild.get_member(uid)
        await i.response.send_message(
            embed=base_embed("Player Reset", f"{m.mention if m else uid} campaign deleted.", COLOR_WARNING),
            ephemeral=True)


class SetFlagModal(Modal, title="Set Story Flag"):
    user_id = TextInput(label="User ID", placeholder="Right-click user > Copy ID")
    flag    = TextInput(label="Flag Name", placeholder="e.g. LANGUAGE_BREAKS")
    value   = TextInput(label="Value", placeholder="true / false / string")

    async def on_submit(self, i: discord.Interaction):
        try:
            uid = int(self.user_id.value.strip())
        except ValueError:
            await i.response.send_message(
                embed=base_embed("Invalid ID","User ID must be a number.",COLOR_DEFEAT),
                ephemeral=True); return
        raw    = self.value.value.strip()
        parsed = True if raw.lower()=="true" else (False if raw.lower()=="false" else raw)
        await db.update_story_flags(i.guild_id, uid, **{self.flag.value.strip(): parsed})
        await i.response.send_message(
            embed=base_embed("Flag Set", f"{self.flag.value.strip()} = {raw} for <@{uid}>", COLOR_GM),
            ephemeral=True)


class SetActModal(Modal, title="Set Act / Scene"):
    user_id = TextInput(label="User ID", placeholder="Right-click user > Copy ID")
    act     = TextInput(label="Act Number", placeholder="0 / 1 / 2 / 3")
    scene   = TextInput(label="Scene Key",  placeholder="e.g. act1_itoman")

    async def on_submit(self, i: discord.Interaction):
        try:
            uid = int(self.user_id.value.strip())
            act = int(self.act.value.strip())
        except ValueError:
            await i.response.send_message(
                embed=base_embed("Invalid Input","User ID and Act must be numbers.",COLOR_DEFEAT),
                ephemeral=True); return
        scene = self.scene.value.strip()
        await db.update_scene(i.guild_id, uid, act, scene)
        await i.response.send_message(
            embed=base_embed("Scene Set", f"<@{uid}> -> Act {act} / {scene}", COLOR_GM),
            ephemeral=True)


class GiveItemModal(Modal, title="Give Item"):
    user_id  = TextInput(label="User ID",  placeholder="Right-click user > Copy ID")
    item_key = TextInput(label="Item Key", placeholder="e.g. medicine / takeda_blade")
    quantity = TextInput(label="Quantity", placeholder="1", default="1")
    is_relic = TextInput(label="Is Relic? (yes/no)", placeholder="no", default="no")

    async def on_submit(self, i: discord.Interaction):
        try:
            uid = int(self.user_id.value.strip())
            qty = int(self.quantity.value.strip())
        except ValueError:
            await i.response.send_message(
                embed=base_embed("Invalid Input","User ID and Quantity must be numbers.",COLOR_DEFEAT),
                ephemeral=True); return
        relic = self.is_relic.value.strip().lower() in ("yes","y","true")
        key   = self.item_key.value.strip()
        await db.add_item(i.guild_id, uid, key, qty, relic)
        await i.response.send_message(
            embed=base_embed("Item Given",
                f"{qty}x {key} -> <@{uid}>{'  (relic)' if relic else ''}", COLOR_GM),
            ephemeral=True)


class AdjustLoyaltyModal(Modal, title="Adjust Loyalty"):
    user_id = TextInput(label="User ID", placeholder="Right-click user > Copy ID")
    delta   = TextInput(label="Amount",  placeholder="+10 or -5")

    async def on_submit(self, i: discord.Interaction):
        try:
            uid   = int(self.user_id.value.strip())
            delta = int(self.delta.value.strip())
        except ValueError:
            await i.response.send_message(
                embed=base_embed("Invalid Input","Both fields must be numbers.",COLOR_DEFEAT),
                ephemeral=True); return
        new_val = await db.adjust_loyalty(i.guild_id, uid, delta)
        sign    = "+" if delta >= 0 else ""
        await i.response.send_message(
            embed=base_embed("Loyalty Adjusted",
                f"<@{uid}> {sign}{delta}. Now: {new_val}.", COLOR_GM),
            ephemeral=True)


async def _deploy_menu(i: discord.Interaction):
    config = await db.get_guild_config(i.guild_id)
    if not config or not config.get("menu_channel_id"):
        await i.response.send_message(
            embed=base_embed("No Menu Channel","Set a menu channel first.",COLOR_DEFEAT), ephemeral=True); return
    channel = i.client.get_channel(config["menu_channel_id"])
    if not channel:
        await i.response.send_message(
            embed=base_embed("Channel Not Found","Menu channel could not be found.",COLOR_DEFEAT), ephemeral=True); return
    from views.menu import MainMenuView
    embed = discord.Embed(
        title="Ghost of Ryukyu",
        description=(
            "1609. The Satsuma fleet has landed on Ryukyu.\n"
            "You are the child of an officer in the invading force.\n"
            "The compound burns at midnight.\n\n"
            "What you do next is permanent."
        ),
        color=0x2C3E50,
    )
    embed.set_footer(text="Ghost of Ryukyu  |  A solo-instance Discord RPG  |  1609")
    msg = await channel.send(embed=embed, view=MainMenuView())
    await db.upsert_guild_config(i.guild_id, menu_message_id=msg.id)
    await i.response.send_message(
        embed=base_embed("Menu Deployed", f"Menu posted in {channel.mention}.", COLOR_GM), ephemeral=True)


async def _server_status(i: discord.Interaction):
    config = await db.get_guild_config(i.guild_id)
    if not config:
        await i.response.send_message(
            embed=base_embed("No Config","Nothing configured yet.",COLOR_DEFEAT), ephemeral=True); return
    def ch(cid):
        if not cid: return "Not set"
        c = i.client.get_channel(cid)
        return c.mention if c else f"<#{cid}>"
    def ro(rid):
        if not rid: return "Not set"
        r = i.guild.get_role(rid)
        return r.mention if r else f"<@&{rid}>"
    embed = base_embed("Server Configuration","",COLOR_GM)
    embed.add_field(name="Menu Channel",     value=ch(config.get("menu_channel_id")),         inline=True)
    embed.add_field(name="Commands Channel", value=ch(config.get("commands_channel_id")),     inline=True)
    embed.add_field(name="Announcements",    value=ch(config.get("announcement_channel_id")), inline=True)
    embed.add_field(name="Hall of Fame",     value=ch(config.get("hall_of_fame_channel_id")), inline=True)
    embed.add_field(name="Leaderboard",      value=ch(config.get("leaderboard_channel_id")),  inline=True)
    embed.add_field(name="GM Role",          value=ro(config.get("gm_role_id")),              inline=True)
    await i.response.send_message(embed=embed, ephemeral=True)


_PAGES = [
    {
        "title": "GM Panel  —  Server Setup",
        "body": (
            "**Set Channel** — Assign a Discord channel to a bot role.\n"
            "Roles: `menu`  `commands`  `announcements`  `hall_of_fame`  `leaderboard`\n\n"
            "**Set GM Role** — Choose which role can access this panel.\n\n"
            "**Deploy Menu** — Post the persistent main menu in the menu channel.\n\n"
            "**Server Status** — View current configuration."
        ),
        "actions": [
            ("Set Channel",   "set_channel"),
            ("Set GM Role",   "set_gm_role"),
            ("Deploy Menu",   "deploy_menu"),
            ("Server Status", "server_status"),
        ],
    },
    {
        "title": "GM Panel  —  Player Management",
        "body": (
            "**Reset Player** — Delete a player's campaign entirely. Irreversible.\n\n"
            "**Set Flag** — Force a story flag for a player.\n\n"
            "**Set Act / Scene** — Move a player to any act and scene key.\n\n"
            "**Give Item** — Add any item or relic to a player's inventory.\n\n"
            "**Adjust Loyalty** — Add or subtract from band loyalty."
        ),
        "actions": [
            ("Reset Player",    "reset_player"),
            ("Set Flag",        "set_flag"),
            ("Set Act / Scene", "set_act"),
            ("Give Item",       "give_item"),
            ("Adjust Loyalty",  "adjust_loyalty"),
        ],
    },
]


class ActionButton(Button):
    def __init__(self, label: str, action: str, row: int):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row)
        self.action = action

    async def callback(self, i: discord.Interaction):
        a = self.action
        if   a == "set_channel":   await i.response.send_modal(SetChannelModal())
        elif a == "set_gm_role":   await i.response.send_modal(SetGMRoleModal())
        elif a == "deploy_menu":   await _deploy_menu(i)
        elif a == "server_status": await _server_status(i)
        elif a == "reset_player":  await i.response.send_modal(ResetPlayerModal())
        elif a == "set_flag":      await i.response.send_modal(SetFlagModal())
        elif a == "set_act":       await i.response.send_modal(SetActModal())
        elif a == "give_item":     await i.response.send_modal(GiveItemModal())
        elif a == "adjust_loyalty":await i.response.send_modal(AdjustLoyaltyModal())


class NavButton(Button):
    def __init__(self, label: str, direction: int, disabled: bool):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, disabled=disabled, row=4)
        self.direction = direction

    async def callback(self, i: discord.Interaction):
        v = self.view
        v.page = max(0, min(len(_PAGES)-1, v.page + self.direction))
        v._build()
        await i.response.edit_message(embed=v.build_embed(), view=v)


class GMPanelView(View):
    def __init__(self, page: int = 0):
        super().__init__(timeout=300)
        self.page = page
        self._build()

    def _build(self):
        for child in list(self.children):
            self.remove_item(child)
        for idx, (label, action) in enumerate(_PAGES[self.page]["actions"]):
            self.add_item(ActionButton(label=label, action=action, row=idx // 3))
        self.add_item(NavButton("Back", -1, disabled=(self.page == 0)))
        self.add_item(NavButton("Next",  1, disabled=(self.page >= len(_PAGES)-1)))

    def build_embed(self) -> discord.Embed:
        p = _PAGES[self.page]
        embed = discord.Embed(title=p["title"], description=p["body"], color=COLOR_GM)
        embed.set_footer(text=f"Page {self.page+1} of {len(_PAGES)}")
        return embed


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gm_panel", description="Open the GM control panel.")
    async def gm_panel(self, i: discord.Interaction):
        config = await db.get_guild_config(i.guild_id)
        is_gm  = False
        if config and config.get("gm_role_id"):
            role = i.guild.get_role(config["gm_role_id"])
            if role and role in i.user.roles:
                is_gm = True
        if not is_gm and not i.user.guild_permissions.administrator:
            await i.response.send_message(
                embed=base_embed("Access Denied","GM role or Administrator required.",COLOR_DEFEAT),
                ephemeral=True); return
        view = GMPanelView(page=0)
        await i.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
