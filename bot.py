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

# Setup logging and environment
logging.basicConfig(level=logging.INFO)
nltk.download('words')
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)
games = {}  # Keeps track of active games per user

# Initialize the database
@bot.event
async def on_ready():
    await stats.init_db()  # Initialize the database
    print("Database initialized.")
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
    if length < 5 or length > 13:
        await interaction.response.send_message("Please choose a word length between 5 and 13.")
        return

    filtered_words = [
        word for word in words.words('en')
        if len(word) == length and word.isalpha() and word.isascii()
    ]
    if not filtered_words:
        await interaction.response.send_message(f"No words found with length {length}. Try a different number.")
        return

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

    await interaction.response.send_message(
        f"Wordle game started with {length}-letter words! You get {length + 1} guesses. Use `/guessword yourword` to make a guess."
    )

# Command: Make a Guess
@bot.tree.command(name="guessword", description="Make a guess in your Wordle game.")
async def guess_word(interaction: discord.Interaction, guess: str):
    if interaction.user.id not in games:
        await interaction.response.send_message("You don't have an active game. Start one with `/startwordle`.", ephemeral=True)
        return

    game_data = games[interaction.user.id]
    game = game_data["game"]
    start_time = game_data["start_time"]

    result = game.guess(guess)
    logging.info(f"Result: {result}")

    if game.is_solved():
        elapsed_time = datetime.now() - start_time
        minutes, seconds = divmod(elapsed_time.total_seconds(), 60)

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

        await interaction.response.send_message(
            f"{result}\n🎉 Congratulations, you solved it in {int(minutes)} minutes and {int(seconds)} seconds!"
        )
        del games[interaction.user.id]
    elif game.remaining_guesses == 0:
        # Update stats only if the word length is 5
        if game.word_length == 5:
            await stats.update_stats(
                user_id=str(interaction.user.id),
                server_id=str(interaction.guild.id),
                won=False
            )

        await interaction.response.send_message(f"{result}\n😢 Better luck next time!")
        del games[interaction.user.id]
    elif game.is_error():
        logging.info(f"Error in the chat: {result}")
        await interaction.response.send_message(result, ephemeral=True)
        game.reset_errors()
    else:
        await interaction.response.send_message(result)

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
    embed.add_field(name="Fastest Rank", value=f"#{fastest_rank}" if fastest_rank else "N/A", inline=True)
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
    await interaction.response.send_message(embed=embed)

# Command: View Leaderboard
@bot.tree.command(name="wordleleaderboard", description="View the Wordle leaderboard for this server.")
async def wordle_leaderboard(interaction: discord.Interaction, category: str):
    # Validate the category
    valid_categories = ["win_percentage", "fastest_time", "average_time", "max_streak"]
    if category not in valid_categories:
        await interaction.response.send_message(
            f"Invalid category! Please choose from: {', '.join(valid_categories)}.",
            ephemeral=True
        )
        return

    # Fetch leaderboard data
    leaderboard = await stats.fetch_leaderboard(
        server_id=str(interaction.guild.id),
        category=category
    )

    # Map category names to display names
    category_display = {
        "win_percentage": "Top Win Percentage",
        "fastest_time": "Fastest Time",
        "average_time": "Fastest Average Time",
        "max_streak": "Biggest Max Streak"
    }

    # Create the embed
    embed = discord.Embed(
        title=f"Wordle Leaderboard - {category_display[category]}",
        color=discord.Color.gold()
    )

    if leaderboard:
        for rank, (user_id, value) in enumerate(leaderboard, start=1):
            user = await bot.fetch_user(user_id)  # Fetch the user's name
            if category == "win_percentage":
                value = f"{value * 100:.2f}%"  # Convert to percentage
            elif category in ["fastest_time", "average_time"]:
                value = f"{value:.2f} seconds"  # Format time
            embed.add_field(
                name=f"#{rank}: {user.name if user else 'Unknown User'}",
                value=f"{value}",
                inline=False
            )
    else:
        embed.description = "No data available for this category."

    # Send the embed
    await interaction.response.send_message(embed=embed)

# Command: Help
@bot.tree.command(name="helpwordle", description="Get help on how to play Wordle.")
async def help_wordle(interaction: discord.Interaction):
    help_text = (
        "**How to Play Wordle on Discord** 🧠\n\n"
        "🎯 The goal is to guess a secret word within a limited number of tries.\n\n"
        "**Commands:**\n"
        "`/startwordle [length]` – Starts a new game. You can specify word length (default is 5).\n"
        "`/guessword yourword` – Submit a guess.\n"
        "`/stats` – View your Wordle statistics.\n"
        "`/helpwordle` – Shows this help message.\n\n"
        "**Rules:**\n"
        "🟩 = Correct letter in correct place\n"
        "🟨 = Correct letter, wrong place\n"
        "⬛ = Letter not in the word\n\n"
        "✅ You win by guessing the word before running out of guesses!\n"
        "⛔ You lose if you run out of guesses.\n\n"
        "_Example:_\n"
        "`guess: GRAPE`\n"
        "`result: 🟨⬛⬛🟩🟩`"
    )
    await interaction.response.send_message(help_text)



    

# Keep the bot alive and run it
keep_alive()
bot.run(TOKEN)
