import discord
from discord.ui import View, Button
import utils.db as db
from utils.embeds import base_embed, COLOR_DEFAULT, COLOR_STORY, COLOR_DEFEAT, COLOR_WARNING, wallet_line
from utils.contracts import generate_and_store_contracts, complete_contract_reward


class ContractBoardView(View):
    def __init__(self, guild_id: int, owner_id: int, page: int = 0):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.owner_id = owner_id
        self.page     = page

    async def build_embed(self):
        contracts = await db.get_contracts(self.guild_id, self.owner_id, "available")
        if not contracts:
            # Generate fresh batch
            contracts = await generate_and_store_contracts(self.guild_id, self.owner_id, 3)

        player  = await db.get_player(self.guild_id, self.owner_id)
        active  = await db.get_active_contract(self.guild_id, self.owner_id)
        embed   = discord.Embed(
            title="Contract Board",
            description=wallet_line(player) if player else "",
            color=COLOR_DEFAULT,
        )
        if active:
            embed.add_field(
                name=f"Active: {active['title']}",
                value=(
                    f"Difficulty: {active['difficulty'].title()}\n"
                    f"{active['description'][:120]}...\n"
                    f"Turns: {active.get('turns_elapsed',0)}/{active.get('turns_allowed','?')}"
                ),
                inline=False,
            )
            embed.set_footer(text="You have an active contract. Complete or abandon it first.")
        elif contracts:
            shown = contracts[self.page % len(contracts)]
            reward = shown.get("reward") or {}
            reward_str = (
                f"Coin: {reward.get('coin',0)}"
                + (f"  Raw Metals: {reward.get('raw_metals',0)}" if reward.get("raw_metals") else "")
                + f"  XP: {reward.get('xp',0)}"
            )
            embed.add_field(name=f"[{self.page+1}/{len(contracts)}] {shown['title']}", value=(
                f"Difficulty: {shown['difficulty'].title()}\n"
                f"{shown['description']}\n\n"
                f"Reward: {reward_str}"
                + (f"\nTurns: {shown.get('turns_allowed','unlimited')}" if shown.get('turns_allowed') else "")
            ), inline=False)
            embed.set_footer(text="Use Next/Prev to browse. Press Accept to take this contract.")
        else:
            embed.add_field(name="No Contracts Available",
                value="No available work at this time. Return later.", inline=False)
        return embed, contracts

    @discord.ui.button(label="Prev",   style=discord.ButtonStyle.secondary, row=0)
    async def prev(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        self.page = max(0, self.page - 1)
        e, _ = await self.build_embed()
        await i.response.edit_message(embed=e, view=self)

    @discord.ui.button(label="Next",   style=discord.ButtonStyle.secondary, row=0)
    async def next(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        contracts = await db.get_contracts(self.guild_id, self.owner_id, "available")
        if contracts:
            self.page = min(len(contracts)-1, self.page+1)
        e, _ = await self.build_embed()
        await i.response.edit_message(embed=e, view=self)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.danger,     row=0)
    async def accept(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        active = await db.get_active_contract(self.guild_id, self.owner_id)
        if active:
            await i.response.send_message(
                embed=base_embed("Contract Active",
                    f"You already have an active contract: {active['title']}",COLOR_WARNING),
                ephemeral=True)
            return
        contracts = await db.get_contracts(self.guild_id, self.owner_id, "available")
        if not contracts:
            await i.response.send_message(
                embed=base_embed("No Contracts","No available contracts.",COLOR_DEFEAT), ephemeral=True)
            return
        idx  = self.page % len(contracts)
        c    = contracts[idx]
        await db.update_contract(c["id"], status="active")
        await i.response.send_message(
            embed=base_embed("Contract Accepted", f"**{c['title']}**\n{c['description']}", COLOR_STORY),
            ephemeral=True)

    @discord.ui.button(label="Complete", style=discord.ButtonStyle.secondary, row=1)
    async def complete(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        active = await db.get_active_contract(self.guild_id, self.owner_id)
        if not active:
            await i.response.send_message(
                embed=base_embed("No Active Contract","No contract in progress.",COLOR_DEFEAT), ephemeral=True)
            return
        reward = await complete_contract_reward(self.guild_id, self.owner_id, active)
        reward_str = (
            f"Coin +{reward.get('coin',0)}"
            + (f"  Raw Metals +{reward.get('raw_metals',0)}" if reward.get("raw_metals") else "")
            + f"  XP +{reward.get('xp',0)}"
        )
        await i.response.send_message(
            embed=base_embed("Contract Complete",
                f"**{active['title']}** completed.\n{reward_str}", COLOR_STORY),
            ephemeral=True)

    @discord.ui.button(label="Abandon", style=discord.ButtonStyle.danger,    row=1)
    async def abandon(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        active = await db.get_active_contract(self.guild_id, self.owner_id)
        if not active:
            await i.response.send_message(
                embed=base_embed("No Active Contract","Nothing to abandon.",COLOR_DEFEAT), ephemeral=True)
            return
        await i.response.send_message(
            embed=base_embed("Abandon Contract?",
                f"**{active['title']}**\nAbandoning costs Loyalty -12.",COLOR_WARNING),
            view=ConfirmAbandonView(self.guild_id, self.owner_id, active, self),
            ephemeral=True)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, row=1)
    async def refresh(self, i: discord.Interaction, b: Button):
        if i.user.id != self.owner_id:
            await i.response.send_message("Not your panel.", ephemeral=True); return
        e, _ = await self.build_embed()
        await i.response.edit_message(embed=e, view=self)


class ConfirmAbandonView(View):
    def __init__(self, guild_id, owner_id, contract, parent):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.owner_id = owner_id
        self.contract = contract
        self.parent   = parent

    @discord.ui.button(label="Confirm Abandon", style=discord.ButtonStyle.danger)
    async def confirm(self, i: discord.Interaction, b: Button):
        await db.update_contract(self.contract["id"], status="abandoned")
        from utils.loyalty import LOSSES
        await db.adjust_loyalty(self.guild_id, self.owner_id, LOSSES["abandon_contract"])
        await i.response.edit_message(
            embed=base_embed("Contract Abandoned",
                f"**{self.contract['title']}** abandoned. Loyalty -12.", COLOR_WARNING),
            view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, i: discord.Interaction, b: Button):
        e, _ = await self.parent.build_embed()
        await i.response.edit_message(embed=e, view=self.parent)
