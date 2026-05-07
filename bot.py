import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("ghost_of_ryukyu")

OWNER_ID = int(os.environ.get("OWNER_ID", 0))

COGS = [
    "cogs.admin_cog",
    "cogs.story_cog",
    "cogs.social_cog",
    "cogs.combat_cog",
    "cogs.band_cog",
    "cogs.economy_cog",
    "cogs.pvp_cog",
]

intents         = discord.Intents.default()
intents.members = True


class GhostBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!gor!",  # Unused — all interactions are slash or button
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        # DB
        from utils.db import init_pool
        await init_pool()
        log.info("Database pool initialised.")

        # Persistent views (survive bot restarts)
        from views.menu import MainMenuView
        self.add_view(MainMenuView())

        # Load cogs
        for cog in COGS:
            await self.load_extension(cog)
            log.info("Loaded cog: %s", cog)

        # Sync slash commands globally
        synced = await self.tree.sync()
        log.info("Synced %d slash command(s).", len(synced))

    async def on_ready(self):
        log.info("Ghost of Ryukyu ready. Logged in as %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Game(name="1609 — Ryukyu Kingdom")
        )

    async def on_command_error(self, ctx, error):
        log.error("Command error: %s", error)


bot = GhostBot()


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set in environment.")
    bot.run(token)