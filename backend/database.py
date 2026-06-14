import sqlite3
import os
import pickle
import numpy as np

DB_PATH = os.path.join(os.path.dirname(__file__), "shan.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS faces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            face_name TEXT NOT NULL DEFAULT 'Face 1',
            face_encoding BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            attempt_type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


def save_user(username: str):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
    conn.commit()
    conn.close()


def get_user(username: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


def username_exists(username: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row is not None


def save_face(username: str, face_name: str, encoding: np.ndarray) -> int:
    blob = pickle.dumps(encoding)
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO faces (username, face_name, face_encoding) VALUES (?, ?, ?)",
        (username, face_name, blob),
    )
    face_id = cur.lastrowid
    conn.commit()
    conn.close()
    return face_id


def get_faces(username: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, face_name, created_at FROM faces WHERE username = ? ORDER BY created_at ASC",
        (username,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_face_encodings(username: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, face_name, face_encoding FROM faces WHERE username = ? ORDER BY created_at ASC",
        (username,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_face_by_id(face_id: int, username: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, face_name, created_at FROM faces WHERE id = ? AND username = ?",
        (face_id, username),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_face_name(face_id: int, username: str, new_name: str):
    conn = get_connection()
    conn.execute(
        "UPDATE faces SET face_name = ? WHERE id = ? AND username = ?",
        (new_name, face_id, username),
    )
    conn.commit()
    conn.close()


def delete_face(face_id: int, username: str):
    conn = get_connection()
    conn.execute(
        "DELETE FROM faces WHERE id = ? AND username = ?",
        (face_id, username),
    )
    conn.commit()
    conn.close()


def log_event(username: str, event_type: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO security_logs (username, attempt_type) VALUES (?, ?)",
        (username, event_type),
    )
    conn.commit()
    conn.close()


def log_attempt(username: str):
    log_event(username, "FAILED_LOGIN")


def log_successful_login(username: str):
    log_event(username, "LOGIN")


def log_registration(username: str):
    log_event(username, "REGISTER")


def get_notifications(username: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, timestamp, attempt_type FROM security_logs WHERE username = ? AND read = 0 AND attempt_type = 'FAILED_LOGIN' ORDER BY timestamp DESC",
        (username,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def dismiss_notifications(username: str):
    conn = get_connection()
    conn.execute(
        "UPDATE security_logs SET read = 1 WHERE username = ? AND read = 0",
        (username,),
    )
    conn.commit()
    conn.close()


def get_user_history(username: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, attempt_type, timestamp FROM security_logs WHERE username = ? ORDER BY timestamp DESC",
        (username,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
