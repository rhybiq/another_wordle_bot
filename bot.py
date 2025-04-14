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
        synced = await bot.tree.sync()  # Sync slash commands with Discord
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

        # Update stats for a win
        await stats.update_stats(
            user_id=str(interaction.user.id),
            server_id=str(interaction.guild.id),  # Pass the server_id here
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
        # Update stats for a loss
        await stats.update_stats(
            user_id=str(interaction.user.id),
            server_id=str(interaction.guild.id),  # Pass the server_id here
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
@bot.tree.command(name="stats", description="View your Wordle statistics.")
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

    # Format guess distribution
    guesses = list(map(int, guess_distribution.keys()))
    counts = list(guess_distribution.values())

    # Create a figure with two subplots
    fig, axes = plt.subplots(2, 1, figsize=(10, 10), gridspec_kw={'height_ratios': [1, 2]})
    fig.subplots_adjust(hspace=0.1)  # Add space between the plots

    # Plot 1: Statistics
    axes[0].axis('off')  # Turn off the axes for the statistics section
    axes[0].text(0.5, 0.9, f"{str(interaction.user.name)}'s STATISTICS", fontsize=20, ha='center', weight='bold')

    # Align statistics horizontally
    stats_x = [0.15, 0.35, 0.55, 0.75]  # Horizontal positions for the stats
    stats_labels = ["Played", "Win %", "Cur. Streak", "Max Streak"]
    stats_values = [games_played, f"{win_percentage:.0f}%", current_streak, max_streak]

    # Adjust vertical positions to avoid overlapping
    value_y = 0.7  # Vertical position for values
    label_y = 0.6  # Vertical position for labels

    for x, label, value in zip(stats_x, stats_labels, stats_values):
        axes[0].text(x, value_y, str(value), fontsize=24, ha='center', weight='bold')  # Values
        axes[0].text(x, label_y, label, fontsize=18, ha='center')  # Labels

    # Add rankings
    rankings_x = [0.25, 0.5, 0.75]  # Horizontal positions for rankings
    rankings_labels = ["Win Rank", "Fastest Rank", "Avg Time Rank"]
    rankings_values = [win_rank, fastest_rank, average_rank]

    # Adjust vertical positions for rankings
    rank_value_y = 0.4  # Vertical position for ranking values
    rank_label_y = 0.3  # Vertical position for ranking labels

    for x, label, value in zip(rankings_x, rankings_labels, rankings_values):
        axes[0].text(x, rank_value_y, f"#{value}" if value else "N/A", fontsize=24, ha='center', weight='bold')  # Values
        axes[0].text(x, rank_label_y, label, fontsize=18, ha='center')  # Labels

    # Plot 2: Guess Distribution
    axes[1].set_title("GUESS DISTRIBUTION", fontsize=16, weight='bold', pad=10)  # Reduce padding for a more compact layout
    if guesses and counts:
        max_count = max(counts)
        bar_height = 0.6  # Increase bar height to reduce the gap between bars
        bar_positions = [i * 0.8 for i in range(len(guesses))]  # Reduce spacing between bars

        # Draw bars and add labels
        for i, (guess, count) in enumerate(zip(guesses, counts)):
            bar_color = 'green' if count == max_count else 'gray'
            axes[1].barh(bar_positions[i], count, color=bar_color, edgecolor='black', height=bar_height)
            axes[1].text(count + 0.5, bar_positions[i], str(count), va='center', fontsize=8)  # Add count labels closer to the bars
            axes[1].text(-1.5, bar_positions[i], str(guess), va='center', fontsize=8)  # Add guess labels closer to the bars

        axes[1].invert_yaxis()  # Invert y-axis to match the example
        axes[1].set_xlim(0, max_count + 5)  # Adjust x-axis limits for better spacing
        axes[1].set_xticks([])  # Remove x-axis ticks for a cleaner look
        axes[1].set_yticks([])  # Remove y-axis ticks for compactness
        axes[1].grid(axis='x', linestyle='--', alpha=0.5)  # Keep light grid lines for readability
        axes[1].axis('off') 
    else:
        axes[1].text(0.5, 0.5, "No guess distribution data available.", fontsize=10, ha='center')
        axes[1].axis('off')  # Turn off all axes for the empty state

    # Save the image to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close()

    # Prepare the file for Discord
    file = discord.File(buf, filename="wordle_stats.png")

    # Send the response
    await interaction.response.send_message(
        content=f"Here are your Wordle statistics for this server, {interaction.user.name}!",
        file=file
    )

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
