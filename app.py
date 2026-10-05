from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

# database.db is created in the same folder as app.py
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

# Exam questions (pass mark = 3 out of 5)
QUESTIONS = [
    {"q": "Who created the Python programming language?",
     "options": ["Guido van Rossum", "Dennis Ritchie", "James Gosling", "Bjarne Stroustrup"],
     "answer": "Guido van Rossum"},
    {"q": "Which keyword is used to define a function in Python?",
     "options": ["func", "define", "def", "function"],
     "answer": "def"},
    {"q": "Which symbol is used for a single-line comment in Python?",
     "options": ["//", "#", "<!-- -->", "**"],
     "answer": "#"},
    {"q": "Which built-in Python module is used to create a GUI?",
     "options": ["Tkinter", "NumPy", "Pandas", "Flask"],
     "answer": "Tkinter"},
    {"q": "What is the file extension for a Python script?",
     "options": [".py", ".pyt", ".pt", ".python"],
     "answer": ".py"},
]
PASS_MARK = 3


# ---------- Database ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        full_name TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER NOT NULL,
                        score INTEGER NOT NULL,
                        total INTEGER NOT NULL,
                        percentage REAL NOT NULL,
                        status TEXT NOT NULL,
                        attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (student_id) REFERENCES students (id))""")
    conn.commit()
    conn.close()


# ---------- Page ----------
@app.route("/")
def home():
    # send questions to the page WITHOUT the correct answers
    questions = [{"q": item["q"], "options": item["options"]} for item in QUESTIONS]
    return render_template("index.html", questions=questions, pass_mark=PASS_MARK)


# ---------- Module 1: Registration ----------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data["name"].strip()
    email = data["email"].strip()
    username = data["username"].strip()
    password = data["password"]

    conn = get_db()
    old = conn.execute("SELECT id FROM students WHERE username = ? OR email = ?",
                       (username, email)).fetchone()
    if old:
        conn.close()
        return jsonify({"ok": False, "error": "Username or email already registered."})

    conn.execute("INSERT INTO students (full_name, email, username, password_hash) VALUES (?, ?, ?, ?)",
                 (name, email, username, generate_password_hash(password)))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ---------- Module 2: Login ----------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE username = ?",
                           (data["username"].strip(),)).fetchone()
    conn.close()

    if student and check_password_hash(student["password_hash"], data["password"]):
        session["student_id"] = student["id"]
        return jsonify({"ok": True, "name": student["full_name"]})
    return jsonify({"ok": False, "error": "Invalid username or password."})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


# ---------- Module 5: Main menu (past results) ----------
@app.route("/history")
def history():
    if "student_id" not in session:
        return jsonify({"ok": False, "error": "Please login."})

    conn = get_db()
    rows = conn.execute("SELECT score, total, percentage, status, attempted_at FROM results "
                        "WHERE student_id = ? ORDER BY id DESC", (session["student_id"],)).fetchall()
    conn.close()
    return jsonify({"ok": True, "history": [dict(r) for r in rows]})


# ---------- Modules 3 and 4: Check answers and save result ----------
@app.route("/submit", methods=["POST"])
def submit():
    if "student_id" not in session:
        return jsonify({"ok": False, "error": "Please login."})

    answers = request.get_json()["answers"]   # example: {"0": "def", "1": "#"}

    score = 0
    for i in range(len(QUESTIONS)):
        if answers.get(str(i)) == QUESTIONS[i]["answer"]:
            score += 1

    total = len(QUESTIONS)
    percentage = round(score / total * 100, 2)
    if score >= PASS_MARK:
        status = "PASS"
    else:
        status = "FAIL"

    conn = get_db()
    conn.execute("INSERT INTO results (student_id, score, total, percentage, status) VALUES (?, ?, ?, ?, ?)",
                 (session["student_id"], score, total, percentage, status))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "score": score, "total": total,
                    "percentage": percentage, "status": status})


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
