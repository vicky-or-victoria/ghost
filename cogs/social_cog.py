# Social Cog
import discord
from discord.ext import commands
from discord import app_commands
import utils.db as db
from utils.embeds import base_embed, COLOR_SOCIAL, COLOR_DEFEAT, COLOR_STORY, COLOR_DEFAULT, act_label, path_label


class SocialCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_channel(self, guild_id: int, channel_type: str):
        config = await db.get_guild_config(guild_id)
        if not config:
            return None
        field = {
            "announcement": "announcement_channel_id",
            "hall_of_fame": "hall_of_fame_channel_id",
            "leaderboard":  "leaderboard_channel_id",
            "commands":     "commands_channel_id",
        }.get(channel_type)
        cid = config.get(field) if field else None
        return self.bot.get_channel(cid) if cid else None

    @app_commands.command(name="player_panel", description="Open your player panel.")
    async def player_panel(self, i: discord.Interaction):
        player = await db.get_player(i.guild_id, i.user.id)
        if not player:
            await i.response.send_message(
                embed=base_embed("No Campaign", "Press Enlist in the menu channel to begin.", COLOR_DEFEAT),
                ephemeral=True)
            return
        if not player.get("is_alive", True):
            await i.response.send_message(
                embed=base_embed("Campaign Ended",
                    f"Shimazu {player['mc_first_name']} has fallen.\n"
                    "Press Enlist to begin a new campaign.", COLOR_DEFEAT),
                ephemeral=True)
            return
        from views.player_view import PlayerView
        pv = PlayerView(player, i.guild_id, i.user.id)
        embed, files = await pv.build_main_embed()
        await i.response.send_message(embed=embed, view=pv, files=files, ephemeral=True)

    async def announce_mc_death(self, guild_id: int, owner_id: int, cause: str = "killed in combat"):
        player = await db.get_player(guild_id, owner_id)
        if not player:
            return
        mc     = f"Shimazu {player['mc_first_name']}"
        path   = path_label(player.get("path_choice"))
        traits = player.get("traits") or []

        # Log to hall of fame
        await db.add_hall_of_fame_entry(guild_id, owner_id, player, "mc_death")
        await db.update_player(guild_id, owner_id, is_alive=False)

        embed = discord.Embed(
            title=f"{mc} has fallen.",
            description=(
                f"Cause: {cause}\n"
                f"{path}  |  Act {player.get('current_act',0)}\n\n"
                "The campaign has ended. "
                "This run has been recorded in the Hall of Fame."
            ),
            color=COLOR_DEFEAT,
        )
        if traits:
            embed.add_field(name="Traits Earned", value=", ".join(traits[:8]), inline=False)
        embed.set_footer(text="Press Enlist to begin a new campaign.")

        ch = await self._get_channel(guild_id, "announcement")
        if ch:
            guild  = self.bot.get_guild(guild_id)
            member = guild.get_member(owner_id) if guild else None
            await ch.send(content=member.mention if member else None, embed=embed)

        await self._post_hof_entry(guild_id, owner_id, player)

    async def announce_act_complete(self, guild_id: int, owner_id: int, act: int):
        player = await db.get_player(guild_id, owner_id)
        if not player:
            return
        mc     = f"Shimazu {player['mc_first_name']}"
        label  = act_label(act)
        ch     = await self._get_channel(guild_id, "announcement")
        if not ch:
            return
        embed = discord.Embed(
            title=f"{label} Complete",
            description=(
                f"{mc} — {path_label(player.get('path_choice'))}\n"
                f"Moving into Act {act+1}."
            ),
            color=COLOR_STORY,
        )
        guild  = self.bot.get_guild(guild_id)
        member = guild.get_member(owner_id) if guild else None
        await ch.send(content=member.mention if member else None, embed=embed)

    async def announce_path_choice(self, guild_id: int, owner_id: int, path: str):
        player = await db.get_player(guild_id, owner_id)
        if not player:
            return
        mc = f"Shimazu {player['mc_first_name']}"
        ch = await self._get_channel(guild_id, "announcement")
        if not ch:
            return
        embed = discord.Embed(
            title=f"{mc} has chosen the {path.capitalize()} Path.",
            description=(
                f"{path_label(path)}\n\n"
                + ("Satsuma — Complete the conquest." if path == "blade"
                   else "Ghost — Resist. Disappear. Survive.")
            ),
            color=COLOR_SOCIAL,
        )
        guild  = self.bot.get_guild(guild_id)
        member = guild.get_member(owner_id) if guild else None
        await ch.send(content=member.mention if member else None, embed=embed)

    async def announce_campaign_complete(self, guild_id: int, owner_id: int):
        player = await db.get_player(guild_id, owner_id)
        if not player:
            return
        mc     = f"Shimazu {player['mc_first_name']}"
        path   = path_label(player.get("path_choice"))
        traits = player.get("traits") or []
        cache  = await db.get_leaderboard(guild_id)
        row    = next((r for r in cache if r["owner_id"]==owner_id), {})

        await db.add_hall_of_fame_entry(guild_id, owner_id, player, "campaign_complete")
        await db.update_player(guild_id, owner_id, campaign_complete=True)

        embed = discord.Embed(
            title=f"{mc} — Campaign Complete",
            description=(
                f"{path}\n\n"
                f"The island is done with them, or they with it.\n\n"
                f"Enemies killed: {row.get('enemies_killed',0)}\n"
                f"Contracts completed: {row.get('contracts_completed',0)}\n"
                f"Band members lost: {row.get('band_members_lost',0)}\n"
                f"PvP wins: {row.get('pvp_wins',0)}"
                + (f"\n\nHall traits: {', '.join(t for t in traits if t in ('Ghost King','Conqueror','The Unbroken','Blood and Ash'))}"
                   if any(t in traits for t in ("Ghost King","Conqueror","The Unbroken","Blood and Ash"))
                   else "")
            ),
            color=COLOR_SOCIAL,
        )
        embed.set_footer(text="Hall of Fame recorded. NG+ traits preserved on next campaign.")

        ch = await self._get_channel(guild_id, "announcement")
        if ch:
            guild  = self.bot.get_guild(guild_id)
            member = guild.get_member(owner_id) if guild else None
            await ch.send(content=member.mention if member else None, embed=embed)

        await self._post_hof_entry(guild_id, owner_id, player)
        await self._refresh_leaderboard(guild_id)

    async def _post_hof_entry(self, guild_id: int, owner_id: int, player: dict):
        ch = await self._get_channel(guild_id, "hall_of_fame")
        if not ch:
            return
        mc     = f"Shimazu {player['mc_first_name']}"
        path   = path_label(player.get("path_choice"))
        traits = player.get("traits") or []
        hall_traits = [t for t in traits if t in ("Ghost King","Conqueror","The Unbroken","Blood and Ash")]
        embed = discord.Embed(title=mc, color=COLOR_SOCIAL)
        embed.add_field(name="Path",       value=path,                                  inline=True)
        embed.add_field(name="Act Reached",value=str(player.get("current_act",0)),      inline=True)
        embed.add_field(name="Level",      value=str(player.get("level",1)),            inline=True)
        if hall_traits:
            embed.add_field(name="Hall of Fame Traits", value=", ".join(hall_traits),   inline=False)
        await ch.send(embed=embed)

    async def _refresh_leaderboard(self, guild_id: int):
        ch = await self._get_channel(guild_id, "leaderboard")
        if not ch:
            return
        entries = await db.get_leaderboard(guild_id)
        if not entries:
            return
        embed = discord.Embed(title="Leaderboard", color=COLOR_DEFAULT)
        def top5(field, label):
            rows = sorted(entries, key=lambda x: x.get(field,0), reverse=True)[:5]
            return "\n".join(f"{i+1}. {r.get('mc_name','?')} — {r.get(field,0)}" for i,r in enumerate(rows)) or "—"
        embed.add_field(name="Enemies Killed",      value=top5("enemies_killed",""), inline=True)
        embed.add_field(name="Contracts",           value=top5("contracts_completed",""), inline=True)
        embed.add_field(name="Band Lost",           value=top5("band_members_lost",""), inline=True)
        embed.add_field(name="PvP Wins",            value=top5("pvp_wins",""), inline=True)
        # Pin or just send
        async for msg in ch.history(limit=5):
            if msg.author == self.bot.user and msg.embeds:
                await msg.edit(embed=embed)
                return
        await ch.send(embed=embed)

    async def announce_band_death(self, guild_id: int, owner_id: int, member: dict):
        ch = await self._get_channel(guild_id, "announcement")
        if not ch:
            return
        player = await db.get_player(guild_id, owner_id)
        mc     = f"Shimazu {player['mc_first_name']}" if player else "Unknown MC"
        traits = member.get("traits") or []
        embed  = discord.Embed(
            title=f"{member['member_name']} has fallen.",
            description=(
                f"{member['archetype']}  |  Band of {mc}\n"
                f"Battles survived: {member['battles_survived']}  |  Kills: {member['kills']}"
                + (f"\nTraits: {', '.join(traits)}" if traits else "")
            ),
            color=COLOR_DEFEAT,
        )
        guild  = self.bot.get_guild(guild_id)
        m      = guild.get_member(owner_id) if guild else None
        await ch.send(content=m.mention if m else None, embed=embed)


async def setup(bot):
    await bot.add_cog(SocialCog(bot))
