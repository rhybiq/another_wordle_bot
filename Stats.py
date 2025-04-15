import aiosqlite
import json
from supabase_client import supabase

DATABASE_FILE = "user_stats.db"



# Update statistics in the database
async def update_stats(user_id, server_id, games_played=0, games_won=0, guess_number=None, time_taken=None, won=False):
    # Fetch the current stats for the user
    response = supabase.table("user_stats").select("*").eq("user_id", user_id).eq("server_id", server_id).execute()
    row = response.data[0] if response.data else None

    if row:
        current_games_played = row["games_played"]
        current_games_won = row["games_won"]
        current_fastest_time = row["fastest_time"]
        current_average_time = row["average_time"]
        guess_distribution = row["guess_distribution"] or {}
        current_streak = row["current_streak"]
        max_streak = row["max_streak"]
    else:
        current_games_played = 0
        current_games_won = 0
        current_fastest_time = 0
        current_average_time = 0
        guess_distribution = {}
        current_streak = 0
        max_streak = 0

    # Update the guess distribution
    if guess_number is not None:
        guess_distribution[str(guess_number)] = guess_distribution.get(str(guess_number), 0) + 1

    # Update fastest time
    if time_taken is not None:
        if current_fastest_time == 0 or time_taken < current_fastest_time:
            current_fastest_time = time_taken

    # Update average time
    if time_taken is not None:
        total_time = (current_average_time * current_games_won) + time_taken
        current_games_won += games_won  # Increment games won
        current_average_time = total_time / current_games_won if current_games_won > 0 else 0

    # Update games played and streaks
    current_games_played += games_played
    if won:
        current_streak += 1
        max_streak = max(max_streak, current_streak)
    else:
        current_streak = 0

    # Upsert the data into Supabase
    supabase.table("user_stats").upsert({
        "user_id": user_id,
        "server_id": server_id,
        "games_played": current_games_played,
        "games_won": current_games_won,
        "fastest_time": current_fastest_time,
        "average_time": current_average_time,
        "guess_distribution": guess_distribution,
        "current_streak": current_streak,
        "max_streak": max_streak
    }).execute()

        
async def update_games_played(user_id, server_id, games_played=1):
    # Fetch the current stats for the user
    response = supabase.table("user_stats").select("games_played").eq("user_id", user_id).eq("server_id", server_id).execute()
    row = response.data[0] if response.data else None

    if row:
        # Increment the games_played count
        current_games_played = row["games_played"] + games_played
    else:
        # If no record exists, initialize games_played
        current_games_played = games_played

    # Upsert the updated games_played value into Supabase
    supabase.table("user_stats").upsert({
        "user_id": user_id,
        "server_id": server_id,
        "games_played": current_games_played
    }).execute()
        
# Fetch statistics from the database
async def fetch_stats(user_id, server_id):
    response = supabase.table("user_stats").select("*").eq("user_id", user_id).eq("server_id", server_id).execute()
    row = response.data[0] if response.data else None

    if row:
        return {
            "games_played": row["games_played"],
            "games_won": row["games_won"],
            "fastest_time": row["fastest_time"],
            "average_time": row["average_time"],
            "guess_distribution": row["guess_distribution"],
            "current_streak": row["current_streak"],
            "max_streak": row["max_streak"]
        }
    else:
        return {
            "games_played": 0,
            "games_won": 0,
            "fastest_time": 0,
            "average_time": 0.0,
            "guess_distribution": {},
            "current_streak": 0,
            "max_streak": 0
        }

async def fetch_server_rankings(server_id, user_id):
    # Fetch all users' stats in the server from Supabase
    response = supabase.table("user_stats").select(
        "user_id, games_won, games_played, fastest_time, average_time"
    ).eq("server_id", server_id).execute()

    rows = response.data if response.data else []

    # Calculate win percentage and filter out users with no games played
    rankings = [
        {
            "user_id": row["user_id"],
            "win_percentage": row["games_won"] / row["games_played"] if row["games_played"] > 0 else 0,
            "fastest_time": row["fastest_time"] if row["fastest_time"] > 0 else float("inf"),
            "average_time": row["average_time"] if row["average_time"] > 0 else float("inf"),
        }
        for row in rows if row["games_played"] > 0
    ]

    # Sort rankings
    win_percentage_rank = sorted(rankings, key=lambda x: x["win_percentage"], reverse=True)
    fastest_time_rank = sorted(rankings, key=lambda x: x["fastest_time"])
    average_time_rank = sorted(rankings, key=lambda x: x["average_time"])

    # Find the user's rank in each category
    user_win_rank = next((i + 1 for i, row in enumerate(win_percentage_rank) if row["user_id"] == user_id), None)
    user_fastest_rank = next((i + 1 for i, row in enumerate(fastest_time_rank) if row["user_id"] == user_id), None)
    user_average_rank = next((i + 1 for i, row in enumerate(average_time_rank) if row["user_id"] == user_id), None)

    return {
        "win_rank": user_win_rank,
        "fastest_rank": user_fastest_rank,
        "average_rank": user_average_rank
    }

async def fetch_leaderboard(server_id, category):
    # Define the column to sort by based on the category
    if category == "win_percentage":
        sort_column = "games_won / NULLIF(games_played, 0)"  # Avoid division by zero
        order = "desc"
    elif category == "fastest_time":
        sort_column = "fastest_time"
        order = "asc"
    elif category == "average_time":
        sort_column = "average_time"
        order = "asc"
    elif category == "max_streak":
        sort_column = "max_streak"
        order = "desc"
    else:
        return []

    # Fetch leaderboard data from Supabase
    response = supabase.rpc(
        "fetch_leaderboard",  # Replace with a Supabase function if needed
        {
            "server_id": server_id,
            "category": category,
        }
    ).execute()

    return response.data
