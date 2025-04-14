import aiosqlite
import json

DATABASE_FILE = "user_stats.db"


async def init_db():
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id TEXT,
                server_id TEXT,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                fastest_time INTEGER DEFAULT 0,
                average_time REAL DEFAULT 0,
                guess_distribution TEXT DEFAULT '{}',
                current_streak INTEGER DEFAULT 0,
                max_streak INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, server_id)
            )
        """)
        await db.commit()

        # Check and add missing columns
        async with db.execute("PRAGMA table_info(user_stats)") as cursor:
            existing_columns = [row[1] for row in await cursor.fetchall()]

        # Add missing columns
        if "fastest_time" not in existing_columns:
            await db.execute("ALTER TABLE user_stats ADD COLUMN fastest_time INTEGER DEFAULT 0")
        if "average_time" not in existing_columns:
            await db.execute("ALTER TABLE user_stats ADD COLUMN average_time REAL DEFAULT 0")
        if "guess_distribution" not in existing_columns:
            await db.execute("ALTER TABLE user_stats ADD COLUMN guess_distribution TEXT DEFAULT '{}'")

        await db.commit()

# Update statistics in the database
async def update_stats(user_id, server_id, games_played=0, games_won=0, guess_number=None, time_taken=None, won=False):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        # Fetch the current stats for the user
        async with db.execute("""
            SELECT games_played, games_won, fastest_time, average_time, guess_distribution
            FROM user_stats
            WHERE user_id = ? AND server_id = ?
        """, (user_id, server_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                current_games_played = row[0]
                current_games_won = row[1]
                current_fastest_time = row[2]
                current_average_time = row[3]
                guess_distribution = json.loads(row[4]) if row[4] else {}
            else:
                current_games_played = 0
                current_games_won = 0
                current_fastest_time = None
                current_average_time = 0
                guess_distribution = {}

        # Update the guess distribution
        if guess_number is not None:
            guess_distribution[str(guess_number)] = guess_distribution.get(str(guess_number), 0) + 1

        # Update fastest time
        if time_taken is not None:
            if current_fastest_time is None or time_taken < current_fastest_time:
                current_fastest_time = time_taken

        # Update average time
        if time_taken is not None:
            total_time = (current_average_time * current_games_won) + time_taken
            current_games_won += games_won  # Increment games won
            current_average_time = total_time / current_games_won if current_games_won > 0 else 0

        # Update games played and games won
        current_games_played += games_played

        # Fetch current streak and max streak
        async with db.execute("SELECT current_streak, max_streak FROM user_stats WHERE user_id = ? AND server_id = ?", (user_id, server_id)) as cursor:
            row = await cursor.fetchone()
            current_streak = row[0] if row else 0
            max_streak = row[1] if row else 0

        # Update streaks
        if won:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

        # Update the database
        await db.execute("""
            INSERT INTO user_stats (user_id, server_id, games_played, games_won, fastest_time, average_time, guess_distribution, current_streak, max_streak)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, server_id) DO UPDATE SET
                games_played = ?,
                games_won = ?,
                fastest_time = ?,
                average_time = ?,
                guess_distribution = ?,
                current_streak = ?,
                max_streak = ?
        """, (
            user_id, server_id, current_games_played, current_games_won, current_fastest_time, current_average_time, json.dumps(guess_distribution), current_streak, max_streak,
            current_games_played, current_games_won, current_fastest_time, current_average_time, json.dumps(guess_distribution), current_streak, max_streak
        ))
        await db.commit()

        
async def update_games_played(user_id, server_id, games_played=1):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("""
            INSERT INTO user_stats (user_id, server_id, games_played)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, server_id) DO UPDATE SET
                games_played = games_played + ?
        """, (user_id, server_id, games_played, games_played))
        await db.commit()
# Fetch statistics from the database
async def fetch_stats(user_id, server_id):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        async with db.execute("""
            SELECT games_played, games_won, fastest_time, average_time, guess_distribution, current_streak, max_streak
            FROM user_stats
            WHERE user_id = ? AND server_id = ?
        """, (user_id, server_id)) as cursor:
            row = await cursor.fetchone()

    if row:
        return {
            "games_played": row[0],
            "games_won": row[1],
            "fastest_time": row[2],
            "average_time": row[3],
            "guess_distribution": eval(row[4]),  # Convert string back to dictionary
            "current_streak": row[5],
            "max_streak": row[6]
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
    async with aiosqlite.connect(DATABASE_FILE) as db:
        # Fetch all users' stats in the server
        async with db.execute("""
            SELECT user_id, games_won * 1.0 / games_played AS win_percentage, fastest_time, average_time
            FROM user_stats
            WHERE server_id = ? AND games_played > 0
        """, (server_id,)) as cursor:
            rows = await cursor.fetchall()

    # Sort rankings
    win_percentage_rank = sorted(rows, key=lambda x: x[1], reverse=True)
    fastest_time_rank = sorted(rows, key=lambda x: x[2] if x[2] > 0 else float('inf'))
    average_time_rank = sorted(rows, key=lambda x: x[3] if x[3] > 0 else float('inf'))

    # Find the user's rank
    user_win_rank = next((i + 1 for i, row in enumerate(win_percentage_rank) if row[0] == user_id), None)
    user_fastest_rank = next((i + 1 for i, row in enumerate(fastest_time_rank) if row[0] == user_id), None)
    user_average_rank = next((i + 1 for i, row in enumerate(average_time_rank) if row[0] == user_id), None)

    return {
        "win_rank": user_win_rank,
        "fastest_rank": user_fastest_rank,
        "average_rank": user_average_rank
    }
