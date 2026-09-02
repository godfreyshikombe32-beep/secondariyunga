import hashlib
import json
import os
import secrets
import sqlite3
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


initialize_database()


def app(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")

    def response(status_code, headers_list, body_bytes):
        status_text = f"{status_code} OK" if status_code in (200, 201, 204) else f"{status_code} ERROR"
        start_response(status_text, headers_list)
        return [body_bytes]

    def send_json(status_code, payload):
        body = json.dumps(payload).encode()
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
            ("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"),
        ]
        return response(status_code, headers, body)

    if method == "OPTIONS":
        return send_json(204, {})

    auth_header = environ.get("HTTP_AUTHORIZATION", "").replace("Bearer ", "")
    is_auth = auth_header in TOKENS

    if path.startswith("/api/") and path != "/api/login" and not is_auth:
        return send_json(401, {"error": "Authentication required"})

    try:
        request_body_size = int(environ.get("CONTENT_LENGTH", 0))
    except (ValueError):
        request_body_size = 0

    request_body = environ["wsgi.input"].read(request_body_size) if request_body_size > 0 else b"{}"

    def read_json():
        return json.loads(request_body or b"{}")

    with connect() as connection:
        if method == "GET":
            if path == "/api/students":
                rows = connection.execute("SELECT * FROM students ORDER BY id").fetchall()
                return send_json(200, [row_json(row) for row in rows])
            elif path == "/api/teachers":
                rows = connection.execute("SELECT * FROM teachers ORDER BY id").fetchall()
                return send_json(200, [row_json(row) for row in rows])
            elif path == "/api/results":
                rows = connection.execute("SELECT * FROM results ORDER BY id").fetchall()
                return send_json(200, [row_json(row) for row in rows])
            elif path == "/api/settings":
                return send_json(200, row_json(connection.execute("SELECT * FROM settings WHERE id = 1").fetchone()))
            else:
                relative = "index.html" if path in ("", "/") else path.lstrip("/")
                file_path = (ROOT / relative).resolve()
                if not file_path.is_file():
                    return send_json(404, {"error": "Not found"})
                content_type = "text/html" if file_path.suffix == ".html" else "text/css" if file_path.suffix == ".css" else "application/javascript" if file_path.suffix == ".js" else "image/jpeg"
                body = file_path.read_bytes()
                headers = [("Content-Type", content_type), ("Content-Length", str(len(body)))]
                return response(200, headers, body)

        elif method == "POST":
            data = read_json()
            if path == "/api/login":
                password_hash = hashlib.sha256(data.get("password", "").encode()).hexdigest()
                user = connection.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", (data.get("username"), password_hash)).fetchone()
                if not user:
                    return send_json(401, {"error": "Invalid username or password"})
                token = secrets.token_urlsafe(32)
                TOKENS.add(token)
                return send_json(200, {"token": token})

            elif path == "/api/students":
                cursor = connection.execute("INSERT INTO students (name, registration_number, class_name, gender, date_of_birth, parent_name, parent_phone, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (data["name"], data["registrationNumber"], data.get("className"), data.get("gender"), data.get("dateOfBirth"), data.get("parentName"), data.get("parentPhone"), data.get("address")))
                return send_json(201, {"id": cursor.lastrowid})
            elif path == "/api/teachers":
                cursor = connection.execute("INSERT INTO teachers (name, email, phone, subject, classes, role) VALUES (?, ?, ?, ?, ?, ?)", (data["name"], data.get("email"), data.get("phone"), data.get("subject"), data.get("classes"), data.get("role")))
                return send_json(201, {"id": cursor.lastrowid})
            elif path == "/api/results":
                cursor = connection.execute("INSERT INTO results (exam, class_name, subject, average, date, status) VALUES (?, ?, ?, ?, ?, ?)", (data["exam"], data.get("className"), data.get("subject"), data.get("average"), data.get("date"), data.get("status")))
                return send_json(201, {"id": cursor.lastrowid})
            elif path == "/api/settings":
                connection.execute("UPDATE settings SET school_name = ?, academic_year = ? WHERE id = 1", (data.get("schoolName"), data.get("academicYear")))
                return send_json(200, {"saved": True})

        elif method == "PUT" and path.startswith("/api/students/"):
            data = read_json()
            student_id = path.rsplit("/", 1)[1]
            connection.execute("UPDATE students SET name=?, registration_number=?, class_name=?, gender=?, date_of_birth=?, parent_name=?, parent_phone=?, address=? WHERE id=?", (data["name"], data["registrationNumber"], data.get("className"), data.get("gender"), data.get("dateOfBirth"), data.get("parentName"), data.get("parentPhone"), data.get("address"), student_id))
            return send_json(200, {"saved": True})

        elif method == "DELETE" and path.startswith("/api/students/"):
            connection.execute("DELETE FROM students WHERE id = ?", (path.rsplit("/", 1)[1],))
            return send_json(200, {"deleted": True})

    return send_json(404, {"error": "Not found"})


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    port = int(os.environ.get("PORT", 8000))
    httpd = make_server("0.0.0.0", port, app)
    print(f"Running on port {port}...")
    httpd.serve_forever()
