# -*- coding: utf-8 -*-
"""
Discord Wordle Bot
Created on Sat Apr 12 18:10:17 2025
@author: rhybiq
"""

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime
from wordle import WordleGame
from nltk.corpus import words
from keep_alive import keep_alive
import logging
import asyncio
import os
import nltk
import Stats as stats  # Import the Stats module
import matplotlib.pyplot as plt
import io
import matplotlib.patches as patches
from words import fetch_word_meaning 
from words import get_words_list # Import the function to fetch word meaning

# Setup logging and environment
logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)
games = {}  # Keeps track of active games per user


async def heartbeat():
   while True:
        logging.info("Bot heartbeat")
        await asyncio.sleep(60)

# Initialize the database
@bot.event
async def on_ready():
    bot.loop.create_task(heartbeat())
   
    print(f'{bot.user} has connected to Discord!')
    try:
        # Clear and resync commands
         # Clear global commands
        synced = await bot.tree.sync()  # Sync commands
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Command: Start Wordle
@bot.tree.command(name="startwordle", description="Start a Wordle game with a specified word length.")
async def start_wordle(interaction: discord.Interaction, length: int = 5):
    try:
        await interaction.response.defer()  # Acknowledge the interaction immediately

        if length < 5 or length > 13:
            await interaction.followup.send("Please choose a word length between 5 and 13.")
            return

        # Fetch the list of words with the specified length
        filtered_words = get_words_list(length)
        if not filtered_words:
            await interaction.followup.send(f"No words found with length {length}. Try a different number.",ephemeral=True)
            return

        # Initialize the game for the user
        games[interaction.user.id] = {
            "game": WordleGame(filtered_words, word_length=length),
            "start_time": datetime.now()
        }

        # Update games played in the database
        await stats.update_games_played(
            user_id=str(interaction.user.id),
            server_id=str(interaction.guild.id),
            games_played=1
        )

        await interaction.followup.send(
            f"Wordle game started with {length}-letter words! You get {length + 1} guesses. Use `/guessword yourword` to make a guess."
        )
    except Exception as e:
        logging.error(f"Error in /startwordle: {e}")
        await interaction.followup.send("An error occurred while starting the game. Please try again later.")

# Command: Make a Guess
@bot.tree.command(name="guessword", description="Make a guess in your Wordle game.")
async def guess_word(interaction: discord.Interaction, guess: str):
    try:

        

        # Check if the user has an active game
        if interaction.user.id not in games:
            await interaction.response.send_message("You don't have an active game. Start one with `/startwordle`.", ephemeral=True)
            return

        game_data = games[interaction.user.id]
        game = game_data["game"]
        start_time = game_data["start_time"]

        # Process the guess
        result = game.guess(guess)
        logging.info(f"Result: {result}")

        if game.is_solved():
            await interaction.response.defer()
            elapsed_time = datetime.now() - start_time
            minutes, seconds = divmod(elapsed_time.total_seconds(), 60)

            # Fetch the word's meaning
            word_meaning = fetch_word_meaning(game.get_secret_word())

            # Update stats only if the word length is 5
            if game.word_length == 5:
                await stats.update_stats(
                    user_id=str(interaction.user.id),
                    server_id=str(interaction.guild.id),
                    games_won=1,
                    guess_number=len(game.history),
                    time_taken=int(elapsed_time.total_seconds()),
                    won=True
                )

            await interaction.followup.send(
                f"{result}\n🎉 Congratulations, you solved it in {int(minutes)} minutes and {int(seconds)} seconds!\n\n"
                f"**Word Meaning:** {word_meaning}"
            )
            del games[interaction.user.id]
        elif game.remaining_guesses == 0:
            # Fetch the word's meaning
            await interaction.response.defer()
            word_meaning = fetch_word_meaning(game.get_secret_word())

            # Update stats only if the word length is 5
            if game.word_length == 5:
                await stats.update_stats(
                    user_id=str(interaction.user.id),
                    server_id=str(interaction.guild.id),
                    won=False
                )

            await interaction.followup.send(
                f"{result}\n😢 Better luck next time! The word was **{game.get_secret_word()}**.\n\n"
                f"**Word Meaning:** {word_meaning}"
            )
            del games[interaction.user.id]
        elif game.is_error():
            logging.info(f"Error in the chat: {result}")
            await interaction.response.send_message(result, ephemeral=True)
            game.reset_errors()
        else:
            await interaction.response.send_message(result)
    except Exception as e:
        logging.error(f"Error in /guessword: {e}")
        await interaction.response.send_message("An error occurred while processing your guess. Please try again later.")

# Command: View Statistics
@bot.tree.command(name="wordleuserstats", description="View your Wordle statistics.")
async def view_stats(interaction: discord.Interaction):
    # Fetch stats for the user in the current server
    stats_data = await stats.fetch_stats(
        user_id=str(interaction.user.id),
        server_id=str(interaction.guild.id)
    )
    rankings = await stats.fetch_server_rankings(
        server_id=str(interaction.guild.id),
        user_id=str(interaction.user.id)
    )
    guess_distribution = stats_data["guess_distribution"]

    await interaction.response.defer()

    # Calculate additional statistics
    games_played = stats_data["games_played"]
    games_won = stats_data["games_won"]
    win_percentage = (games_won / games_played * 100) if games_played > 0 else 0
    current_streak = stats_data.get("current_streak", 0)
    max_streak = stats_data.get("max_streak", 0)

    # Rankings
    win_rank = rankings["win_rank"]
    fastest_rank = rankings["fastest_rank"]
    average_rank = rankings["average_rank"]

    # Create the embed
    embed = discord.Embed(
        title=f"{interaction.user.name}'s Wordle Statistics",
        color=discord.Color.blue()
    )

    # Add statistics to the embed
    embed.add_field(name="Played", value=str(games_played), inline=True)
    embed.add_field(name="Won", value=str(games_won), inline=True)
    embed.add_field(name="Win %", value=f"{win_percentage:.0f}%", inline=True)
    embed.add_field(name="Current Win Streak", value=str(current_streak), inline=True)
    embed.add_field(name="Max Win Streak", value=str(max_streak), inline=True)

    # Add rankings to the embed
    embed.add_field(name="Win Rank", value=f"#{win_rank}" if win_rank else "N/A", inline=True)
    embed.add_field(name="Quickest Solve Rank", value=f"#{fastest_rank}" if fastest_rank else "N/A", inline=True)
    embed.add_field(name="Avg Time Rank", value=f"#{average_rank}" if average_rank else "N/A", inline=True)

    # Add guess distribution to the embed
    if guess_distribution:
        guess_dist_text = "\n".join(
            f"{guess} : {count}" for guess, count in sorted(guess_distribution.items(), key=lambda x: int(x[0]))
        )
        embed.add_field(name="Guess Distribution", value=guess_dist_text, inline=False)
    else:
        embed.add_field(name="Guess Distribution", value="No data available", inline=False)

    # Send the embed
    await interaction.followup.send(embed=embed)

# Command: View Leaderboard
@bot.tree.command(name="wordleleaderboard", description="View the Wordle leaderboard for this server.")
@app_commands.describe(category="Choose a leaderboard category")
@app_commands.choices(
    category=[
        app_commands.Choice(name="Top Win Percentage", value="win_percentage"),
        app_commands.Choice(name="Quickest User", value="fastest_time"),
        app_commands.Choice(name="Avg Time", value="average_time"),
        app_commands.Choice(name="Winning Streak", value="max_streak"),
        app_commands.Choice(name="Fastest time", value="fastest_solve"),  # New category
    ]
)
async def wordleleaderboard(interaction: discord.Interaction, category: app_commands.Choice[str]):
    try:
        await interaction.response.defer()

        # Map category names to display names
        category_display = {
            "win_percentage": "Top Win Percentage",
            "fastest_time": "Quickest User",
            "average_time": "Avg Time",
            "max_streak": "Winning Streak",
            "fastest_solve": "Fastest time"  # New category
        }

        if category.value == "fastest_solve":
            # Fetch top 10 fastest solves from the new table
            leaderboard = await stats.fetch_fastest_solves(
                server_id=str(interaction.guild.id)
            )
        else:
            # Fetch leaderboard data for other categories
            leaderboard = await stats.fetch_leaderboard(
                server_id=str(interaction.guild.id),
                category=category.value
            )

        # Create the embed
        embed = discord.Embed(
            title=f"Wordle Leaderboard - {category_display[category.value]}",
            color=discord.Color.gold()
        )

        if leaderboard:
            leaderboard_text = ""
            for rank, entry in enumerate(leaderboard, start=1):
                user_id = entry["user_id"]  # Extract the user_id
                value = entry["value"] if "value" in entry else entry["solve_time"]  # Extract value or solve_time

                try:
                    # Fetch the user's name
                    user = await bot.fetch_user(user_id)
                    username = user.name if user else "Unknown User"
                except discord.NotFound:
                    username = "Unknown User"
                except Exception as e:
                    username = "Unknown User"

                # Format the value based on the category
                if category.value == "win_percentage":
                    value = f"{value * 100:.2f}%"  # Convert to percentage
                elif category.value in ["fastest_time", "average_time", "fastest_solve"]:
                    value = f"{value:.2f} seconds"  # Format time

                # Add the rank, username, and value in the same row
                leaderboard_text += f"**#{rank}**: {username} - {value}\n"

            embed.description = leaderboard_text
        else:
            embed.description = "No data available for this category."

        # Send the embed
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logging.error(f"Error in /wordleleaderboard: {e}")
        await interaction.followup.send("An error occurred while fetching the leaderboard. Please try again later.")

# Command: Help
@bot.tree.command(name="helpwordle", description="Get help on how to play Wordle.")
async def help_wordle(interaction: discord.Interaction):
    help_text = (
        "**How to Play Wordle on Discord** 🧠\n\n"
        "🎯 The goal is to guess a secret word within a limited number of tries.\n\n"
        "**Commands:**\n"
        "`/startwordle [length]` – Starts a new game. You can specify the word length (default is 5).\n"
        "`/guessword yourword` – Submit a guess for the current game.\n"
        "`/wordleuserstats` – View your Wordle statistics, including games played, win percentage, and streaks.\n"
        "`/wordleleaderboard [category]` – View the top players in the server for a specific category.\n"
        "`/helpwordle` – Shows this help message.\n\n"
        "**Leaderboard Categories:**\n"
        "1. `Top Win Percentage` – Players with the highest win percentage.\n"
        "2. `Fastest Time` – Players with the fastest solved games.\n"
        "3. `Fastest Average Time` – Players with the fastest average solve time.\n"
        "4. `Biggest Winning Streak` – Players with the longest winning streak.\n\n"
        "**Rules:**\n"
        "🟩 = Correct letter in the correct place\n"
        "🟨 = Correct letter, wrong place\n"
        "⬛ = Letter not in the word\n\n"
        "**How to Win:**\n"
        "✅ You win by guessing the word before running out of guesses!\n"
        "⛔ You lose if you run out of guesses.\n\n"
        "_Example:_\n"
        "`guess: GRAPE`\n"
        "`result: 🟨⬛⬛🟩🟩`\n\n"
        "**Tips:**\n"
        "- Use `/wordleleaderboard` to see how you rank against other players in the server.\n"
        "- Focus on common vowels and consonants to narrow down the word quickly.\n"
        "- Keep track of your guesses to avoid repeating letters."
    )
    await interaction.response.send_message(help_text)



    

# Keep the bot alive and run it
keep_alive()
bot.run(TOKEN)
