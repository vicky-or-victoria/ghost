# Story Cog
import discord
from discord.ext import commands
import utils.db as db
import utils.story_engine as story
from utils.embeds import base_embed, COLOR_STORY, COLOR_DEFAULT, act_label
from utils.assets import get_story_banner, apply_banner
from views.story_view import (
    Scene1View, Scene2View, Scene3View,
    Scene4View, Scene6View, PathChoiceView, EpilogueView,
)


class StoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_or_create_thread(self, guild_id: int, owner_id: int) -> discord.Thread | None:
        """Get the player's private forum thread, creating it if missing."""
        player = await db.get_player(guild_id, owner_id)
        if not player:
            return None

        # Return existing thread if stored
        thread_id = player.get("forum_thread_id")
        if thread_id:
            thread = self.bot.get_channel(thread_id)
            if thread:
                return thread
            # Fetch from API if not in cache
            try:
                thread = await self.bot.fetch_channel(thread_id)
                return thread
            except Exception:
                pass  # Thread may have been deleted — recreate below

        # Create a new thread
        config = await db.get_guild_config(guild_id)
        if not config or not config.get("forum_channel_id"):
            return None
        forum = self.bot.get_channel(config["forum_channel_id"])
        if not forum or not isinstance(forum, discord.ForumChannel):
            return None

        guild  = self.bot.get_guild(guild_id)
        member = guild.get_member(owner_id) if guild else None
        username = member.display_name if member else f"Player {owner_id}"
        mc_name  = f"Shimazu {player['mc_first_name']}" if player.get("mc_first_name") else username

        thread_name = f"{username} — {mc_name}"

        divider = "-" * 44
        player_line = member.mention if member else username
        desc = (
            divider + "\n"
            + "**Player:** " + player_line + "\n"
            + "**Character:** " + mc_name + "\n"
            + "**Campaign starts:** Act 0 - Before the Fire\n"
            + divider + "\n\n"
            + "This thread records your campaign. Story scenes and choices appear here."
        )
        opener = discord.Embed(
            title="Ghost of Ryukyu",
            description=desc,
            color=0x2C3E50,
        )

        # GM role gets access — set allowed_mentions and thread tags if needed
        gm_role_id = config.get("gm_role_id")

        thread, _ = await forum.create_thread(
            name=thread_name,
            embed=opener,
            reason=f"Ghost of Ryukyu campaign thread for {username}",
        )

        # Store thread ID on player
        await db.update_player(guild_id, owner_id, forum_thread_id=thread.id)

        # Invite GM role to thread if it exists
        if gm_role_id and guild:
            gm_role = guild.get_role(gm_role_id)
            # Forum threads inherit channel permissions — private threads need explicit adds
            # For forum channels, visibility is controlled at the channel level
            # Just ping the thread so GMs with the role can see it
            pass

        return thread

    async def _post_to_commands(self, guild_id: int, owner_id: int,
                                  embed: discord.Embed, view=None, files: list = None):
        """Post a story embed to the player's private forum thread."""
        thread = await self._get_or_create_thread(guild_id, owner_id)
        if thread:
            return await thread.send(embed=embed, view=view, files=files or [])

        # Fallback to commands channel if forum not configured
        config  = await db.get_guild_config(guild_id)
        if not config or not config.get("commands_channel_id"):
            return None
        channel = self.bot.get_channel(config["commands_channel_id"])
        if not channel:
            return None
        guild  = self.bot.get_guild(guild_id)
        member = guild.get_member(owner_id) if guild else None
        return await channel.send(content=member.mention if member else None,
                                   embed=embed, view=view, files=files or [])

    async def deliver_scene(self, guild_id: int, owner_id: int, scene_key: str):
        player = await db.get_player(guild_id, owner_id)
        if not player:
            return
        scene_map = {
            "act0_enlistment":  self.scene_act0_enlistment,
            "act0_courtyard":   self.scene_act0_courtyard,
            "act0_scene1":      self.scene_act0_burning_tent,
            "act0_armory":      self.scene_act0_armory,
            "act0_gate":        self.scene_act0_gate,
            "act0_father":      self.scene_act0_father,
            "act0_forest":      self.scene_act0_forest,
            "act0_complete":    self.scene_act0_complete,
            "act1_cave":        self.scene_act1_cave,
            "act1_itoman":      self.scene_act1_itoman,
            "act1_language":    self.scene_act1_language_breaks,
            "act1_sora_trace":  self.scene_act1_sora_trace,
            "act1_path_choice": self.scene_act1_path_choice,
            "epilogue":         self.scene_epilogue,
        }
        handler = scene_map.get(scene_key)
        if handler:
            await handler(guild_id, owner_id)

    # Act 0

    async def scene_act0_enlistment(self, guild_id: int, owner_id: int):
        player = await db.get_player(guild_id, owner_id)
        if not player:
            return
        comp = "Nabi" if player["mc_gender"] == "male" else "Kenji"
        embed = discord.Embed(
            title="A Letter from Shimazu Takeo",
            description=(
                "*You will join me when the fleet makes port. Bring only what you can carry.*\n"
                "*Ryukyu is a small kingdom and its resistance will be brief.*\n"
                "*When it is done, there will be something worth showing you.*\n"
                "*Come ready to learn what it means to carry this name.*\n\n"
                "— Your Father\n\n"
                "*Received at Kagoshima, late winter, 1609.*\n\n"
                f"The sea crossing takes two weeks. You will meet your companion {comp} on the island. "
                "The compound burns at midnight.\n\n"
                "All 7 stats begin at 8. Your gear is determined by what you do next."
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 0 — Before the Fire")
        await db.update_scene(guild_id, owner_id, 0, "act0_courtyard")
        await self._post_to_commands(guild_id, owner_id, embed)
        await self.scene_act0_courtyard(guild_id, owner_id)

    async def scene_act0_courtyard(self, guild_id: int, owner_id: int):
        embed = discord.Embed(
            title="Two Weeks at the Compound",
            description=(
                "*The island smells like salt and something green and living underneath it. "
                "Nothing like Kagoshima. The men play dice near the cook fires. "
                "Lieutenant Mori — your father's second — keeps losing and laughing about it. "
                "You have been watching the treeline. You do not know why. "
                "Your father watches it too, from the other side of the courtyard, "
                "and you have not yet learned what it means when he goes quiet like that.*\n\n"
                "Day 14. The compound is secure. Satsuma holds the southern coast.\n\n"
                "The raid begins at the third hour past midnight."
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 0 — Before the Fire  |  Scene: The Compound")
        await db.update_scene(guild_id, owner_id, 0, "act0_scene1")
        await self._post_to_commands(guild_id, owner_id, embed)
        await self.scene_act0_burning_tent(guild_id, owner_id)

    async def scene_act0_burning_tent(self, guild_id: int, owner_id: int):
        embed = discord.Embed(
            title="The Tent Wall is Orange",
            description=(
                "*The tent wall is orange. You can hear it before you understand it — "
                "the sound of fire eating wood, and underneath it, something else. "
                "Steel. Voices in a language you don't know. "
                "You are already moving before you are fully awake, "
                "which is the only thing that saves you.*\n\n"
                "**Your tent is on fire. The entrance flap is still clear. "
                "Through the gap you can see the courtyard — shadows, torches thrown, men running. "
                "Your gear is beside your bedroll. You have three seconds.**"
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 0 — Scene 1  |  Burning Tent")
        flags = await story.get_flags(guild_id, owner_id)
        await self._post_to_commands(guild_id, owner_id, embed,
            view=Scene1View(guild_id, owner_id, self))

    async def scene_act0_courtyard_escape(self, guild_id: int, owner_id: int):
        embed = discord.Embed(
            title="The Courtyard",
            description=(
                "*The beam across his legs is burning at one end. "
                "He has maybe a minute before it reaches him. "
                "Three soldiers run past without looking. "
                "You look. He sees you look. "
                "For a moment the entire courtyard narrows down to just that — "
                "his eyes finding yours across the smoke and the screaming.*"
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 0 — Scene 2  |  The Courtyard")
        await self._post_to_commands(guild_id, owner_id, embed,
            view=Scene2View(guild_id, owner_id, self))

    async def scene_act0_armory(self, guild_id: int, owner_id: int):
        flags   = await story.get_flags(guild_id, owner_id)
        unarmed = not flags.get("GRABBED_GEAR_ACT0")
        note    = "\n\n*(You left without a weapon. A standard blade is on the rack.)*" if unarmed else ""
        embed   = discord.Embed(
            title="The Armory",
            description=(
                "*Your father's sword is on the rack nearest the door. "
                "You recognize the handle before you see the blade — "
                "the worn silk wrapping, the small dent in the guard from a sparring accident three years ago. "
                "He always kept it here when he slept. "
                "He said a sword in the tent was a sword you couldn't reach when you needed it.*"
                + note
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 0 — Scene 3  |  The Armory")
        await self._post_to_commands(guild_id, owner_id, embed,
            view=Scene3View(guild_id, owner_id, self, unarmed=unarmed))

    async def scene_act0_gate(self, guild_id: int, owner_id: int):
        embed = discord.Embed(
            title="The Gate — Lieutenant Mori",
            description=(
                "*He sees you before you see him.*\n\n"
                "*'Shimazu.' His voice is controlled — the voice of a man deciding not to be afraid out loud. "
                "'Go. I'll hold here.'*\n\n"
                "*He won't. You both know he won't. "
                "The gate is twenty meters and open ground and the treeline is moving.*"
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 0 — Scene 4  |  The Gate")
        await self._post_to_commands(guild_id, owner_id, embed,
            view=Scene4View(guild_id, owner_id, self))

    async def scene_act0_father(self, guild_id: int, owner_id: int):
        embed = discord.Embed(
            title="Behind the Barracks",
            description=(
                "*Your father falls forward. "
                "The young warrior stands over him for a moment — not triumphant, not relieved. Just still. "
                "Then they look up and find you across the smoke and distance, "
                "and for a second you are both frozen in it. "
                "Their eyes are very clear. They will remember your face. "
                "You will remember theirs.*\n\n"
                "*Sora turns and disappears into the treeline. "
                "Your father does not move.*"
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 0 — Scene 5  |  The Father")
        await story.set_flags(guild_id, owner_id, FATHER_KILLER="SORA", SORA_SAW_MC=True)
        await db.update_scene(guild_id, owner_id, 0, "act0_forest")
        await self._post_to_commands(guild_id, owner_id, embed)
        await self.scene_act0_forest(guild_id, owner_id)

    async def scene_act0_forest(self, guild_id: int, owner_id: int):
        embed = discord.Embed(
            title="The Forest Edge",
            description=(
                "*The island is very dark away from the fire. "
                "You can hear the sea somewhere to the south. "
                "You cannot hear your father's voice. "
                "You could not have heard it anyway, from here. "
                "You tell yourself this.*"
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 0 — Scene 6  |  The Forest Edge")
        await self._post_to_commands(guild_id, owner_id, embed,
            view=Scene6View(guild_id, owner_id, self))

    async def scene_act0_complete(self, guild_id: int, owner_id: int):
        player = await db.get_player(guild_id, owner_id)
        flags  = await story.get_flags(guild_id, owner_id)
        mc     = f"Shimazu {player['mc_first_name']}"

        summary = []
        if flags.get("TOOK_FATHERS_SWORD"):
            summary.append("Takeda's Blade (relic). Trait: Heir's Burden.")
        elif player.get("equipped_weapon") == "katana":
            summary.append("Katana (ATK 10).")
        if flags.get("TOOK_SUPPLIES_ACT0"):
            summary.append("3x Medicine, 2x Rations.")
        if flags.get("DAICHI_SAVED"):
            summary.append("Daichi joins as starting band member. Trait: Indebted.")
        if flags.get("MORI_SAVED"):
            summary.append("Mori survived. Trait: Mori's Debt. Intel once per act.")
        if flags.get("LOOKED_BACK"):
            summary.append("Grief trait — -1 ATK/-1 Resolve for first 3 battles.")

        embed = discord.Embed(
            title="Act 0 — Complete",
            description=(
                f"*The screen goes black.*\n\n"
                f"**{mc} wakes in a cave on the hillside. They are not alone.**\n\n"
                "Act 1 — Survival begins."
            ),
            color=COLOR_STORY,
        )
        if summary:
            embed.add_field(name="Escape Summary", value="\n".join(summary), inline=False)
        embed.set_footer(text="Act 0 — Complete  |  Act 1 begins")

        from utils.map_render import seed_player_map
        from utils.satsuma_ai import spawn_act_units
        await seed_player_map(guild_id, owner_id)
        await spawn_act_units(guild_id, owner_id, 1)
        await db.update_scene(guild_id, owner_id, 1, "act1_cave")
        await db.set_leaderboard_act(guild_id, owner_id, 1)
        await self._post_to_commands(guild_id, owner_id, embed)
        await self.scene_act1_cave(guild_id, owner_id)

    # Act 1

    async def scene_act1_cave(self, guild_id: int, owner_id: int):
        companion = await db.get_companion(guild_id, owner_id)
        comp      = companion["companion_name"] if companion else "the stranger"
        embed     = discord.Embed(
            title="The Cave — Dawn",
            description=(
                f"*The light at the cave mouth is the grey-pink of very early morning. "
                f"The person watching you is young — your age, or close to it. "
                f"They are Ryukyuan. "
                f"They have a small knife at their belt and no other visible weapon. "
                f"They say something short, in a language you cannot follow, "
                f"and hold out a piece of dried fish. "
                f"They wait to see what you do with it.*\n\n"
                f"This is **{comp}**.\n\n"
                "**Language Barrier active.** "
                "Their dialogue appears in Ryukyuan. "
                "Response options are physical only until the barrier breaks."
            ),
            color=COLOR_STORY,
        )
        embed.add_field(name="Companion Trust",
            value="Tier 0 — Cautious. Build trust through actions, not words.", inline=False)
        embed.set_footer(text="Act 1 — Survival  |  Scene: The Cave")
        await db.update_scene(guild_id, owner_id, 1, "act1_first_steps")
        await self._post_to_commands(guild_id, owner_id, embed)

    async def scene_act1_itoman(self, guild_id: int, owner_id: int):
        embed = discord.Embed(
            title="Itoman — Village Square",
            description=(
                "*The elder looks at you the way he might look at a storm on the horizon — "
                "calculating what it will do before it arrives. "
                "The companion speaks to him at length. He answers. "
                "Then he looks at you again, and something in his expression shifts. "
                "Not warmth, exactly, but a decision. "
                "He gestures toward a storage building. He says one word you understand: "
                "the Japanese word for stay.*\n\n"
                "**Itoman is now available as a base of operations.**"
            ),
            color=COLOR_STORY,
        )
        embed.add_field(name="Available at Itoman",
            value="Rest (+Loyalty, HP restore)  |  Recruit fighters  |  Contracts", inline=False)
        embed.set_footer(text="Act 1 — Survival  |  Scene: Itoman Village")
        await db.update_scene(guild_id, owner_id, 1, "act1_contracts")
        await self._post_to_commands(guild_id, owner_id, embed)

    async def scene_act1_language_breaks(self, guild_id: int, owner_id: int):
        companion = await db.get_companion(guild_id, owner_id)
        comp      = companion["companion_name"] if companion else "the companion"
        embed     = discord.Embed(
            title="The Language Breaks",
            description=(
                f"*{comp} has been sharpening their knife for ten minutes without speaking. "
                f"Then they say something longer than a warning. "
                f"You gesture — you don't understand. "
                f"They pause. Then, very carefully, in broken and hard-won Japanese, they try again.*\n\n"
                f"*'My grandmother taught me your language. A little. "
                f"She said it was useful to know the words of people who might come to take things from you.' "
                f"A pause. "
                f"'I did not think I would need it this soon.' "
                f"They go back to sharpening the knife. "
                f"After a moment, they look up. "
                f"'You can ask me things now. If you want.'*\n\n"
                "**Language barrier lifted. Full dialogue now available.**\n"
                f"**{comp}'s trust advances to Ally (Tier 2).**\n"
                f"**{comp} mentions their grandmother lives in the north.**"
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 1 — Survival  |  Scene: The Language Breaks")
        await story.set_flags(guild_id, owner_id, LANGUAGE_BREAKS=True)
        if companion:
            await db.update_companion(guild_id, owner_id, trust_tier=max(2, companion["trust_tier"]))
        await db.adjust_loyalty(guild_id, owner_id, 5)
        await db.update_scene(guild_id, owner_id, 1, "act1_post_language")
        await self._post_to_commands(guild_id, owner_id, embed)

    async def scene_act1_sora_trace(self, guild_id: int, owner_id: int):
        companion = await db.get_companion(guild_id, owner_id)
        comp      = companion["companion_name"] if companion else "the companion"
        embed     = discord.Embed(
            title="The Burned Depot",
            description=(
                f"*{comp} straightens up and looks at the treeline. "
                f"'I know who did this,' they say. "
                f"Not proudly. Not with satisfaction. Something more complicated than either. "
                f"'We should move. They will not have gone far, "
                f"and they will not be glad to see you.'*\n\n"
                "Sora's presence is now registered on the overworld. "
                "You may occasionally see a sighting marker on the map — a hex briefly highlighted — "
                "before it clears."
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 1 — Survival  |  Scene: Sora, at Distance")
        await story.set_flags(guild_id, owner_id, SORA_TRACE_FOUND=True)
        await db.update_scene(guild_id, owner_id, 1, "act1_approaching_choice")
        await self._post_to_commands(guild_id, owner_id, embed)

    async def scene_act1_path_choice(self, guild_id: int, owner_id: int):
        # Auto-save before path choice
        player    = await db.get_player(guild_id, owner_id)
        band_size = await db.get_band_size(guild_id, owner_id)
        from utils.saves import build_snapshot
        from utils.embeds import act_label
        snapshot = await build_snapshot(guild_id, owner_id)
        await db.write_save(guild_id, owner_id, 1, snapshot,
            "Before Path Choice — Act 1/2 Boundary", band_size)

        embed = discord.Embed(
            title="The Officer's Visit",
            description=(
                "*The fire has burned down to coals by the time you look at each other. "
                "The night sounds of Ryukyu fill the space where conversation should be. "
                "The companion's face is very calm. "
                "It is the calm of someone who has already decided something "
                "and is waiting to find out if you have too.*\n\n"
                "A Satsuma officer has delivered orders. "
                "General Iso Tadanaga requires your presence at Naha by morning. "
                "Your continued absence will be interpreted.\n\n"
                "**This choice is permanent. A save has been written to Slot 1.**"
            ),
            color=COLOR_STORY,
        )
        embed.set_footer(text="Act 1 — End  |  Path Choice  |  Auto-save written to Slot 1")
        await self._post_to_commands(guild_id, owner_id, embed,
            view=PathChoiceView(guild_id, owner_id, self))

    async def _check_and_trigger_act1_scenes(self, guild_id: int, owner_id: int):
        """Called after contract completion or End Turn to auto-fire Act 1 scenes when conditions met."""
        import utils.db as db2
        from utils.story_engine import get_flags, set_flags
        player   = await db2.get_player(guild_id, owner_id)
        if not player or player.get("current_act", 0) != 1:
            return
        flags    = await get_flags(guild_id, owner_id)
        scene    = player.get("current_scene","")
        cache    = await db2.get_leaderboard(guild_id)
        row      = next((r for r in cache if r["owner_id"]==owner_id), {})
        contracts_done = row.get("contracts_completed", 0)
        companion = await db2.get_companion(guild_id, owner_id)
        trust     = companion.get("trust_tier", 0) if companion else 0

        # Scene: Language Breaks — after 3 contracts + companion trust Tier 1+
        if (not flags.get("LANGUAGE_BREAKS")
                and contracts_done >= 3
                and trust >= 1
                and scene not in ("act1_language","act1_post_language","act1_sora_trace",
                                  "act1_approaching_choice","act1_path_choice")):
            await self.scene_act1_language_breaks(guild_id, owner_id)
            return

        # Scene: Sora Trace — after language breaks + 1 more contract
        if (flags.get("LANGUAGE_BREAKS")
                and not flags.get("SORA_TRACE_FOUND")
                and contracts_done >= 4
                and scene not in ("act1_sora_trace","act1_approaching_choice","act1_path_choice")):
            await self.scene_act1_sora_trace(guild_id, owner_id)
            return

        # Scene: Path Choice — after 5 contracts + language breaks + sora trace
        if (flags.get("LANGUAGE_BREAKS")
                and flags.get("SORA_TRACE_FOUND")
                and contracts_done >= 5
                and scene not in ("act1_path_choice","act0_complete")):
            await self.scene_act1_path_choice(guild_id, owner_id)
            return

    async def scene_epilogue(self, guild_id: int, owner_id: int):
        segments = await story.generate_epilogue(guild_id, owner_id)
        opener   = discord.Embed(
            title="Epilogue — What the Island Remembers",
            description="*The island does not forget.*",
            color=COLOR_STORY,
        )
        await self._post_to_commands(guild_id, owner_id, opener,
            view=EpilogueView(guild_id, owner_id, segments))


async def setup(bot):
    await bot.add_cog(StoryCog(bot))