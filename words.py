import requests
import logging
import re
def clean_dict_list():

    #fetching the word list from the dictionary api repo

    response =requests.get("https://raw.githubusercontent.com/meetDeveloper/freeDictionaryAPI/refs/heads/master/meta/wordList/english.txt")
    try:
        with open("resources/dictionary-raw-word-list.txt","wb") as file:
            file.write(response.content)
    except Exception:
        raise Exception("exception raised")
    logging.info("dictionary-raw-word-list.txt file created successfully")
    #remove the undesired words from the list 
    try:
        with open("resources/dictionary-raw-word-list.txt","r", encoding="utf-8") as file :
            DICT_WORD_LIST = file.read().splitlines()
    except FileNotFoundError:
        raise FileNotFoundError("file dictionary-raw-word-list.txt not found")
    pattern = re.compile("^[a-zA-z]{5,13}$")
    
    #create a clean dictionary file
    try:
        with open("resources/dictionary-word-list.txt","w") as file :
            for word in DICT_WORD_LIST :
                if pattern.match(word):
                    file.write(f"{word}\n")
    except Exception :
        raise Exception("exception raised")
    logging.info("dictionary-word-list.txt file created successfully")

clean_dict_list()

# Load the words.txt file into memory when the module is imported
# try:
#     with open("resources/english.txt", "r") as file:
#         WORD_LIST = file.read().splitlines()
# except FileNotFoundError:
#     raise FileNotFoundError("The words.txt file is missing in the resources folder.")

try:
    with open("resources/dictionary-word-list.txt", "r", encoding="utf-8") as file:
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

def clean_dict_list():

    #fetching the word list from the dictionary api repo

    response =requests.get("https://raw.githubusercontent.com/meetDeveloper/freeDictionaryAPI/refs/heads/master/meta/wordList/english.txt")
    try:
        with open("resources/dictionary-raw-word-list.txt","wb") as file:
            file.write(response.content)
    except Exception:
        raise Exception("exception raised")
    logging.info("dictionary-raw-word-list.txt file created successfully")
    #remove the undesired words from the list 
    try:
        with open("resources/dictionary-raw-word-list.txt","r") as file :
            DICT_WORD_LIST = file.read().splitlines()
    except FileNotFoundError:
        raise FileNotFoundError("file dictionary-raw-word-list.txt not found")
    pattern = re.compile("^[a-zA-z]{5,13}$")
    
    #create a clean dictionary file
    try:
        with open("resources/dictionary-word-list.txt","w") as file :
            for word in DICT_WORD_LIST :
                if pattern.match(word):
                    file.write(f"{word}\n")
    except Exception :
        raise Exception("exception raised")
    logging.info("dictionary-word-list.txt file created successfully")