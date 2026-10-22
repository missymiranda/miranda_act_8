import os
import sqlite3
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

DB_PATH = Path(__file__).with_name("students.db")


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_database():
    """Create the students table and add sample records if empty."""
    conn = get_db_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                name TEXT NOT NULL,
                program TEXT NOT NULL,
                year INTEGER NOT NULL,
                section TEXT NOT NULL
            )
        """)

        count = conn.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        if count == 0:
            sample_students = [
                ("2024-1001", "Karol Vincent Pedregosa", "BSA", 4, "ANSCI"),
                ("2024-1002", "Liza Java", "BEED", 1, "D"),
                ("2024-1003", "Paul Joseph Miranda", "BSCS", 2, "A"),
                ("2024-1004", "Issa Kailah Javier", "BSHM", 3, "C"),
                ("2024-1005", "Rizza Anthea Malacad", "BSED-Filipino", 4, "B"),
            ]

            conn.executemany("""
                INSERT INTO students
                    (student_id, name, program, year, section)
                VALUES (?, ?, ?, ?, ?)
            """, sample_students)

        conn.commit()

    finally:
        conn.close()


# ==========================================
# VALIDATE STUDENT DATA
# ==========================================

def validate_student(data):
    if not isinstance(data, dict):
        return None, "Send student data as a JSON object."

    student_id = str(data.get("student_id", "")).strip()
    name = str(data.get("name", "")).strip()
    program = str(data.get("program", "")).strip()
    section = str(data.get("section", "")).strip()

    try:
        year = int(data.get("year", ""))
    except (TypeError, ValueError):
        return None, "Year must be a whole number."

    if not all([student_id, name, program, section]):
        return None, (
            "All fields are required: "
            "student_id, name, program, year, section."
        )

    if year < 1 or year > 6:
        return None, "Year must be between 1 and 6."

    return {
        "student_id": student_id,
        "name": name,
        "program": program,
        "year": year,
        "section": section
    }, None


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():
    ensure_database()
    return render_template("index.html")


# ==========================================
# ACTIVITY 8: GET ALL STUDENTS
# AND CREATE A STUDENT
# ==========================================

@app.route("/api/students", methods=["GET", "POST"])
def api_students():
    ensure_database()

    # GET: Retrieve all students
    if request.method == "GET":
        conn = get_db_connection()

        try:
            rows = conn.execute(
                "SELECT * FROM students ORDER BY id"
            ).fetchall()

            return jsonify([dict(row) for row in rows])

        finally:
            conn.close()

    # POST: Add a new student
    student_data, error = validate_student(
        request.get_json(silent=True)
    )

    if error:
        return jsonify({"error": error}), 400

    conn = get_db_connection()

    try:
        cursor = conn.execute("""
            INSERT INTO students
                (student_id, name, program, year, section)
            VALUES (?, ?, ?, ?, ?)
        """, (
            student_data["student_id"],
            student_data["name"],
            student_data["program"],
            student_data["year"],
            student_data["section"]
        ))

        conn.commit()

        created = conn.execute(
            "SELECT * FROM students WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

        return jsonify({
            "message": "Student added successfully.",
            "student": dict(created)
        }), 201

    finally:
        conn.close()


# ==========================================
# ACTIVITY 8: GET ONE, UPDATE, OR DELETE
# ==========================================

@app.route(
    "/api/students/<int:student_record_id>",
    methods=["GET", "PUT", "DELETE"]
)
def api_student_detail(student_record_id):
    ensure_database()

    conn = get_db_connection()

    try:
        existing = conn.execute(
            "SELECT * FROM students WHERE id = ?",
            (student_record_id,)
        ).fetchone()

        if existing is None:
            return jsonify({
                "error": "Student not found."
            }), 404

        # GET: Retrieve one student
        if request.method == "GET":
            return jsonify(dict(existing))

        # DELETE: Delete one student
        if request.method == "DELETE":
            conn.execute(
                "DELETE FROM students WHERE id = ?",
                (student_record_id,)
            )

            conn.commit()

            return jsonify({
                "message": "Student deleted successfully.",
                "id": student_record_id
            }), 200

        # PUT: Update one student
        student_data, error = validate_student(
            request.get_json(silent=True)
        )

        if error:
            return jsonify({"error": error}), 400

        conn.execute("""
            UPDATE students
            SET student_id = ?,
                name = ?,
                program = ?,
                year = ?,
                section = ?
            WHERE id = ?
        """, (
            student_data["student_id"],
            student_data["name"],
            student_data["program"],
            student_data["year"],
            student_data["section"],
            student_record_id
        ))

        conn.commit()

        updated = conn.execute(
            "SELECT * FROM students WHERE id = ?",
            (student_record_id,)
        ).fetchone()

        return jsonify({
            "message": "Student updated successfully.",
            "student": dict(updated)
        }), 200

    finally:
        conn.close()


# ==========================================
# ACTIVITY 8: CLASSMATE STUDENTS API
# ==========================================

@app.route("/api/classmate-students", methods=["GET"])
def classmate_students():
    api_url = request.args.get("url", "").strip()
    parsed = urlparse(api_url)

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not (
            parsed.hostname == "onrender.com"
            or parsed.hostname.endswith(".onrender.com")
        )
        or parsed.path.rstrip("/") != "/api/students"
        or parsed.query
        or parsed.username
        or parsed.password
    ):
        return jsonify({
            "error": (
                "Enter your classmate's HTTPS Render API URL "
                "ending in /api/students."
            )
        }), 400

    try:
        req = Request(
            api_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Activity8StudentClient/1.0"
            }
        )

        with urlopen(req, timeout=8) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        if not isinstance(data, list):
            return jsonify({
                "error": (
                    "The classmate API did not return a JSON list."
                )
            }), 502

        return jsonify(data), 200

    except (
        HTTPError,
        URLError,
        TimeoutError,
        ValueError,
        OSError
    ) as exc:
        app.logger.warning(
            "Classmate API request failed: %s", exc
        )

        return jsonify({
            "error": (
                "Could not load the classmate API. "
                "Check the URL and try again."
            )
        }), 502


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":
    ensure_database()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )