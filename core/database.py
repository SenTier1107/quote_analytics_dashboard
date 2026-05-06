import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "quotes.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            author TEXT NOT NULL,
            word_count INTEGER,
            char_count INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS quote_tags (
            quote_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY (quote_id, tag),
            FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            quote_id INTEGER PRIMARY KEY,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS authors (
            name TEXT PRIMARY KEY,
            birth_year INTEGER,
            death_year INTEGER,
            century TEXT,
            nationality TEXT,
            occupation TEXT,
            occupation_group TEXT,
            description TEXT,
            summary TEXT,
            image_url TEXT,
            wiki_url TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            quote_id INTEGER PRIMARY KEY,
            vector BLOB NOT NULL,
            model_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE
        )
        """)

        conn.commit()
    finally:
        conn.close()  # 예외 발생해도 반드시 연결 닫힘