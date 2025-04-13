# -*- coding: utf-8 -*-
"""
Created on Sat Apr 12 18:10:17 2025

@author: rhybiq
"""
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
from wordle import WordleGame
from wordfreq import top_n_list
from datetime import datetime
from keep_alive import keep_alive
import asyncio
import logging

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

games = {}  # Keeps track of games per user

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()  # Sync slash commands with Discord
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="startwordle", description="Start a Wordle game with a specified word length.")
async def start_wordle(interaction: discord.Interaction, length: int = 5):
    if length < 5 or length > 10:
        await interaction.response.send_message("Please choose a word length between 5 and 10.")
        return

    filtered_words = [
        word for word in top_n_list('en', 500000) 
        if len(word) == length and word.isalpha() and word.isascii()
    ]
    if not filtered_words:
        await interaction.response.send_message(f"No words found with length {length}. Try a different number.")
        return

    games[interaction.user.id] = {
        "game": WordleGame(filtered_words, word_length=length),
        "start_time": datetime.now()  # Record the start time
    }
    await interaction.response.send_message(
        f"Wordle game started with {length}-letter words! You get {length + 1} guesses. Use `/guessword yourword` to make a guess."
    )
    asyncio.create_task(game_timeout(interaction.user.id, interaction))

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
        await interaction.response.send_message(
            f"{result}\n🎉 Congratulations, you solved it in {int(minutes)} minutes and {int(seconds)} seconds!"
        )
        del games[interaction.user.id]
    elif game.remaining_guesses == 0:
        await interaction.response.send_message(f"{result}\n😢 Better luck next time!")
        del games[interaction.user.id]
    elif game.is_error():
        logging.info(f"Error in the chat: {result}")
        await interaction.response.send_message(result,ephemeral=True)
        game.reset_errors()
    else:
        await interaction.response.send_message(result)

@bot.tree.command(name="helpwordle", description="Get help on how to play Wordle.")
async def help_wordle(interaction: discord.Interaction):
    help_text = (
        "**How to Play Wordle on Discord** 🧠\n\n"
        "🎯 The goal is to guess a secret word within a limited number of tries.\n\n"
        "**Commands:**\n"
        "`/startwordle [length]` – Starts a new game. You can specify word length (default is 5).\n"
        "`/guessword yourword` – Submit a guess.\n"
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

async def game_timeout(user_id, interaction):
    await asyncio.sleep(9 * 60)  # Wait for 9 minutes
    if user_id in games:  # Check if the game is still active
        #await interaction.followup.send(f"{interaction.user.mention}, 1 minute left to finish your Wordle game!")
        await interaction.send_message(f"{interaction.user.mention}, 1 minute left to finish your Wordle game!")
    await asyncio.sleep(60)  # Wait for the final minute
    if user_id in games:  # Check again if the game is still active
        del games[user_id]  # Remove the game
        await interaction.followup.send(f"{interaction.user.mention}, time's up! Your Wordle game has ended.")

keep_alive()
bot.run(TOKEN)
