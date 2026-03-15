import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import datetime
import sqlite3
# Base directory
Base_dir = os.path.dirname(os.path.abspath(__file__))
# Add your naughty words here
naughty_words = ["--placeholder--"]

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True


#create a database to store the number of warnings per user
def create_user_table():
    conn = sqlite3.connect(os.path.join(Base_dir, "users_warning.db"))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_per_guild (
            user_id INTEGER,
            warning_count INTEGER,
            guild_id INTEGER,
            PRIMARY KEY(user_id, guild_id)
        )
    """)

    conn.commit()
    conn.close()


create_user_table()

#increase the number of warnings per user
def increase_and_get_warning_count(user_id, guild_id):
    conn = sqlite3.connect(os.path.join(Base_dir, "users_warning.db"))
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT warning_count 
        FROM users_per_guild 
        WHERE user_id = ? AND guild_id = ?
    """,
        (user_id, guild_id),
    )
    result = cursor.fetchone()

    if result is None:
        cursor.execute(
            """
            INSERT INTO users_per_guild (user_id, warning_count, guild_id)
            VALUES (?, 1, ?)
        """,
            (user_id, guild_id),
        )
        conn.commit()
        conn.close()
        return 1

    cursor.execute(
        """
        UPDATE users_per_guild
        SET warning_count = ?
        WHERE user_id = ? AND guild_id = ?
    """,
        (result[0] + 1, user_id, guild_id),
    )

    conn.commit()
    conn.close()
    return result[0] + 1


bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}, bot is online")

#check if the message contains a naughty word
@bot.event
async def on_message(message):
    if message.author.id != bot.user.id:
        for word in naughty_words:
            if word.lower() in message.content.lower():
                num_warnings = increase_and_get_warning_count(
                    message.author.id, message.guild.id
                )

                if num_warnings >= 3:
                    await message.author.timeout(
                        datetime.timedelta(minutes=120),
                        reason="Saying too much naughty words",
                    )
                    await message.channel.send(
                        f"{message.author.mention} has been timed out for 2 hours for saying too much naughty words"
                    )
                    await message.delete()
                    break

                if num_warnings == 1:
                    await message.author.send(
                        "Please do not say naughty words, you have been warned, 1 more time and you'll be timed out for an hour"
                    )
                    await message.channel.send(
                        f"{message.author.mention} Please do not say naughty words"
                    )
                    await message.delete()
                    break

                if num_warnings == 2:
                    await message.author.timeout(
                        datetime.timedelta(minutes=60),
                        reason="Saying too much naughty words",
                    )
                    await message.author.send(
                        "You have been timed out for an hour for saying too much naughty words, one more time and you'll be timed out for 2 hours"
                    )
                    await message.channel.send(
                        f"{message.author.mention} has been timed out for an hour for saying too much naughty words"
                    )
                    await message.delete()
                    break

    await bot.process_commands(message)

#clear the number of warnings per user
@bot.command()
@commands.has_permissions(moderate_members=True)
async def clearwarnings(ctx, member: discord.Member):
    conn = sqlite3.connect(os.path.join(Base_dir, "users_warning.db"))
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM users_per_guild
        WHERE user_id = ? AND guild_id = ?
    """,
        (member.id, ctx.guild.id),
    )
    conn.commit()
    conn.close()
    await ctx.send(f"Warnings for {member.mention} have been cleared.")


@clearwarnings.error
async def clearwarnings_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Member not found.")


TOKEN = os.getenv("DISCORD_TOKEN")

bot.run(TOKEN)
