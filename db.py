import sqlite3

def init_db():
    conn = sqlite3.connect("assistant.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            time TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_reminder(task: str, time: str) -> str:
    conn = sqlite3.connect("assistant.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reminders (task, time) VALUES (?, ?)", (task, time))
    conn.commit()
    conn.close()
    return f"Successfully saved reminder: '{task}' at {time}."

def list_reminders() -> str:
    conn = sqlite3.connect("assistant.db")
    cursor = conn.cursor()
    cursor.execute("SELECT task, time FROM reminders")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "No reminders found."
    return "; ".join([f"{r[0]} at {r[1]}" for r in rows])

if __name__ == "__main__":
    init_db()
