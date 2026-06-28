import sqlite3
import os
import json
import secrets

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "ctf.db")

STARTING_HEARTS = 3

LEVEL3_WORDLIST = [
    "123456", "password", "12345678", "qwerty", "123456789", "letmein",
    "football", "iloveyou", "admin123", "welcome1", "monkey123", "dragon99",
    "sunshine1", "princess1", "baseball1", "trustno1", "master123", "hello123",
    "freedom1", "whatever1", "shadow99", "michael1", "jennifer1", "computer1",
    "summer2023", "winter2024", "spring2024", "autumn2023", "summer2024",
    "password1", "qwerty123", "abc12345", "letmein1", "iloveyou1", "football1",
    "superman1", "batman123", "starwars1", "pokemon99", "minecraft1",
    "soccer123", "basketball", "tennis123", "guitar123", "musiclover",
    "happy2024", "lucky2023", "newyork12", "london123", "paris2024",
]

# Each level maps to one OWASP Top 10 (2025) category.
# "slug" is used in URLs, e.g. /level/injection
LEVELS = [
    {
        "id": 1,
        "slug": "injection",
        "name": "SQL Injection",
        "owasp": "A05:2025 - Injection",
        "description": "Bypass a login form that builds SQL queries unsafely.",
         "flag": "FLAG{sql_injection_master}",
    },
    {
        "id": 2,
        "slug": "access-control",
        "name": "Broken Access Control",
        "owasp": "A01:2025 - Broken Access Control",
        "description": "View another user's private note without permission.",
        "flag": "FLAG{idor_no_ownership_check}",
    },
    {
        "id": 3,
        "slug": "auth-failures",
        "name": "Authentication Failures",
        "owasp": "A07:2025 - Authentication Failures",
        "description": "Break a weak login that has no rate limiting.",
        "flag": "FLAG{no_rate_limit_brute_force}",
    },
    {
        "id": 4,
        "slug": "misconfiguration",
        "name": "Security Misconfiguration",
        "owasp": "A02:2025 - Security Misconfiguration",
        "description": "Find a debug endpoint that was left exposed.",
        "flag": "FLAG{robots_txt_leaked_debug_endpoint}",
    },
    {
        "id": 5,
        "slug": "exceptional-conditions",
        "name": "Mishandling of Exceptional Conditions",
        "owasp": "A10:2025 - Mishandling of Exceptional Conditions",
        "description": "Trigger an error that skips a security check.",
        "flag": "FLAG{exception_swallowed_the_access_check}",
    },
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_token TEXT UNIQUE NOT NULL,
            hearts INTEGER NOT NULL DEFAULT 3,
            difficulty TEXT NOT NULL DEFAULT 'beginner',
            score INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            level_id INTEGER NOT NULL,
            solved INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0,
            solved_at TEXT,
            FOREIGN KEY (player_id) REFERENCES players(id),
            UNIQUE(player_id, level_id)
        );

        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            level_id INTEGER,
            event_type TEXT NOT NULL,
            detail TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS level1_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

       CREATE TABLE IF NOT EXISTS level2_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS level3_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS level3_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS level5_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            active INTEGER NOT NULL
        );
        """
    )
    try:
        conn.execute(
            "INSERT INTO level1_users (username, password) VALUES ('admin', 'sup3rSecretPW!')"
        )
    except sqlite3.IntegrityError:
        pass

    existing = conn.execute("SELECT COUNT(*) as c FROM level2_notes").fetchone()
    if existing["c"] == 0:
        decoy_owners = ["bob", "carol", "dave", "erin", "frank", "grace"]
        decoy_titles = [
            "Lunch plans", "Reminder", "Shopping list", "Workout log",
            "Book recommendations", "Trip ideas", "Recipe", "Random thoughts",
            "Password hint (not real)", "Draft email", "Todo", "Quote I liked",
        ]
        decoy_content = [
            "Nothing important here.",
            "Just a placeholder note.",
            "Need to follow up on this later.",
            "Doesn't matter, just testing the notes feature.",
        ]

        import random
        random.seed(42)  # deterministic so the puzzle is consistent every run

        # Insert a batch of decoy notes BEFORE the player's note, so the
        # player's own note_id won't be 1 -- more realistic.
        for _ in range(7):
            conn.execute(
                "INSERT INTO level2_notes (owner, title, content) VALUES (?, ?, ?)",
                (random.choice(decoy_owners), random.choice(decoy_titles), random.choice(decoy_content)),
            )

        your_note_id = conn.execute(
            "INSERT INTO level2_notes (owner, title, content) VALUES (?, ?, ?)",
            ("you", "Grocery list",
             "milk, eggs, bread (reminder: I saved Alice's backup note at id 0000 once, just in case)"),
        ).lastrowid

        # More decoys after your note
        for _ in range(9):
            conn.execute(
                "INSERT INTO level2_notes (owner, title, content) VALUES (?, ?, ?)",
                (random.choice(decoy_owners), random.choice(decoy_titles), random.choice(decoy_content)),
            )

        alice_flag_id = conn.execute(
            "INSERT INTO level2_notes (owner, title, content) VALUES (?, ?, ?)",
            ("alice", "Private flag note", f"You found Alice's private note! {LEVELS[1]['flag']}"),
        ).lastrowid

        # Patch the hint in "your" note to point at Alice's real note id
        conn.execute(
            "UPDATE level2_notes SET content = ? WHERE id = ?",
            (f"milk, eggs, bread (reminder: I saved Alice's backup note at id {alice_flag_id} once, just in case)",
             your_note_id),
        )

       # A few more decoys after, so the flag isn't suspiciously near the end
        for _ in range(6):
            conn.execute(
                "INSERT INTO level2_notes (owner, title, content) VALUES (?, ?, ?)",
                (random.choice(decoy_owners), random.choice(decoy_titles), random.choice(decoy_content)),
            )

    try:
        conn.execute(
            "INSERT INTO level3_users (username, password) VALUES ('jsmith', 'summer2024')"
        )
    except sqlite3.IntegrityError:
        pass

    existing_members = conn.execute("SELECT COUNT(*) as c FROM level5_members").fetchone()
    if existing_members["c"] == 0:
        conn.execute(
            "INSERT INTO level5_members (name, active) VALUES (?, ?)", ("alice", 1)
        )
        conn.execute(
            "INSERT INTO level5_members (name, active) VALUES (?, ?)", ("bob", 0)
        )

    conn.commit()
    conn.close()
    

def create_player(difficulty="beginner"):
    token = secrets.token_hex(16)
    conn = get_db()
    conn.execute(
        "INSERT INTO players (session_token, hearts, difficulty) VALUES (?, ?, ?)",
        (token, STARTING_HEARTS, difficulty),
    )
    conn.commit()
    player = conn.execute(
        "SELECT * FROM players WHERE session_token = ?", (token,)
    ).fetchone()
    conn.close()
    return dict(player)

def get_player(token):
    conn = get_db()
    player = conn.execute(
        "SELECT * FROM players WHERE session_token = ?", (token,)
    ).fetchone()
    conn.close()
    return dict(player) if player else None


def get_progress(player_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM progress WHERE player_id = ?", (player_id,)
    ).fetchall()
    conn.close()
    return {row["level_id"]: dict(row) for row in rows}

def log_event(player_id, level_id, event_type, detail=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO event_log (player_id, level_id, event_type, detail) VALUES (?, ?, ?, ?)",
        (player_id, level_id, event_type, detail),
    )
    conn.commit()
    conn.close()


def lose_heart(player_id, level_id, reason=""):
    conn = get_db()
    conn.execute(
        "UPDATE players SET hearts = hearts - 1 WHERE id = ?", (player_id,)
    )
    conn.commit()
    player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    conn.close()
    log_event(player_id, level_id, "heart_lost", reason)
    return dict(player)


def record_attempt(player_id, level_id):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO progress (player_id, level_id, attempts)
        VALUES (?, ?, 1)
        ON CONFLICT(player_id, level_id)
        DO UPDATE SET attempts = attempts + 1
        """,
        (player_id, level_id),
    )
    conn.commit()
    conn.close()


def solve_level(player_id, level_id, points=100):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO progress (player_id, level_id, solved, solved_at)
        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(player_id, level_id)
        DO UPDATE SET solved = 1, solved_at = CURRENT_TIMESTAMP
        """,
        (player_id, level_id),
    )
    conn.execute(
        "UPDATE players SET score = score + ? WHERE id = ?", (points, player_id)
    )
    conn.commit()
    conn.close()
    log_event(player_id, level_id, "level_solved")

PLAYER_COOKIE_NAME = "ctf_player_token"


def get_or_create_player(request, response_setter, difficulty="beginner"):
    """
    Looks up the player based on their cookie. If no valid player exists yet,
    creates one and arranges for the cookie to be set on the response.

    request: the Flask request object
    response_setter: a function that takes (cookie_name, cookie_value) and
                      sets it on whatever response we end up sending
    """
    token = request.cookies.get(PLAYER_COOKIE_NAME)
    player = get_player(token) if token else None

    if player is None:
        player = create_player(difficulty=difficulty)
        response_setter(PLAYER_COOKIE_NAME, player["session_token"])

    return player

def level1_vulnerable_login(username, password):
    """
    INTENTIONALLY VULNERABLE -- raw string interpolation into SQL.
    This is the bug the player is meant to exploit in Level 1.
    """
    conn = get_db()
    query = f"SELECT * FROM level1_users WHERE username = '{username}' AND password = '{password}'"
    try:
        cur = conn.execute(query)
        user = cur.fetchone()
        error = None
    except sqlite3.OperationalError as e:
        user = None
        error = str(e)
    conn.close()
    return (dict(user) if user else None), error

def level2_get_note(note_id):
    """
    INTENTIONALLY VULNERABLE -- fetches a note by ID with no check on
    whether the requester actually owns it. This is the bug: any valid
    note_id returns its content, regardless of who's asking.
    """
    conn = get_db()
    note = conn.execute(
        "SELECT * FROM level2_notes WHERE id = ?", (note_id,)
    ).fetchone()
    conn.close()
    return dict(note) if note else None

def level3_login(username, password, player_id=None):
    """
    Safe from SQL injection (parameterized query) -- the vulnerability
    here is purely the ABSENCE of rate limiting, not the query itself.
    """
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM level3_users WHERE username = ? AND password = ?",
        (username, password),
    ).fetchone()

    if player_id is not None:
        conn.execute(
            "INSERT INTO level3_attempts (player_id, username, password) VALUES (?, ?, ?)",
            (player_id, username, password),
        )
        conn.commit()

    conn.close()
    return dict(user) if user else None


def level3_attempt_count(player_id):
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM level3_attempts WHERE player_id = ?", (player_id,)
    ).fetchone()
    conn.close()
    return row["c"]


def level3_recent_attempt_rate(player_id, seconds=5):
    """
    Counts how many attempts this player made in the last N seconds.
    This is the actual 'detection' logic -- a real system would flag
    a high count in a short window as a brute-force pattern.
    """
    conn = get_db()
    row = conn.execute(
        f"""
        SELECT COUNT(*) as c FROM level3_attempts
        WHERE player_id = ?
        AND timestamp >= datetime('now', '-{seconds} seconds')
        """,
        (player_id,),
    ).fetchone()
    conn.close()
    return row["c"]

def level5_check_membership(membership_id):
    """
    INTENTIONALLY VULNERABLE -- this function was "defensively" written
    so that if anything goes wrong while checking membership, the user
    is let through rather than the app crashing. That defensive instinct
    accidentally turned an access check into a bypass: any error at all
    (not just a clean 'not found') results in access_granted = True.
    """
    conn = get_db()
    try:
        member_id_int = int(membership_id)
        row = conn.execute(
            "SELECT * FROM level5_members WHERE id = ?", (member_id_int,)
        ).fetchone()
        access_granted = row is not None and row["active"] == 1
    except Exception:
        # "Don't break the page if something's weird with the input"
        # -- this is the bug. Should be: access_granted = False
        access_granted = True
    finally:
        conn.close()

    return access_granted