import requests
import nltk
from nltk.corpus import words

nltk.download('words')

# Load the words.txt file into memory when the module is imported
try:
    with open("resources/words.txt", "r") as file:
        WORD_LIST = file.read().splitlines()
except FileNotFoundError:
    raise FileNotFoundError("The words.txt file is missing in the resources folder.")

# Function to fetch word meaning
def fetch_word_meaning(word):
    """
    Fetch the meaning of a word using the Free Dictionary API.
    """
    response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
    if response.status_code == 200:
        data = response.json()
        return data[0]["meanings"][0]["definitions"][0]["definition"]
    else:
        return "No definition found."
    
def get_words_list(length):
    """
    Filter the preloaded word list by length.
    """
    # Filter words by length
    filtered_words = [
        word for word in WORD_LIST
        if len(word) == length and word.isalpha() and word.isascii()
    ]
    return filtered_words
