# app.py
# This script implements a complete desktop AI Chatbot with a Secure Login/Signup system.
# Core Features:
# 1. SQLite Database backend to store user credentials & persistent user theme settings.
# 2. Cryptographically strong password hashing using PBKDF2-HMAC-SHA256 (built-in).
# 3. GUI state toggling: Shows Login/Signup page first, then launches the Chat window.
# 4. Circular chatbot and user profile avatars rendered dynamically beside messages using PIL.
# 5. Multilingual support (English and Hindi) with custom auto-detection via Devanagari character checking.
# 6. Persistent user preference storage (Light/Dark themes) saved directly to SQLite.
# 7. Non-blocking typing animation ("Bot is typing...") running inside background threads.
# 8. Speech Recognition (Speech-to-Text) with language parameter controls ('en-US' / 'hi-IN').
# 9. Thread-safe Queue-based Speech Output (Text-to-Speech) mapping native language voices dynamically.
# 10. Persistent logging of conversations in chat_history.txt categorized by logged-in users.
# 11. Logout option to secure sessions and return to the login interface.

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import threading
import queue
import sqlite3
import hashlib
import speech_recognition as sr
import pyttsx3
import time
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw
from deep_translator import GoogleTranslator

# Attempt to load the chatbot backend logic
try:
    import chatbot
except FileNotFoundError as e:
    print(f"Error loading chatbot modules: {e}")
except Exception as e:
    print(f"An unexpected error occurred during chatbot initialization: {e}")


# Resolve directories relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "users.db")
LOG_PATH = os.path.join(BASE_DIR, "chat_history.txt")

# ==========================================
# DATABASE & SECURITY CONFIGURATION
# ==========================================

def init_db():
    """
    Initializes the SQLite database, creates the users table, and migrates the schema
    to include user theme preferences if missing.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL
        )
    """)
    
    # Schema migration: Add theme column if it does not exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'dark'")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    conn.commit()
    conn.close()

def hash_password(password, salt=None):
    """
    Generates a PBKDF2-HMAC-SHA256 hash for a password using a secure random salt.
    """
    if salt is None:
        salt = os.urandom(16) # 16-byte random salt
    else:
        if isinstance(salt, str):
            salt = bytes.fromhex(salt)
            
    # Perform PBKDF2 hashing
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return key.hex(), salt.hex()

def verify_password(stored_hash, salt, entered_password):
    """
    Checks if the entered password matches the stored hash.
    """
    key, _ = hash_password(entered_password, salt)
    return key == stored_hash

def register_user(username, password):
    """
    Registers a new user in the database. Returns (success, message).
    """
    if not username or not password:
        return False, "Fields cannot be empty. ❌"
    if len(password) < 6:
        return False, "Password must be at least 6 characters long. ❌"
        
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if username exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (username.lower(),))
    if cursor.fetchone() is not None:
        conn.close()
        return False, "Username already exists. ❌"
        
    # Hash password
    pwd_hash, salt = hash_password(password)
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username.lower(), pwd_hash, salt)
        )
        conn.commit()
        return True, "Registration successful! You can now log in. ✅"
    except Exception as e:
        return False, f"Database error: {e} ❌"
    finally:
        conn.close()

def login_user(username, password):
    """
    Validates user credentials against the SQLite database. Returns (success, message).
    """
    if not username or not password:
        return False, "Please enter both username and password. ❌"
        
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username.lower(),))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return False, "Invalid username or password. ❌"
        
    stored_hash, salt = row
    if verify_password(stored_hash, salt, password):
        return True, "Login successful! ✅"
    return False, "Invalid username or password. ❌"

def get_user_theme(username):
    """
    Retrieves the saved theme preference for the user from SQLite. Defaults to 'dark'.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT theme FROM users WHERE username = ?", (username.lower(),))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return "dark"

def set_user_theme(username, theme):
    """
    Saves the user's theme preference to SQLite.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET theme = ? WHERE username = ?", (theme, username.lower()))
    conn.commit()
    conn.close()


# ==========================================
# TRANSLATION & UTILITIES
# ==========================================

def translate_text(text, source='auto', target='en'):
    """
    Translates input text using Google Translate via deep-translator.
    """
    try:
        if not text.strip():
            return text
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def is_hindi(text):
    """
    Checks if a string contains characters from the Devanagari Unicode range.
    Useful for offline, high-speed Hindi language detection.
    """
    for char in text:
        if '\u0900' <= char <= '\u097f':
            return True
    return False


# ==========================================
# AVATAR PROCESSING UTILITY
# ==========================================

def load_circular_avatar(image_path, size=(40, 40)):
    """
    Loads an image, resizes it, masks it to a circular shape, and returns a PhotoImage.
    """
    try:
        if not os.path.exists(image_path):
            return None
            
        # Open and resize image
        img = Image.open(image_path).convert("RGBA")
        img = img.resize(size, Image.Resampling.LANCZOS)
        
        # Create alpha mask for the circle shape
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)
        
        # Apply circular crop using mask
        circular_img = Image.new("RGBA", size, (0, 0, 0, 0))
        circular_img.paste(img, (0, 0), mask=mask)
        
        return ImageTk.PhotoImage(circular_img)
    except Exception as e:
        print(f"Error rendering circular avatar for {image_path}: {e}")
        return None


# ==========================================
# MAIN APPLICATION INTERFACE
# ==========================================

class AIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Assistant")
        self.root.geometry("560x660")
        self.root.resizable(width=False, height=False)

        # Theme color definitions (Catppuccin Mocha vs Catppuccin Latte)
        self.themes = {
            "dark": {
                "bg": "#181825",
                "card_bg": "#1e1e2e",
                "entry_bg": "#313244",
                "text": "#cdd6f4",
                "border": "#45475a",
                "accent": "#89b4fa",
                "user_bubble": "#89b4fa",
                "user_bubble_fg": "#11111b",
                "bot_bubble": "#313244",
                "bot_bubble_fg": "#cdd6f4",
                "voice_btn": "#f5c2e7",
                "send_btn": "#a6e3a1",
                "header_fg": "#89b4fa"
            },
            "light": {
                "bg": "#eff1f5",
                "card_bg": "#e6e9ef",
                "entry_bg": "#ccd0da",
                "text": "#4c4f69",
                "border": "#bcc0cc",
                "accent": "#1e66f5",
                "user_bubble": "#1e66f5",
                "user_bubble_fg": "#ffffff",
                "bot_bubble": "#ccd0da",
                "bot_bubble_fg": "#4c4f69",
                "voice_btn": "#ea76cb",
                "send_btn": "#40a02b",
                "header_fg": "#1e66f5"
            }
        }

        # Set default startup variables (before login, default to dark card)
        self.current_theme = "dark"
        self.apply_theme_colors()

        # Load avatar assets (cached references)
        assets_dir = os.path.join(BASE_DIR, 'assets')
        self.bot_avatar_img = load_circular_avatar(os.path.join(assets_dir, "chatbot_avatar.png"), (40, 40))
        self.user_avatar_img = load_circular_avatar(os.path.join(assets_dir, "user_avatar.png"), (40, 40))

        # User session tracking & bubbles mapping cache
        self.current_user = None
        self.chat_bubbles = []

        # Speech Queue setup
        self.speech_queue = queue.Queue()
        self.start_speech_worker()

        # Build Container Frames
        self.main_container = tk.Frame(self.root, bg=self.bg_color)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.show_login_view()

    def apply_theme_colors(self):
        """
        Extracts values from the themes dictionary and binds them to color variables.
        """
        colors = self.themes[self.current_theme]
        self.bg_color = colors["bg"]
        self.card_bg = colors["card_bg"]
        self.entry_bg = colors["entry_bg"]
        self.text_color = colors["text"]
        self.border_color = colors["border"]
        self.accent_color = colors["accent"]
        self.user_bubble_bg = colors["user_bubble"]
        self.user_bubble_fg = colors["user_bubble_fg"]
        self.bot_bubble_bg = colors["bot_bubble"]
        self.bot_bubble_fg = colors["bot_bubble_fg"]

    # ==========================================
    # LOGIN / SIGNUP VIEW IMPLEMENTATION
    # ==========================================

    def show_login_view(self):
        """
        Clears the main container and displays the Login/Registration card layout.
        """
        # Clear container
        for widget in self.main_container.winfo_children():
            widget.destroy()

        self.root.title("AI Assistant - Login")
        self.root.configure(bg=self.bg_color)
        self.main_container.configure(bg=self.bg_color)

        # Outer card frame to bundle credentials form
        card = tk.Frame(self.main_container, bg=self.card_bg, padx=30, pady=40, highlightthickness=1, highlightbackground=self.border_color)
        card.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=400, height=440)

        # Title Label
        title_label = tk.Label(card, text="AI Portal Login", font=("Segoe UI", 18, "bold"), bg=self.card_bg, fg=self.accent_color)
        title_label.pack(pady=(0, 25))

        # Username Input
        user_lbl = tk.Label(card, text="Username", font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.text_color)
        user_lbl.pack(anchor=tk.W)
        self.login_user_entry = tk.Entry(card, bg=self.entry_bg, fg=self.text_color, insertbackground=self.text_color, font=("Segoe UI", 11), bd=0, highlightthickness=1, highlightbackground=self.border_color, highlightcolor=self.accent_color)
        self.login_user_entry.pack(fill=tk.X, ipady=8, pady=(5, 15))

        # Password Input
        pass_lbl = tk.Label(card, text="Password", font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.text_color)
        pass_lbl.pack(anchor=tk.W)
        self.login_pass_entry = tk.Entry(card, show="*", bg=self.entry_bg, fg=self.text_color, insertbackground=self.text_color, font=("Segoe UI", 11), bd=0, highlightthickness=1, highlightbackground=self.border_color, highlightcolor=self.accent_color)
        self.login_pass_entry.pack(fill=tk.X, ipady=8, pady=(5, 20))

        # Status Label
        self.login_status = tk.Label(card, text="", font=("Segoe UI", 9), bg=self.card_bg, fg="#f38ba8", wrap=True)
        self.login_status.pack(fill=tk.X, pady=(0, 15))

        # Buttons Frame
        btn_frame = tk.Frame(card, bg=self.card_bg)
        btn_frame.pack(fill=tk.X)

        # Log In Action
        login_btn = tk.Button(btn_frame, text="Log In", font=("Segoe UI", 11, "bold"), bg="#a6e3a1", fg="#11111b", activebackground="#b4befe", activeforeground="#11111b", bd=0, pady=6, cursor="hand2", command=self.handle_login)
        login_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Sign Up / Register Action
        signup_btn = tk.Button(btn_frame, text="Sign Up", font=("Segoe UI", 11, "bold"), bg=self.accent_color, fg="#11111b", activebackground="#b4befe", activeforeground="#11111b", bd=0, pady=6, cursor="hand2", command=self.handle_signup)
        signup_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))

        # Bind Enter key inside credentials to log in
        self.login_pass_entry.bind("<Return>", lambda e: self.handle_login())

    def handle_login(self):
        """
        Validates credentials, retrieves saved user theme, and shifts to chat view upon success.
        """
        username = self.login_user_entry.get().strip()
        password = self.login_pass_entry.get().strip()
        
        success, message = login_user(username, password)
        if success:
            self.current_user = username.lower()
            # Retrieve persistent user theme settings
            self.current_theme = get_user_theme(self.current_user)
            self.apply_theme_colors()
            self.log_session_start()
            self.show_chat_view()
        else:
            self.login_status.config(text=message, fg="#f38ba8")

    def handle_signup(self):
        """
        Processes sign up and writes output message to the card status bar.
        """
        username = self.login_user_entry.get().strip()
        password = self.login_pass_entry.get().strip()
        
        success, message = register_user(username, password)
        if success:
            self.login_status.config(text=message, fg="#a6e3a1") # Green on success
            self.login_pass_entry.delete(0, tk.END)
        else:
            self.login_status.config(text=message, fg="#f38ba8") # Red on failure

    # ==========================================
    # CHAT VIEW IMPLEMENTATION
    # ==========================================

    def show_chat_view(self):
        """
        Clears the container and builds the main speech-enabled chatbot interface.
        """
        for widget in self.main_container.winfo_children():
            widget.destroy()

        self.root.title(f"AI Assistant - Chatting as {self.current_user}")
        self.chat_bubbles = []

        # Configure custom combobox styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.update_combobox_style()

        # Top Bar (Header + Language + Theme + Logout)
        self.top_bar = tk.Frame(self.main_container, bg=self.bg_color, pady=10)
        self.top_bar.pack(fill=tk.X, padx=15)

        # Welcome Header Label
        self.header_lbl = tk.Label(self.top_bar, text=f"User: {self.current_user}", font=("Segoe UI", 11, "bold"), bg=self.bg_color, fg=self.accent_color)
        self.header_lbl.pack(side=tk.LEFT)

        # Language Selector Combobox
        self.lang_var = tk.StringVar(value="Auto-Detect")
        self.lang_lbl = tk.Label(self.top_bar, text="Language:", font=("Segoe UI", 9, "bold"), bg=self.bg_color, fg=self.text_color)
        self.lang_lbl.pack(side=tk.LEFT, padx=(15, 5))
        
        self.lang_menu = ttk.Combobox(
            self.top_bar, 
            textvariable=self.lang_var, 
            values=["Auto-Detect", "English", "Hindi"], 
            state="readonly", 
            width=11,
            font=("Segoe UI", 9)
        )
        self.lang_menu.pack(side=tk.LEFT)

        # Logout Button
        self.logout_btn = tk.Button(self.top_bar, text="Logout ↩", font=("Segoe UI", 9, "bold"), bg="#f38ba8", fg="#11111b", activebackground="#f5bde6", bd=0, padx=10, pady=3, cursor="hand2", command=self.handle_logout)
        self.logout_btn.pack(side=tk.RIGHT)

        # Theme Switch Button
        theme_txt = "Theme: ☀️" if self.current_theme == "dark" else "Theme: 🌙"
        self.theme_button = tk.Button(self.top_bar, text=theme_txt, font=("Segoe UI", 9, "bold"), bg=self.accent_color, fg="#11111b", activebackground="#b4befe", bd=0, padx=10, pady=3, cursor="hand2", command=self.toggle_theme)
        self.theme_button.pack(side=tk.RIGHT, padx=(0, 10))

        # Chat display frame (Canvas + Scrollbar)
        self.display_frame = tk.Frame(self.main_container, bg=self.bg_color)
        self.display_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        # Canvas
        self.canvas = tk.Canvas(self.display_frame, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        self.scrollbar = tk.Scrollbar(self.display_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Bubble frame inside canvas
        self.bubbles_frame = tk.Frame(self.canvas, bg=self.bg_color)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.bubbles_frame, anchor="nw")

        self.bubbles_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Bottom Input Control Bar
        self.bottom_frame = tk.Frame(self.main_container, bg=self.card_bg, pady=15, padx=15)
        self.bottom_frame.pack(fill=tk.X)

        # Input Box
        self.entry_box = tk.Entry(self.bottom_frame, bg=self.entry_bg, fg=self.text_color, insertbackground=self.text_color, font=("Segoe UI", 11), bd=0, highlightthickness=1, highlightbackground=self.border_color, highlightcolor=self.accent_color)
        self.entry_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=8, padx=(0, 8))
        self.entry_box.focus()

        # Bind Enter to send message
        self.entry_box.bind("<Return>", self.send_message)

        # Speak Button
        self.voice_button = tk.Button(self.bottom_frame, text="🎙 Speak", font=("Segoe UI", 11, "bold"), bg=self.themes[self.current_theme]["voice_btn"], fg="#11111b", activebackground="#f5bde6", bd=0, padx=14, pady=5, command=self.start_voice_recognition, cursor="hand2")
        self.voice_button.pack(side=tk.LEFT, padx=(0, 8))

        # Send Button
        self.send_button = tk.Button(self.bottom_frame, text="Send", font=("Segoe UI", 11, "bold"), bg=self.themes[self.current_theme]["send_btn"], fg="#11111b", activebackground="#b4befe", bd=0, padx=16, pady=5, command=lambda: self.send_message(None), cursor="hand2")
        self.send_button.pack(side=tk.RIGHT)

        # Apply root background configuration
        self.root.configure(bg=self.bg_color)

        # Bot initial greetings
        self.insert_bubble("Bot", f"Hello {self.current_user}! I am PythonBot. How can I help you prepare today? 😊")

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def update_combobox_style(self):
        """
        Redraws the ttk combobox layout colors.
        """
        self.style.configure('TCombobox', fieldbackground=self.entry_bg, background=self.entry_bg, foreground=self.text_color, arrowcolor=self.accent_color, bordercolor=self.border_color)
        self.style.map('TCombobox', fieldbackground=[('readonly', self.entry_bg)], selectbackground=[('readonly', self.accent_color)], selectforeground=[('readonly', '#11111b')])

    # ==========================================
    # THEME TOGGLING IMPLEMENTATION
    # ==========================================

    def toggle_theme(self):
        """
        Toggles between light and dark themes, records preference to SQLite, and updates colors.
        """
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        set_user_theme(self.current_user, self.current_theme)
        
        self.apply_theme_colors()
        self.update_gui_theme()

    def update_gui_theme(self):
        """
        Applies newly computed theme colors to all active Tkinter widgets dynamically.
        """
        colors = self.themes[self.current_theme]
        
        # Core containers
        self.root.configure(bg=self.bg_color)
        self.main_container.configure(bg=self.bg_color)
        self.top_bar.configure(bg=self.bg_color)
        self.display_frame.configure(bg=self.bg_color)
        self.canvas.configure(bg=self.bg_color)
        self.bubbles_frame.configure(bg=self.bg_color)
        self.bottom_frame.configure(bg=self.card_bg)

        # Labels
        self.header_lbl.configure(bg=self.bg_color, fg=self.accent_color)
        self.lang_lbl.configure(bg=self.bg_color, fg=self.text_color)

        # Combobox style
        self.update_combobox_style()

        # Input fields & controls
        self.entry_box.configure(
            bg=self.entry_bg, 
            fg=self.text_color, 
            insertbackground=self.text_color,
            highlightbackground=self.border_color, 
            highlightcolor=self.accent_color
        )
        self.voice_button.configure(bg=colors["voice_btn"])
        self.send_button.configure(bg=colors["send_btn"])
        
        # Theme button text
        theme_txt = "Theme: ☀️" if self.current_theme == "dark" else "Theme: 🌙"
        self.theme_button.configure(text=theme_txt, bg=self.accent_color)

        # Dynamically recolor existing chat bubbles
        for sender, bubble_widget, row_frame, avatar_widget in self.chat_bubbles:
            row_frame.configure(bg=self.bg_color)
            avatar_widget.configure(bg=self.bg_color)
            if sender == "You":
                bubble_widget.configure(bg=self.user_bubble_bg, fg=self.user_bubble_fg)
            else:
                bubble_widget.configure(bg=self.bot_bubble_bg, fg=self.bot_bubble_fg)

    # ==========================================
    # LOGGING & CHAT UTILITIES
    # ==========================================

    def handle_logout(self):
        """
        Clears user sessions, stops ongoing speech outputs, and redirects to LoginView.
        """
        self.log_session_end()
        
        # Stop speech thread requests
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break
                
        self.current_user = None
        self.chat_bubbles = []
        self.show_login_view()

    def set_input_state(self, state):
        """
        Locks or unlocks text input fields and send/voice triggers to avoid spam.
        """
        self.entry_box.config(state=state)
        self.send_button.config(state=state)
        self.voice_button.config(state=state)

    def log_session_start(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n=== [{self.current_user}] Chat Session Started: {timestamp} ===\n")
        except Exception as e:
            print(f"Failed session start logging: {e}")

    def log_session_end(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"=== [{self.current_user}] Chat Session Ended: {timestamp} ===\n")
        except Exception as e:
            print(f"Failed session end logging: {e}")

    def log_chat_message(self, sender, text):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [{self.current_user}] {sender}: {text}\n")
        except Exception as e:
            print(f"Failed message logging: {e}")

    def insert_bubble(self, sender, text):
        """
        Appends user/bot chat bubble dynamically next to their circular avatar label.
        """
        row_frame = tk.Frame(self.bubbles_frame, bg=self.bg_color, pady=6)
        row_frame.pack(fill=tk.X, expand=True)

        # Bubble configuration
        if sender == "You":
            bubble_bg = self.user_bubble_bg
            bubble_fg = self.user_bubble_fg
            avatar_img = self.user_avatar_img
            align_side = tk.RIGHT
            pad_bubble = (40, 0)
            pad_avatar = (5, 10)
            self.log_chat_message(self.current_user, text)
        else:
            bubble_bg = self.bot_bubble_bg
            bubble_fg = self.bot_bubble_fg
            avatar_img = self.bot_avatar_img
            align_side = tk.LEFT
            pad_bubble = (0, 40)
            pad_avatar = (10, 5)
            self.log_chat_message("Bot", text)

        # 1. Create and pack Avatar container
        if avatar_img:
            avatar_label = tk.Label(row_frame, image=avatar_img, bg=self.bg_color)
        else:
            # Fallback circle graphic if file is missing
            avatar_canvas = tk.Canvas(row_frame, width=40, height=40, bg=self.bg_color, highlightthickness=0)
            color = self.accent_color if sender == "You" else "#f5c2e7"
            avatar_canvas.create_oval(2, 2, 38, 38, fill=color, outline="")
            initial = sender[0].upper() if sender == "You" else "B"
            avatar_canvas.create_text(20, 20, text=initial, fill="#11111b", font=("Segoe UI", 11, "bold"))
            avatar_label = avatar_canvas

        avatar_label.pack(side=align_side, anchor=tk.N, padx=pad_avatar)

        # 2. Create and pack Message bubble
        bubble = tk.Message(row_frame, text=text, bg=bubble_bg, fg=bubble_fg, font=("Segoe UI", 11), aspect=400, width=320, justify="left", padx=12, pady=8, bd=0)
        bubble.pack(side=align_side, anchor=tk.N, padx=pad_bubble)

        # Cache reference to dynamically re-theme
        self.chat_bubbles.append((sender, bubble, row_frame, avatar_label))

        self.root.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def insert_typing_bubble(self, is_hi=False):
        """
        Creates a temporary italicized 'Bot is typing...' bubble on the screen and returns the widget.
        Supports Hindi typing translation placeholder.
        """
        row_frame = tk.Frame(self.bubbles_frame, bg=self.bg_color, pady=6)
        row_frame.pack(fill=tk.X, expand=True)

        # Avatar layout
        if self.bot_avatar_img:
            avatar_label = tk.Label(row_frame, image=self.bot_avatar_img, bg=self.bg_color)
        else:
            avatar_canvas = tk.Canvas(row_frame, width=40, height=40, bg=self.bg_color, highlightthickness=0)
            avatar_canvas.create_oval(2, 2, 38, 38, fill="#f5c2e7", outline="")
            avatar_canvas.create_text(20, 20, text="B", fill="#11111b", font=("Segoe UI", 11, "bold"))
            avatar_label = avatar_canvas
            
        avatar_label.pack(side=tk.LEFT, anchor=tk.N, padx=(10, 5))

        # Select placeholder text
        typing_text = "बॉट टाइप कर रहा है... 🤔" if is_hi else "Bot is typing... 🤔"

        # Typing placeholder message widget
        bubble = tk.Message(
            row_frame,
            text=typing_text,
            bg=self.bot_bubble_bg,
            fg=self.bot_bubble_fg,
            font=("Segoe UI", 11, "italic"),
            aspect=400,
            width=320,
            justify="left",
            padx=12,
            pady=8,
            bd=0
        )
        bubble.pack(side=tk.LEFT, anchor=tk.N, padx=(0, 40))

        # Cache reference to dynamically re-theme
        self.chat_bubbles.append(("Bot", bubble, row_frame, avatar_label))

        self.root.update_idletasks()
        self.canvas.yview_moveto(1.0)

        return bubble

    def replace_typing_with_response(self, bubble_widget, response, lang_code):
        """
        Replaces the placeholder bubble text with the final response, logs it, and speaks it.
        Unlocks UI input controls upon completion.
        """
        # Update text contents and remove italics
        bubble_widget.config(text=response, font=("Segoe UI", 11))
        
        # Log and speak in the proper language
        self.log_chat_message("Bot", response)
        self.speak_response(response, lang_code)

        # Re-enable inputs
        self.set_input_state(tk.NORMAL)
        self.entry_box.focus()

        # Update scrollbar location
        self.root.update_idletasks()
        self.canvas.yview_moveto(1.0)


    # ==========================================
    # SPEECH SYNTHESIS ENGINE (TTS)
    # ==========================================

    def start_speech_worker(self):
        """
        Starts a daemon worker to execute sequential, thread-safe speech outputs.
        Supports selecting Hindi voices dynamically if available on the host system.
        """
        def _speech_worker():
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 155)
            except Exception as e:
                print(f"TTS Engine worker error: {e}")
                return

            while True:
                item = self.speech_queue.get()
                if item is None:
                    break
                text, lang_code = item
                try:
                    # Select voice matching target language
                    voices = engine.getProperty('voices')
                    selected_voice = None
                    for voice in voices:
                        if lang_code == 'hi' and ('hindi' in voice.name.lower() or 'hi' in voice.id.lower() or 'hi_in' in voice.id.lower()):
                            selected_voice = voice.id
                            break
                        elif lang_code == 'en' and ('english' in voice.name.lower() or 'en' in voice.id.lower() or 'en_us' in voice.id.lower() or 'en_gb' in voice.id.lower()):
                            selected_voice = voice.id
                            
                    if selected_voice:
                        engine.setProperty('voice', selected_voice)
                    
                    engine.say(text)
                    engine.runAndWait()
                except Exception as ex:
                    print(f"TTS execution error: {ex}")
                self.speech_queue.task_done()

        self.worker_thread = threading.Thread(target=_speech_worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def speak_response(self, text, lang_code):
        self.speech_queue.put((text, lang_code))

    # ==========================================
    # VOICE INPUT RECOGNITION (STT)
    # ==========================================

    def start_voice_recognition(self):
        """
        Runs voice capture as a background daemon task.
        Loads lang configuration to support both Hindi ('hi-IN') and English ('en-US').
        """
        self.voice_button.config(text="Listening...", state=tk.DISABLED, bg="#f38ba8")

        # Determine speech recognition language code
        selected_lang = self.lang_var.get()
        rec_lang = "en-US"
        if selected_lang == "Hindi":
            rec_lang = "hi-IN"

        def _recognize_speech():
            recognizer = sr.Recognizer()
            recognized_text = None
            
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.8)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                # Listen in target language
                recognized_text = recognizer.recognize_google(audio, language=rec_lang)
            
            except sr.WaitTimeoutError:
                self.root.after(0, lambda: self.insert_bubble("Bot", "Speech timeout: No audio detected. ❌"))
                self.root.after(0, lambda: self.speak_response("Speech timeout.", "en"))
            except sr.UnknownValueError:
                self.root.after(0, lambda: self.insert_bubble("Bot", "Sorry, I could not understand that audio. ❌"))
                self.root.after(0, lambda: self.speak_response("Sorry, I could not understand.", "en"))
            except sr.RequestError as e:
                self.root.after(0, lambda: self.insert_bubble("Bot", f"Speech service request error: {e} ❌"))
            except Exception as e:
                self.root.after(0, lambda: self.insert_bubble("Bot", f"Microphone connection error: {e} ❌"))
                self.root.after(0, lambda: self.speak_response("Microphone error.", "en"))

            self.root.after(0, lambda: self.voice_button.config(text="🎙 Speak", state=tk.NORMAL, bg=self.themes[self.current_theme]["voice_btn"]))
            
            if recognized_text:
                self.root.after(0, lambda: self.process_message(recognized_text))

        listener_thread = threading.Thread(target=_recognize_speech)
        listener_thread.daemon = True
        listener_thread.start()

    # ==========================================
    # CORE INTERACTION LOGIC
    # ==========================================

    def process_message(self, message):
        """
        Locks user inputs, displays user query, runs translation and chatbot classification
        inside background threads, displays typing animations, and triggers final updates.
        """
        # Lock inputs
        self.set_input_state(tk.DISABLED)

        # Render user bubble & log it
        self.insert_bubble("You", message)

        # Detect target language
        selected_lang = self.lang_var.get()
        if selected_lang == "Auto-Detect":
            input_lang = "hi" if is_hindi(message) else "en"
        elif selected_lang == "Hindi":
            input_lang = "hi"
        else:
            input_lang = "en"

        # Show temporary 'Bot is typing...' (localized)
        typing_bubble = self.insert_typing_bubble(is_hi=(input_lang == "hi"))

        def _async_process():
            query_for_bot = message
            
            # Translate Hindi input to English for classification & DB searching
            if input_lang == "hi":
                query_for_bot = translate_text(message, source="hi", target="en")

            # Get standard chatbot classification response
            try:
                raw_response, intent_tag = chatbot.chatbot_response(query_for_bot)
            except NameError:
                raw_response, intent_tag = "Error: Chatbot model is not loaded. Run train.py first to create the model files. ❌", "error"
            except Exception as e:
                raw_response, intent_tag = f"An error occurred: {str(e)} ❌", "error"

            combined_response = raw_response

            # Translate combined response back to Hindi if target language is Hindi
            final_response = combined_response
            if input_lang == "hi":
                final_response = translate_text(combined_response, source="en", target="hi")

            # Hold for typing animation (exactly 2 seconds total)
            time.sleep(2)

            # Update GUI inside the main thread
            self.root.after(0, lambda: self.replace_typing_with_response(typing_bubble, final_response, input_lang))

        # Launch prediction and translation in a background thread to keep UI completely fluid
        worker_thread = threading.Thread(target=_async_process)
        worker_thread.daemon = True
        worker_thread.start()

    def send_message(self, event):
        user_message = self.entry_box.get().strip()
        if not user_message:
            return "break"

        self.entry_box.delete(0, tk.END)
        self.process_message(user_message)
        return "break"

if __name__ == "__main__":
    # Validate assets before launching
    missing_files = []
    for f in ['words.pkl', 'classes.pkl', 'chatbot_model.keras']:
        if not os.path.exists(f):
            missing_files.append(f)
            
    if missing_files:
        print("\n" + "="*60)
        print("WARNING: Chatbot training files are missing!")
        print(f"Missing: {', '.join(missing_files)}")
        print("Please run 'python train.py' to train and save the model before launching app.py.")
        print("="*60 + "\n")
        
        warn_root = tk.Tk()
        warn_root.withdraw()
        messagebox.showerror(
            "Missing Training Files", 
            "The model training files (chatbot_model.keras, words.pkl, classes.pkl) were not found.\n\n"
            "Please run 'python train.py' to train your chatbot first, then start app.py."
        )
        warn_root.destroy()
        sys.exit(1)

    # Initialize SQL database schema
    init_db()

    # Start Tkinter Event loop
    root = tk.Tk()
    app = AIApp(root)
    root.mainloop()
