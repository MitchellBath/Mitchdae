import os
import discord
from discord.ext import commands
import random
import aiosqlite
import dotenv
import asyncio

dotenv.load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
guild = discord.Object(id=GUILD_ID)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables. Check your .env file.")


intents = discord.Intents.default()
intents.message_content = True

class MitchdaeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.synced = False

    async def setup_hook(self):
        # This runs before on_ready()
        await setup_db()
        await genChars(adjs, nouns)
        print("Database setup complete.")

    async def on_ready(self):
        if not self.synced:
            await self.tree.sync()
            self.synced = True
        print(f"Logged in as {self.user}")

bot = MitchdaeBot()


# ======================
# DATABASE SETUP
# ======================
async def setup_db():
    async with aiosqlite.connect("mitchdae.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            discord_id INTEGER UNIQUE,
            cash INTEGER DEFAULT 0
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            power INTEGER
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_characters (
            user_id INTEGER,
            character_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(character_id) REFERENCES characters(id)
        );
        """)
        await db.commit()

# generate characters at runtime
adjs = [
    "All-in",
    "Caveman",
    "Date Rate",
    "(R)",
    "(D)",
    "AI Torture",
    "Sovi",
    "Sanford",
    "Gambler",
    "Cuck",
    "Racist",
    "Ultimate",
    "Skeleton",
    "Bootlicker",
    "Clanker",
    "Stanker",
    "Deadbeat",
    "Chonky",
    "In 5 Years",
    "Out Night",
    "Gay",
    "Bad Gay",
    "Good Gay",
    "Bisexual",
    "Heterosexual",
    "Straight",
    "LAN Party",
    "Wizard",
    "Trucker",
    "Pregnant",
    "Filled",
    "NPC",
    "Chicken Jockey",
    "Shut Up Cracker",
    "Cracker",
    "Fishy",
    "Old Yeller",
    "Godlike",
    "Wimpy",
    "Cum",
    "Cumming",
    "Splooger",
    "Lizard",
    "Trough",
    "English Degree",
    "Hole-filled",
    "Minecraft"
]
nouns = [
    "Mitch",
    "Kaden",
    "William",
    "David",
    "Brendan",
    "Victor"
    "Krusk",
    "Stranger",
    "Bimblore",
    "Khulli",
    "Dwayne",
    "Poopshit",
    "Vinkledorf",
    "Chung Pao",
    "Esrit",
    "Ihsoy",
    "Ri'ik",
    "Goobus",
    "beingDevisor",
    "BluePineapple",
    "Ketasive",
    "Fedsmoker",
    "Mobility Mary",
    "White Whale",
    "Epstein",
    "Trump",
    "Biden",
    "Xan",
    "Josh",
    "Wither Skeleton",
    "Wither",
    "Asian Baby",
    "Coup Game",
    "Drywall"
]

# ======================
# BOT EVENTS
# ======================

# ======================
# COMMANDS
# ======================

# Roll three random characters
@bot.tree.command(name="roll", description="Roll for a random set of characters.")
async def roll(interaction: discord.Interaction):
    async with aiosqlite.connect("mitchdae.db") as db:
        async with db.execute("SELECT name, power FROM characters ORDER BY RANDOM() LIMIT 3;") as cursor:
            results = await cursor.fetchall()

    if not results:
        await interaction.response.send_message("No characters found in the database.")
        return

    choices = [f"{i+1}. {name} (Power {power})" for i, (name, power) in enumerate(results)]
    msg = "\n".join(choices)
    await interaction.response.send_message(f"Your roll:\n{msg}\nType the number of the character you want to claim!")

    def check(m):
        return (
            m.author.id == interaction.user.id
            and m.channel.id == interaction.channel.id
            and m.content.isdigit()
            and 1 <= int(m.content) <= 3
        )

    try:
        reply = await bot.wait_for("message", check=check, timeout=20.0)
        choice = int(reply.content) - 1
        name, power = results[choice]

        async with aiosqlite.connect("mitchdae.db") as db:
            await db.execute("INSERT OR IGNORE INTO users (discord_id) VALUES (?);", (interaction.user.id,))
            async with db.execute("SELECT id FROM users WHERE discord_id = ?;", (interaction.user.id,)) as cursor:
                (user_id,) = await cursor.fetchone()
            async with db.execute("SELECT id FROM characters WHERE name = ?;", (name,)) as cursor:
                (char_id,) = await cursor.fetchone()
            await db.execute("INSERT INTO user_characters (user_id, character_id) VALUES (?, ?);", (user_id, char_id))
            await db.commit()

        await interaction.followup.send(f"You claimed **{name}** with Power {power}!")

    except Exception:
        await interaction.followup.send("You didn’t pick in time!")


# Battle another user
@bot.tree.command(name="battle", description="Battle another user to compare your characters' power levels.")
async def battle(interaction: discord.Interaction, opponent: discord.Member):
    async with aiosqlite.connect("mitchdae.db") as db:
        async with db.execute("SELECT id FROM users WHERE discord_id = ?;", (interaction.user.id,)) as cursor:
            user_row = await cursor.fetchone()
        async with db.execute("SELECT id FROM users WHERE discord_id = ?;", (opponent.id,)) as cursor:
            opp_row = await cursor.fetchone()

        if not user_row or not opp_row:
            await interaction.response.send_message("Both players need to have characters!")
            return

        user_id = user_row[0]
        opp_id = opp_row[0]

        async with db.execute("""
        SELECT c.name, c.power FROM characters c
        JOIN user_characters uc ON uc.character_id = c.id
        WHERE uc.user_id = ?
        ORDER BY RANDOM() LIMIT 1;
        """, (user_id,)) as cursor:
            user_char = await cursor.fetchone()

        async with db.execute("""
        SELECT c.name, c.power FROM characters c
        JOIN user_characters uc ON uc.character_id = c.id
        WHERE uc.user_id = ?
        ORDER BY RANDOM() LIMIT 1;
        """, (opp_id,)) as cursor:
            opp_char = await cursor.fetchone()

    if not user_char or not opp_char:
        await interaction.response.send_message("Both players need at least one character!")
        return

    uname, upower = user_char
    oname, opower = opp_char

    result = f"{interaction.user.display_name}'s **{uname} ({upower})** vs {opponent.display_name}'s **{oname} ({opower})**\n"
    if upower > opower:
        result += f"🏆 {interaction.user.display_name} wins!"
    elif opower > upower:
        result += f"🏆 {opponent.display_name} wins!"
    else:
        result += "It's a tie!"

    await interaction.response.send_message(result)


async def genChars(adjs, nouns):
    async with aiosqlite.connect("mitchdae.db") as db:
        async with db.execute("SELECT COUNT(*) FROM characters;") as cursor:
            (count,) = await cursor.fetchone()
        if count > 0:
            print("Characters already exist; skipping generation.")
            return

        for a in adjs:
            for n in nouns:
                name = f"{a} {n}"
                power = random.randint(0, 999)
                await db.execute("INSERT INTO characters (name, power) VALUES (?, ?);", (name, power))
        await db.commit()
        print(f"{len(adjs)*len(nouns)} characters generated!")




# Add new characters (admin-only)
@bot.tree.command(name="addchar", description="Add a new character to the database.")
async def addchar(interaction: discord.Interaction, name: str, power: int):
    """Adds a character to the database with a power level between 0 and 999."""
    # Check power bounds
    if power < 0 or power > 999:
        await interaction.response.send_message("Power must be between 0 and 999.", ephemeral=True)
        return

    # Insert into database
    async with aiosqlite.connect("mitchdae.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO characters (name, power) VALUES (?, ?);",
            (name, power)
        )
        await db.commit()

    await interaction.response.send_message(f"✅ Added character **{name}** with power {power}.", ephemeral=True)

# view chars
@bot.tree.command(name="mychars", description="View all characters you have claimed.")
async def mychars(interaction: discord.Interaction):
    async with aiosqlite.connect("mitchdae.db") as db:
        # Get user ID
        async with db.execute("SELECT id FROM users WHERE discord_id = ?;", (interaction.user.id,)) as cursor:
            user_row = await cursor.fetchone()

        if not user_row:
            await interaction.response.send_message("You have no characters yet!", ephemeral=True)
            return

        user_id = user_row[0]

        # Get all characters
        async with db.execute("""
            SELECT c.name, c.power
            FROM characters c
            JOIN user_characters uc ON uc.character_id = c.id
            WHERE uc.user_id = ?
            ORDER BY c.name;
        """, (user_id,)) as cursor:
            chars = await cursor.fetchall()

    if not chars:
        await interaction.response.send_message("You have no characters yet!", ephemeral=True)
        return

    msg = "\n".join(f"**{name}** (Power {power})" for name, power in chars)
    await interaction.response.send_message(f"Your characters:\n{msg}", ephemeral=True)

# clear user
@bot.tree.command(name="deletechars", description="Delete all characters you have claimed.")
async def deletechars(interaction: discord.Interaction):
    async with aiosqlite.connect("mitchdae.db") as db:
        # Get user ID
        async with db.execute("SELECT id FROM users WHERE discord_id = ?;", (interaction.user.id,)) as cursor:
            user_row = await cursor.fetchone()

        if not user_row:
            await interaction.response.send_message("You have no characters to delete.", ephemeral=True)
            return

        user_id = user_row[0]

        # Delete all characters for this user
        await db.execute("DELETE FROM user_characters WHERE user_id = ?;", (user_id,))
        await db.commit()

    await interaction.response.send_message("✅ All your characters have been deleted.", ephemeral=True)


@bot.tree.command(name="sacrifice", description="Turn a character into cash.")
async def sacrifice(interaction: discord.Interaction, character_name: str):
    await interaction.response.defer()

    async with aiosqlite.connect("mitchdae.db") as db:
        # 1. Get the user's ID
        async with db.execute("SELECT id FROM users WHERE discord_id = ?;", (interaction.user.id,)) as cursor:
            result = await cursor.fetchone()
            if not result:
                await interaction.followup.send("You don't have any characters yet!")
                return
            (user_id,) = result
        # 2. Verify they own the character
        async with db.execute("""
            SELECT c.id, c.power
            FROM characters c
            JOIN user_characters uc ON uc.character_id = c.id
            WHERE uc.user_id = ? AND LOWER(c.name) = LOWER(?);
        """, (user_id, character_name)) as cursor:
            row = await cursor.fetchone()
        if not row:
            await interaction.followup.send("You do not own that character.")
            return
        char_id, power = row
        # 3. Delete the character from the user's inventory
        await db.execute("DELETE FROM user_characters WHERE user_id = ? AND character_id = ?;", (user_id, char_id))
        # 4. Update or insert the user's cash manually
        async with db.execute("SELECT cash FROM users WHERE discord_id = ?;", (interaction.user.id,)) as cursor:
            existing = await cursor.fetchone()
        if existing is None:
            await db.execute("INSERT INTO users (discord_id, cash) VALUES (?, ?);", (interaction.user.id, power))
        else:
            await db.execute("UPDATE users SET cash = cash + ? WHERE discord_id = ?;", (power, interaction.user.id))
        await db.commit()

    await interaction.followup.send(f"You sacrificed **{character_name}** for 💰 **{power} Cash**.")




bot.run(BOT_TOKEN)