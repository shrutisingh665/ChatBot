# src/utils/logger.py
# Handles log files writing. Writes user/bot dialogue logs safely
# on Android writable storage path.

import os
from datetime import datetime
from kivy.utils import platform
from kivy.app import App

def get_log_path():
    log_name = "chat_history.txt"
    if platform == 'android':
        app = App.get_running_app()
        if app:
            return os.path.join(app.user_data_dir, log_name)
        else:
            return os.path.join(os.environ.get('ANDROID_PRIVATE', '.'), log_name)
    else:
        return log_name

def log_chat_history(username, speaker, text):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{username}] {speaker}: {text}\n")
    except Exception as e:
        print(f"Log history error: {e}")
