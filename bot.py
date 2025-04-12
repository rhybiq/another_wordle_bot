# -*- coding: utf-8 -*-
"""
Created on Sat Apr 12 18:10:17 2025

@author: rhybiq
"""
import sys
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from  wordle import WordleGame
from english_words import get_english_words_set  




load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

games = {}  # Keeps track of games per user

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='startwordle')
async def start_wordle(ctx, length: int = 5):
    if length < 5 or length > 10:
        await ctx.send("Please choose a word length between 5 and 10.")
        return

    filtered_words = [word for word in get_english_words_set(['web2'], lower=True) if len(word) == length]
    if not filtered_words:
        await ctx.send(f"No words found with length {length}. Try a different number.")
        return

    games[ctx.author.id] = WordleGame(filtered_words, word_length=length)
    await ctx.send(f"Wordle game started with {length}-letter words! You get {length + 1} guesses. Use `!guess yourword` to make a guess.")

@bot.command(name='guess')
async def _evaluate_guess(ctx, guess: str):
    # Check if the user has an active game
    if ctx.author.id not in games:
        await ctx.send("You don't have an active game. Start one with `/startwordle`.")
        return

    # Get the user's game instance
    game = games[ctx.author.id]

    # Make a guess and get the result
    result = game.guess(guess)

    # Check if the game is solved or over
    if game.is_solved():
        await ctx.send(result)
        await ctx.send("🎉 Congratulations, you solved it!")
        del games[ctx.author.id]  # Remove the game after it's solved
    elif game.remaining_guesses == 0:
        await ctx.send(result)
        await ctx.send("😢 Better luck next time!")
        del games[ctx.author.id]  # Remove the game after it's over
    else:
        await ctx.send(result)

bot.run(TOKEN)
