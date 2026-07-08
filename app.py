# app.py
# Redirection script that launches the Android-compatible Kivy GUI interface.
# Keeps the entry point consistent with standard desktop launching conventions.

import sys
import os

# Add the project directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import AIAppManager

if __name__ == '__main__':
    AIAppManager().run()
