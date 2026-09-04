import sqlite3

DB_FILE = "assistant.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            time_spec TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_reminder(task: str, time_spec: str = "today") -> str:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO reminders (task, time_spec) VALUES (?, ?)", (task.strip(), time_spec.strip()))
        conn.commit()
        conn.close()
        return f"Done! Saved reminder: '{task}' scheduled for {time_spec}."
    except Exception as e:
        return f"Database error: {str(e)}"

def list_reminders() -> str:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT task, time_spec FROM reminders ORDER BY id DESC LIMIT 5")
        rows = c.fetchall()
        conn.close()
        if not rows:
            return "You have no active reminders right now."
        return "; ".join([f"{r[0]} ({r[1]})" for r in rows])
    except Exception as e:
        return f"Database error: {str(e)}"

def save_note(title: str, content: str) -> str:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO notes (title, content) VALUES (?, ?)", (title.strip(), content.strip()))
        conn.commit()
        conn.close()
        return f"Stored note under '{title}': '{content}'."
    except Exception as e:
        return f"Database error: {str(e)}"

def search_notes(query: str) -> str:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT title, content FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY id DESC LIMIT 3", (f"%{query}%", f"%{query}%"))
        rows = c.fetchall()
        conn.close()
        if not rows:
            return f"No database records found matching '{query}'."
        return "; ".join([f"{r[0]}: {r[1]}" for r in rows])
    except Exception as e:
        return f"Database error: {str(e)}"

init_db()
