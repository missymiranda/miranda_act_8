import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("students.db")

def initialize_database():
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                name TEXT NOT NULL,
                program TEXT NOT NULL,
                year INTEGER NOT NULL,
                section TEXT NOT NULL
            )
        """)
        # This setup script resets the table to the five sample records each time it runs.
        connection.execute("DELETE FROM students")
        connection.execute("DELETE FROM sqlite_sequence WHERE name = 'students'")
        students = [
            ("2024-1001", "Karol Vincent Pedregosa", "BSA", 4, "ANSCI"),
            ("2024-1002", "Liza Java", "BEED", 1, "D"),
            ("2024-1003", "Paul Joseph Miranda", "BSCS", 2, "A"),
            ("2024-1004", "Issa Kailah Javier", "BSHM", 3, "C"),
            ("2024-1005", "Rizza Anthea Malacad", "BSED-Filipino", 4, "B"),
        ]
        connection.executemany("""
            INSERT INTO students (student_id, name, program, year, section)
            VALUES (?, ?, ?, ?, ?)
        """, students)
        connection.commit()
    finally:
        connection.close()
    print(f"Database initialized: {DB_PATH}")

if __name__ == "__main__":
    initialize_database()
