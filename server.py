import hashlib
import json
import os
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
DATABASE = ROOT / "iyunga.db"
TOKENS = set()


def connect():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with connect() as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, registration_number TEXT UNIQUE NOT NULL, class_name TEXT, gender TEXT, date_of_birth TEXT, parent_name TEXT, parent_phone TEXT, address TEXT);
        CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT, phone TEXT, subject TEXT, classes TEXT, role TEXT);
        CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY AUTOINCREMENT, exam TEXT NOT NULL, class_name TEXT, subject TEXT, average TEXT, date TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, school_name TEXT, academic_year TEXT);
        INSERT OR IGNORE INTO settings (id, school_name, academic_year) VALUES (1, 'Iyunga Secondary School', '2026');
        """)
        connection.execute("INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (1, 'admin', ?)", (hashlib.sha256(b"1234").hexdigest(),))
        if connection.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            connection.executemany("INSERT INTO students (name, registration_number, class_name, gender, date_of_birth, parent_name, parent_phone, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
                ("John Michael", "ISS/2026/001", "Form I", "Male", "2010-01-15", "Michael John", "0712345678", "Iyunga"),
                ("Amina Hassan", "ISS/2026/002", "Form II", "Female", "2009-06-20", "Hassan Ali", "0755123456", "Mbeya")
            ])


def row_json(row):
    value = dict(row)
    if "registration_number" in value:
        value["registrationNumber"] = value.pop("registration_number")
        value["className"] = value.pop("class_name")
        value["dateOfBirth"] = value.pop("date_of_birth")
        value["parentName"] = value.pop("parent_name")
        value["parentPhone"] = value.pop("parent_phone")
    elif "class_name" in value:
        value["className"] = value.pop("class_name")
    return value


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def authenticated(self):
        return self.headers.get("Authorization", "").replace("Bearer ", "") in TOKENS

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/") and not self.authenticated():
            self.send_json(401, {"error": "Authentication required"})
            return
        with connect() as connection:
            if path == "/api/students":
                rows = connection.execute("SELECT * FROM students ORDER BY id").fetchall()
                self.send_json(200, [row_json(row) for row in rows])
            elif path == "/api/teachers":
                rows = connection.execute("SELECT * FROM teachers ORDER BY id").fetchall()
                self.send_json(200, [row_json(row) for row in rows])
            elif path == "/api/results":
                rows = connection.execute("SELECT * FROM results ORDER BY id").fetchall()
                self.send_json(200, [row_json(row) for row in rows])
            elif path == "/api/settings":
                self.send_json(200, row_json(connection.execute("SELECT * FROM settings WHERE id = 1").fetchone()))
            else:
                self.serve_file(path)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/login":
            data = self.read_json()
            password_hash = hashlib.sha256(data.get("password", "").encode()).hexdigest()
            with connect() as connection:
                user = connection.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", (data.get("username"), password_hash)).fetchone()
            if not user:
                self.send_json(401, {"error": "Invalid username or password"})
                return
            token = secrets.token_urlsafe(32)
            TOKENS.add(token)
            self.send_json(200, {"token": token})
            return
        if not self.authenticated():
            self.send_json(401, {"error": "Authentication required"})
            return
        data = self.read_json()
        with connect() as connection:
            if path == "/api/students":
                cursor = connection.execute("INSERT INTO students (name, registration_number, class_name, gender, date_of_birth, parent_name, parent_phone, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (data["name"], data["registrationNumber"], data.get("className"), data.get("gender"), data.get("dateOfBirth"), data.get("parentName"), data.get("parentPhone"), data.get("address")))
                self.send_json(201, {"id": cursor.lastrowid})
            elif path == "/api/teachers":
                cursor = connection.execute("INSERT INTO teachers (name, email, phone, subject, classes, role) VALUES (?, ?, ?, ?, ?, ?)", (data["name"], data.get("email"), data.get("phone"), data.get("subject"), data.get("classes"), data.get("role")))
                self.send_json(201, {"id": cursor.lastrowid})
            elif path == "/api/results":
                cursor = connection.execute("INSERT INTO results (exam, class_name, subject, average, date, status) VALUES (?, ?, ?, ?, ?, ?)", (data["exam"], data.get("className"), data.get("subject"), data.get("average"), data.get("date"), data.get("status")))
                self.send_json(201, {"id": cursor.lastrowid})
            elif path == "/api/settings":
                connection.execute("UPDATE settings SET school_name = ?, academic_year = ? WHERE id = 1", (data.get("schoolName"), data.get("academicYear")))
                self.send_json(200, {"saved": True})
            else:
                self.send_json(404, {"error": "Not found"})

    def do_PUT(self):
        if not self.authenticated():
            self.send_json(401, {"error": "Authentication required"})
            return
        path = urlparse(self.path).path
        data = self.read_json()
        if path.startswith("/api/students/"):
            student_id = path.rsplit("/", 1)[1]
            with connect() as connection:
                connection.execute("UPDATE students SET name=?, registration_number=?, class_name=?, gender=?, date_of_birth=?, parent_name=?, parent_phone=?, address=? WHERE id=?", (data["name"], data["registrationNumber"], data.get("className"), data.get("gender"), data.get("dateOfBirth"), data.get("parentName"), data.get("parentPhone"), data.get("address"), student_id))
            self.send_json(200, {"saved": True})
        else:
            self.send_json(404, {"error": "Not found"})

    def do_DELETE(self):
        if not self.authenticated():
            self.send_json(401, {"error": "Authentication required"})
            return
        path = urlparse(self.path).path
        if path.startswith("/api/students/"):
            with connect() as connection:
                connection.execute("DELETE FROM students WHERE id = ?", (path.rsplit("/", 1)[1],))
            self.send_json(200, {"deleted": True})
        else:
            self.send_json(404, {"error": "Not found"})

    def serve_file(self, path):
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        file_path = (ROOT / relative).resolve()
        if ROOT not in file_path.parents and file_path != ROOT:
            self.send_error(403)
            return
        if not file_path.is_file():
            self.send_error(404)
            return
        content_type = "text/html" if file_path.suffix == ".html" else "text/css" if file_path.suffix == ".css" else "application/javascript" if file_path.suffix == ".js" else "image/jpeg"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(format % args)


if __name__ == "__main__":
    initialize_database()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Iyunga backend running at http://{host}:{port}")
    server.serve_forever()