# -*- coding: utf-8 -*-
"""
Created on Sat Apr 12 18:17:46 2025

@author: rhybiq
"""

import random

WORDS = ['apple', 'grape', 'train', 'plant', 'beach']

class WordleGame:
    def __init__(self, word_list, word_length=5):
        self.word_length = word_length
        self.allowed_guesses = word_length + 1
        self.word_list = [word for word in word_list if len(word) == word_length]
        self.secret_word = random.choice(self.word_list)
        self.remaining_guesses = self.allowed_guesses
        self.history = []

    def guess(self, word):
        word = word.lower()
        if len(word) != self.word_length:
            return f"Guess must be {self.word_length} letters long."

        if word not in self.word_list:
            return "Not a valid word."

        self.remaining_guesses -= 1
        result = self._evaluate_guess(word)
        self.history.append((word, result))

        if word == self.secret_word:
            return f"✅ Correct! The word was **{self.secret_word}**.\n\nYour guesses:\n" + self._format_history()

        if self.remaining_guesses == 0:
            return f"❌ Out of guesses! The word was **{self.secret_word}**.\n\nYour guesses:\n" + self._format_history()

        return f"{result} ({self.remaining_guesses} guesses left)\n\nYour guesses so far:\n" + self._format_history()

    def _format_history(self):
        # Format the history with a monospaced code block for proper alignment
        formatted_history = "\n".join([f"{guess.ljust(self.word_length)}: {result}" for guess, result in self.history])
        return f"```\n{formatted_history}\n```"

    def is_solved(self):
        return self.history and self.history[-1][0] == self.secret_word

    def _evaluate_guess(self, guess):
        result = []
        secret_temp = list(self.secret_word)
        guess = list(guess)

        emoji_result = [''] * len(guess)
        used = [False] * len(secret_temp)

        # First pass: 🟩
        for i in range(len(guess)):
            if guess[i] == secret_temp[i]:
                emoji_result[i] = "🟩"
                used[i] = True
            else:
                emoji_result[i] = None

        # Second pass: 🟨 or ⬛
        for i in range(len(guess)):
            if emoji_result[i] is not None:
                continue
            if guess[i] in secret_temp:
                found = False
                for j in range(len(secret_temp)):
                    if guess[i] == secret_temp[j] and not used[j]:
                        emoji_result[i] = "🟨"
                        used[j] = True
                        found = True
                        break
                if not found:
                    emoji_result[i] = "⬛"
            else:
                emoji_result[i] = "⬛"
        
        return "".join(emoji_result)
