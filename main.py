# main.py
# Main Kivy App Launcher. Imports screens, coordinates theme setups,
# and executes the event loop. Compatible with Android build architectures.

import os
import sys

# Ensure local NLTK data folder path is registered
import nltk
from kivy.utils import platform

if platform == 'android':
    nltk_data_dir = os.path.join(os.environ.get('ANDROID_PRIVATE', '.'), 'nltk_data')
else:
    nltk_data_dir = os.path.join(os.path.dirname(__file__), 'nltk_data')

if nltk_data_dir not in nltk.data.path:
    nltk.data.path.append(nltk_data_dir)

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivy.utils import platform
from src.gui.screens import LoginScreen, ChatScreen

# Configure window settings for mobile support
Window.softinput_mode = 'resize'

# Simulate portrait mobile viewport on desktop
if platform != 'android':
    Window.size = (360, 640)

class AIAppManager(App):
    def build(self):
        # Establish Theme palettes matching Catppuccin color standards (Mocha and Latte)
        self.theme_palette = {
            "dark": {
                "bg": (0.094, 0.094, 0.145, 1),       # Mocha base
                "card_bg": (0.118, 0.118, 0.180, 1),  # Mocha surface
                "entry_bg": (0.192, 0.196, 0.266, 1), # Mocha text field
                "text": (0.803, 0.839, 0.956, 1),     # Mocha text
                "border": (0.271, 0.278, 0.352, 1),   # Mocha border
                "accent": (0.537, 0.705, 0.980, 1),   # Pastel Blue
                "user_bubble": (0.537, 0.705, 0.980, 1),
                "user_bubble_fg": (0.066, 0.066, 0.105, 1),
                "bot_bubble": (0.192, 0.196, 0.266, 1),
                "bot_bubble_fg": (0.803, 0.839, 0.956, 1),
                "voice_btn": (0.961, 0.761, 0.906, 1), # Pastel Pink
                "send_btn": (0.650, 0.890, 0.631, 1)   # Pastel Green
            },
            "light": {
                "bg": (0.937, 0.945, 0.961, 1),       # Latte base
                "card_bg": (0.902, 0.914, 0.937, 1),  # Latte surface
                "entry_bg": (0.800, 0.816, 0.855, 1), # Latte text field
                "text": (0.298, 0.310, 0.412, 1),     # Latte text
                "border": (0.737, 0.753, 0.800, 1),   # Latte border
                "accent": (0.118, 0.400, 0.961, 1),   # Intense Blue
                "user_bubble": (0.118, 0.400, 0.961, 1),
                "user_bubble_fg": (1, 1, 1, 1),
                "bot_bubble": (0.800, 0.816, 0.855, 1),
                "bot_bubble_fg": (0.298, 0.310, 0.412, 1),
                "voice_btn": (0.918, 0.463, 0.796, 1),
                "send_btn": (0.251, 0.627, 0.169, 1)
            }
        }
        
        self.current_theme = "dark"
        self.current_user = None

        self.sm = ScreenManager()
        
        # 1. Add Login screen
        self.login_screen = LoginScreen(self, name='login')
        self.sm.add_widget(self.login_screen)
        
        # 2. Add Chat screen
        self.chat_screen = ChatScreen(self, name='chat')
        self.sm.add_widget(self.chat_screen)
        
        return self.sm

    def load_chat_view(self):
        """Loads and enters the conversational chat interface."""
        self.chat_screen.setup_ui()
        self.sm.current = 'chat'

    def on_start(self):
        """Requests required runtime Android permissions at startup."""
        import threading
        
        # Start background unzipping of prepackaged NLTK zips on Android
        threading.Thread(target=self.extract_nltk_data, daemon=True).start()

        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.RECORD_AUDIO])
            except Exception as e:
                print(f"Failed to request Android permissions: {e}")

    def extract_nltk_data(self):
        """Asynchronously unzips prepackaged NLTK zip archives to writable internal storage."""
        import zipfile
        if platform == 'android':
            nltk_data_dir = os.path.join(os.environ.get('ANDROID_PRIVATE', '.'), 'nltk_data')
        else:
            nltk_data_dir = os.path.join(os.path.dirname(__file__), 'nltk_data')

        os.makedirs(nltk_data_dir, exist_ok=True)
        app_dir = os.path.dirname(__file__)

        # Extract WordNet corpus
        wordnet_zip = os.path.join(app_dir, 'nltk_data', 'corpora', 'wordnet.zip')
        wordnet_dest = os.path.join(nltk_data_dir, 'corpora')
        if os.path.exists(wordnet_zip):
            if not os.path.exists(os.path.join(wordnet_dest, 'wordnet')):
                os.makedirs(wordnet_dest, exist_ok=True)
                try:
                    with zipfile.ZipFile(wordnet_zip, 'r') as zf:
                        zf.extractall(wordnet_dest)
                    print("NLTK extraction: successfully unzipped wordnet.zip")
                except Exception as e:
                    print(f"NLTK extraction: error unzipping wordnet.zip: {e}")
            else:
                print("NLTK extraction: wordnet already unzipped")

        # Extract Punkt tokenizer
        punkt_zip = os.path.join(app_dir, 'nltk_data', 'tokenizers', 'punkt.zip')
        punkt_dest = os.path.join(nltk_data_dir, 'tokenizers')
        if os.path.exists(punkt_zip):
            if not os.path.exists(os.path.join(punkt_dest, 'punkt')):
                os.makedirs(punkt_dest, exist_ok=True)
                try:
                    with zipfile.ZipFile(punkt_zip, 'r') as zf:
                        zf.extractall(punkt_dest)
                    print("NLTK extraction: successfully unzipped punkt.zip")
                except Exception as e:
                    print(f"NLTK extraction: error unzipping punkt.zip: {e}")
            else:
                print("NLTK extraction: punkt already unzipped")

if __name__ == '__main__':
    AIAppManager().run()
