# Story Engine
import utils.db as db
from utils.traits import assign_story_trait, assign_companion_trait

# All story flag keys
F = {
    "FATHER_KILLER":          "FATHER_KILLER",
    "SORA_SAW_MC":            "SORA_SAW_MC",
    "LOOKED_BACK":            "LOOKED_BACK",
    "LANGUAGE_BREAKS":        "LANGUAGE_BREAKS",
    "SORA_TRACE_FOUND":       "SORA_TRACE_FOUND",
    "PATH_CHOICE":            "PATH_CHOICE",
    "MERCIFUL_FIGHT_1":       "MERCIFUL_FIGHT_1",
    "ISO_KNOWS_SOMETHING":    "ISO_KNOWS_SOMETHING",
    "SORA_DUEL_COUNT":        "SORA_DUEL_COUNT",
    "SORA_DUEL_RESULT_1":     "SORA_DUEL_RESULT_1",
    "SORA_DUEL_RESULT_2":     "SORA_DUEL_RESULT_2",
    "SORA_DUEL_RESULT_3":     "SORA_DUEL_RESULT_3",
    "SORA_SPARED":            "SORA_SPARED",
    "SORA_KILLED":            "SORA_KILLED",
    "SORA_CONFESSION":        "SORA_CONFESSION",
    "CIVILIAN_WITNESS":       "CIVILIAN_WITNESS",
    "ISO_RELAYS_SORA":        "ISO_RELAYS_SORA",
    "MORI_SAVED":             "MORI_SAVED",
    "MORI_ARMED":             "MORI_ARMED",
    "DAICHI_SAVED":           "DAICHI_SAVED",
    "GRABBED_GEAR_ACT0":      "GRABBED_GEAR_ACT0",
    "TOOK_FATHERS_SWORD":     "TOOK_FATHERS_SWORD",
    "TOOK_SUPPLIES_ACT0":     "TOOK_SUPPLIES_ACT0",
    "ACT0_COMPLETE":          "ACT0_COMPLETE",
    "ACT1_COMPLETE":          "ACT1_COMPLETE",
    "ACT2_COMPLETE":          "ACT2_COMPLETE",
    "ACT3_COMPLETE":          "ACT3_COMPLETE",
    "HANA_MET":               "HANA_MET",
    "ISO_MET":                "ISO_MET",
    "TANGLED_THREAD_STARTED": "TANGLED_THREAD_STARTED",
    "TANGLED_THREAD_COMPLETE":"TANGLED_THREAD_COMPLETE",
    "KATSUREN_COMPLETE":      "KATSUREN_COMPLETE",
    "COMPANION_RESCUED":      "COMPANION_RESCUED",
    "COMPANION_TRUST_TIER":   "COMPANION_TRUST_TIER",
    "SORA_ORIGIN_KNOWN":      "SORA_ORIGIN_KNOWN",
    "SHURI_APPROACH":         "SHURI_APPROACH",
    "CAMPAIGN_COMPLETE":      "CAMPAIGN_COMPLETE",
}


async def get_flags(guild_id: int, owner_id: int) -> dict:
    row = await db.get_story_flags(guild_id, owner_id)
    return row.get("flags") or {}


async def set_flags(guild_id: int, owner_id: int, **kw):
    await db.update_story_flags(guild_id, owner_id, **kw)


# Act 0 escape scene handlers

async def scene1_choice(guild_id: int, owner_id: int, choice: str):
    """Burning Tent. choice: grab_gear | run"""
    if choice == "grab_gear":
        await db.update_player(guild_id, owner_id,
            equipped_weapon="katana", equipped_weapon_tier=1, atk=10,
            equipped_armor="ashigaru_armor", equipped_armor_tier=1, def_=9)
        await set_flags(guild_id, owner_id, GRABBED_GEAR_ACT0=True)
    else:
        # Ran — no weapon yet, slightly faster
        await db.update_player(guild_id, owner_id,
            equipped_armor="ashigaru_armor", equipped_armor_tier=1, spd=10)
    await db.update_scene(guild_id, owner_id, 0, "act0_courtyard")


async def scene2_choice(guild_id: int, owner_id: int, choice: str):
    """Courtyard / Lt. Daichi. choice: pull_free | keep_moving"""
    if choice == "pull_free":
        await db.add_band_member(guild_id, owner_id, "Daichi", "Ashigaru", {
            "hp":80,"max_hp":80,"atk":8,"def":8,"spd":8,
            "resolve":8,"recon":8,"individual_loyalty":70
        })
        await db.adjust_loyalty(guild_id, owner_id, 5)
        await assign_story_trait(guild_id, owner_id, "Indebted")
        await set_flags(guild_id, owner_id, DAICHI_SAVED=True)
    await db.update_scene(guild_id, owner_id, 0, "act0_armory")


async def scene3_choice(guild_id: int, owner_id: int, choice: str):
    """Armory. choice: fathers_sword | supplies | both (unarmed only)"""
    flags = await get_flags(guild_id, owner_id)
    unarmed = not flags.get("GRABBED_GEAR_ACT0")

    if choice in ("fathers_sword", "both"):
        if not unarmed and choice == "both":
            choice = "fathers_sword"  # Can't take both if already armed
        await db.update_player(guild_id, owner_id,
            equipped_weapon="takeda_blade", equipped_weapon_tier=1, atk=13)
        await db.add_item(guild_id, owner_id, "takeda_blade", 1, is_relic=True)
        await assign_story_trait(guild_id, owner_id, "Heir's Burden")
        await set_flags(guild_id, owner_id, TOOK_FATHERS_SWORD=True)

    if choice in ("supplies", "both"):
        await db.add_item(guild_id, owner_id, "medicine", 3)
        await db.add_item(guild_id, owner_id, "rations", 2)
        await set_flags(guild_id, owner_id, TOOK_SUPPLIES_ACT0=True)

    # Give standard katana if still unarmed
    player = await db.get_player(guild_id, owner_id)
    if not player.get("equipped_weapon"):
        await db.update_player(guild_id, owner_id,
            equipped_weapon="katana", equipped_weapon_tier=1, atk=10)

    await db.update_scene(guild_id, owner_id, 0, "act0_gate")


async def scene4_choice(guild_id: int, owner_id: int, choice: str):
    """The Gate / Lt. Mori. choice: carry | give_weapon | leave"""
    if choice == "carry":
        await db.add_item(guild_id, owner_id, "mori_seal", 1, is_relic=True)
        await db.adjust_loyalty(guild_id, owner_id, 5)
        await set_flags(guild_id, owner_id, MORI_SAVED=True)
        await assign_story_trait(guild_id, owner_id, "Mori's Debt")
    elif choice == "give_weapon":
        await set_flags(guild_id, owner_id, MORI_ARMED=True)
    else:
        # Mori dies
        await db.increment_trait_counter(guild_id, owner_id, "mc", "band_deaths_witnessed", 1)
    await db.update_scene(guild_id, owner_id, 0, "act0_father")


async def scene6_choice(guild_id: int, owner_id: int, choice: str):
    """Forest Edge. choice: look_back | keep_walking"""
    if choice == "look_back":
        await assign_story_trait(guild_id, owner_id, "Grief")
        await set_flags(guild_id, owner_id, LOOKED_BACK=True)
    await set_flags(guild_id, owner_id,
        FATHER_KILLER="SORA", SORA_SAW_MC=True, ACT0_COMPLETE=True)
    await db.update_scene(guild_id, owner_id, 0, "act0_complete")


# Path choice

async def apply_path_choice(guild_id: int, owner_id: int, path: str):
    await db.update_player(guild_id, owner_id, path_choice=path, current_act=2)
    await set_flags(guild_id, owner_id, PATH_CHOICE=path, ACT1_COMPLETE=True)
    await db.set_leaderboard_act(guild_id, owner_id, 2)

    if path == "ghost":
        companion = await db.get_companion(guild_id, owner_id)
        if companion:
            new_trust = min(3, companion["trust_tier"] + 1)
            await db.update_companion(guild_id, owner_id, trust_tier=new_trust)
        pool = await db.get_pool()
        async with pool.acquire() as c:
            await c.execute(
                "UPDATE faction_standing SET satsuma_standing=0 WHERE guild_id=$1 AND owner_id=$2",
                guild_id, owner_id)
        await assign_story_trait(guild_id, owner_id, "Deserter")

    elif path == "blade":
        await db.update_companion(guild_id, owner_id, is_present=False)
        await db.adjust_loyalty(guild_id, owner_id, -15)
        pool = await db.get_pool()
        async with pool.acquire() as c:
            await c.execute(
                "UPDATE faction_standing SET ryukyuan_standing=0 WHERE guild_id=$1 AND owner_id=$2",
                guild_id, owner_id)
        await assign_story_trait(guild_id, owner_id, "Oath-Bound")


# Sora duel tracking

async def record_sora_duel(guild_id: int, owner_id: int, result: str):
    """result: won | lost | draw | fled"""
    flags = await get_flags(guild_id, owner_id)
    count = int(flags.get("SORA_DUEL_COUNT") or 0) + 1
    await set_flags(guild_id, owner_id,
        SORA_DUEL_COUNT=count,
        **{f"SORA_DUEL_RESULT_{count}": result}
    )
    if result == "won" and count >= 3:
        await set_flags(guild_id, owner_id, SORA_KILLED=True)


# Act advancement

async def check_act_advancement(guild_id: int, owner_id: int) -> int | None:
    player = await db.get_player(guild_id, owner_id)
    if not player:
        return None
    flags = await get_flags(guild_id, owner_id)
    act   = player.get("current_act", 0)
    if act == 0 and flags.get("ACT0_COMPLETE"):
        return 1
    if act == 1 and flags.get("ACT1_COMPLETE") and flags.get("PATH_CHOICE"):
        return 2
    if act == 2 and flags.get("ACT2_COMPLETE") and flags.get("KATSUREN_COMPLETE"):
        return 3
    if act == 3 and flags.get("ACT3_COMPLETE"):
        return None  # Campaign complete
    return None


# Epilogue generator

async def generate_epilogue(guild_id: int, owner_id: int) -> list:
    player    = await db.get_player(guild_id, owner_id)
    companion = await db.get_companion(guild_id, owner_id)
    flags     = await get_flags(guild_id, owner_id)
    memorial  = await db.get_memorial(guild_id, owner_id)
    path      = player.get("path_choice")
    traits    = player.get("traits") or []
    mc        = f"Shimazu {player['mc_first_name']}"
    segments  = []

    # Opening
    segments.append({
        "title": "What Remains",
        "text": (
            f"The battle at Shuri ends. The island settles into a quiet "
            f"that sounds different from the quiet before. "
            f"{mc} stands at the coast and watches the sea. "
            f"What they carry out with them is everything that happened here."
        )
    })

    # Companion
    if companion:
        comp = companion["companion_name"]
        trust = companion.get("trust_tier", 0)
        present = companion.get("is_present", True)
        if path == "ghost" and present:
            if trust >= 4:
                segments.append({"title": comp, "text": (
                    f"{comp} stayed. After Shuri, they remained on the island. "
                    f"They did not ask {mc} to leave, and they did not ask them to stay. "
                    f"That too was a kind of answer."
                )})
            elif trust >= 2:
                segments.append({"title": comp, "text": (
                    f"{comp} and {mc} parted at the coast without ceremony. "
                    f"Some things do not require a last word."
                )})
            else:
                segments.append({"title": comp, "text": (
                    f"{comp} left before the final battle. They had their own road. "
                    f"{mc} understood."
                )})
        elif path == "blade":
            if flags.get("COMPANION_RESCUED"):
                segments.append({"title": comp, "text": (
                    f"{comp} was released after Shuri. No explanation was given. None was asked for. "
                    f"They walked north without looking back."
                )})
            else:
                segments.append({"title": comp, "text": (
                    f"{comp} had left long before Shuri. "
                    f"Whether they survived the occupation was not something {mc} was told."
                )})

    # Sora
    sora_spared    = flags.get("SORA_SPARED")
    sora_killed    = flags.get("SORA_KILLED")
    sora_duel_ct   = int(flags.get("SORA_DUEL_COUNT") or 0)
    sora_confession= flags.get("SORA_CONFESSION")
    sora_origin    = flags.get("SORA_ORIGIN_KNOWN")

    if path == "ghost":
        if sora_spared:
            text = (
                "Sora returned to Ryukyu after Shuri. "
                "Which side they returned to was not recorded. They had been on both."
            )
        elif sora_killed:
            text = (
                "Sora did not survive Shuri. The resistance remembered them differently depending on who you asked."
            )
        else:
            text = "Sora withdrew from the final engagement. What came after is not known."
        if sora_confession:
            text += (
                " What Sora had been told about the night of the raid — "
                "that the compound was a military target — "
                "was either the truth or the most convenient version of it."
            )
        if sora_origin:
            text += " Their history with the Shimazu clan ran deeper than either of them knew going in."
    else:
        if sora_spared:
            text = (
                f"Sora was held as a prisoner after Shuri, at {mc}'s request. "
                "Iso noted it without comment."
            )
        elif sora_killed:
            text = "Sora died at Shuri. The hunt Iso had framed as justice ended there."
        else:
            text = "Sora was not found at Shuri. The island kept them."

    if sora_duel_ct > 0:
        text += f" They had faced each other {sora_duel_ct} time{'s' if sora_duel_ct!=1 else ''} before the end."
    segments.append({"title": "Sora", "text": text})

    # Band memorial
    if memorial:
        names = [m["member_name"] for m in memorial[:6]]
        dead_str = ", ".join(names)
        if len(memorial) > 6:
            dead_str += f", and {len(memorial)-6} others"
        segments.append({"title": "Those Who Fell", "text": (
            f"{dead_str}. Their names were kept. "
            f"The island did not record them but the band did."
        )})

    # Mori
    if flags.get("MORI_SAVED") and path == "ghost":
        segments.append({"title": "Lt. Mori", "text": (
            "Mori survived the raid and made it off the island. "
            f"He sent word twice in the following year. "
            f"He never explained why he helped, but {mc} knew."
        )})

    # Iso
    if flags.get("ISO_MET"):
        if path == "blade":
            segments.append({"title": "General Iso", "text": (
                f"Iso filed his report. {mc} was mentioned once, in a list of officers who performed adequately. "
                "That was the last either of them said about it."
            )})
        else:
            segments.append({"title": "General Iso", "text": (
                "Iso never confirmed he knew where the defector was. "
                "He had the recon reports. He chose not to act on them. "
                "That was not something either of them discussed."
            )})

    # Hall traits
    if "Ghost King" in traits and path == "ghost":
        segments.append({"title": "The Ghost", "text": (
            f"{mc} became something the island didn't have a name for — "
            "not Satsuma, not Ryukyuan, not enemy, not ally. "
            "The stories that came later were all different. That was the point."
        )})
    elif "Conqueror" in traits and path == "blade":
        segments.append({"title": "The Conqueror", "text": (
            f"{mc} finished what their father started. The island was under Satsuma authority. "
            "Whether that was the right thing was a question they stopped asking."
        )})

    # Final MC line
    looked_back  = flags.get("LOOKED_BACK")
    took_sword   = flags.get("TOOK_FATHERS_SWORD")
    if path == "ghost" and looked_back:
        final = (
            f"{mc} left the island carrying the compound fire with them. "
            f"The moment before Sora looked up across the smoke — "
            f"they had looked back at it once. They never stopped."
        )
    elif path == "ghost" and not looked_back:
        final = (
            f"{mc} did not look back. Not at the forest edge in the dark, not at Shuri, not at the coast. "
            f"Some things you carry better without turning around."
        )
    elif path == "blade" and took_sword:
        final = (
            f"{mc} boarded the ship home with the sword. "
            f"The island got smaller. They had done what their father could not finish. "
            f"The sword was heavier than it used to be."
        )
    else:
        final = (
            f"{mc} stood at the water and waited for the fleet. "
            f"They had done what they came to do. The island let them leave. "
            f"The moment before Sora looked up across the smoke — "
            f"that was where it had all started, and they had carried it the whole way through."
        )
    segments.append({"title": "What the Island Remembers", "text": final})
    return segments
