# src/database/db_manager.py
# Handles SQLite database operations for user accounts and theme states.
# Uses platform-specific pathing to write to writable locations on mobile.

import os
import sqlite3
import hashlib
from kivy.utils import platform
from kivy.app import App

def get_db_path():
    db_name = "users.db"
    if platform == 'android':
        app = App.get_running_app()
        if app:
            # Persistent internal data folder for the Android application
            return os.path.join(app.user_data_dir, db_name)
        else:
            # Fallback if application context is not fully loaded yet
            return os.path.join(os.environ.get('ANDROID_PRIVATE', '.'), db_name)
    else:
        # Standard local directory on Desktop environments
        return db_name

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            theme TEXT DEFAULT 'dark'
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    else:
        if isinstance(salt, str):
            salt = bytes.fromhex(salt)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return key.hex(), salt.hex()

def verify_password(stored_hash, salt, entered_password):
    key, _ = hash_password(entered_password, salt)
    return key == stored_hash

def register_user(username, password):
    if not username or not password:
        return False, "Fields cannot be empty. ❌"
    if len(password) < 6:
        return False, "Password must be at least 6 characters. ❌"
        
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username.lower(),))
    if cursor.fetchone() is not None:
        conn.close()
        return False, "Username already exists. ❌"
        
    pwd_hash, salt = hash_password(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt, theme) VALUES (?, ?, ?, 'dark')",
            (username.lower(), pwd_hash, salt)
        )
        conn.commit()
        return True, "Registered successfully! Log in now. ✅"
    except Exception as e:
        return False, f"Database error: {e} ❌"
    finally:
        conn.close()

def login_user(username, password):
    if not username or not password:
        return False, "Please enter all fields. ❌"
        
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username.lower(),))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return False, "Invalid username or password. ❌"
        
    stored_hash, salt = row
    if verify_password(stored_hash, salt, password):
        return True, "Success! ✅"
    return False, "Invalid username or password. ❌"

def get_user_theme(username):
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT theme FROM users WHERE username = ?", (username.lower(),))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return "dark"

def set_user_theme(username, theme):
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET theme = ? WHERE username = ?", (theme, username.lower()))
    conn.commit()
    conn.close()
