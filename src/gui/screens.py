# src/gui/screens.py
# Implements the mobile-optimized LoginScreen and ChatScreen screens.
# Integrates with the custom widgets, database manager, classifier, and speech engine.

import time
import threading
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window

from src.database.db_manager import login_user, register_user, get_user_theme, set_user_theme
from src.utils.translation import translate_text, is_hindi
from src.utils.speech import SpeechHandler
from src.utils.logger import log_chat_history
from src.core.classifier import chatbot_response

from src.gui.widgets import (
    RoundCard,
    CircularAvatar,
    ChatBubble,
    ModernTextInput,
    RoundButton,
    WidgetSpacer
)

class LoginScreen(Screen):
    """
    Polished Login and Signup portal, fully responsive for all screen sizes.
    """
    def __init__(self, app_root, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.app_root = app_root
        
        # Use ScrollView to prevent soft keyboard overlap clipping
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.add_widget(self.scroll)
        
        self.anchor = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_y=None)
        self.anchor.height = max(Window.height, dp(450))
        Window.bind(on_resize=self._update_anchor_height)
        
        # Inner centered card container
        self.card = RoundCard(
            bg_color=(0.118, 0.118, 0.180, 1), 
            orientation='vertical', 
            padding=dp(25), 
            spacing=dp(15), 
            size_hint=(None, None),
            height=dp(430)
        )
        
        # Bind card width responsively to screen size
        self.bind(width=self._update_card_width)
        
        # Title Header
        title = Label(
            text="AI Portal Login", 
            font_size='22sp', 
            bold=True, 
            color=(0.537, 0.705, 0.980, 1), 
            size_hint_y=None, 
            height=dp(40)
        )
        self.card.add_widget(title)
        
        # Username Input Section
        self.card.add_widget(Label(
            text="Username", 
            color=(0.803, 0.839, 0.956, 1), 
            halign='left', 
            font_size='14sp',
            size_hint_y=None, 
            height=dp(20), 
            text_size=(dp(280), None)
        ))
        
        self.username_input = ModernTextInput(
            bg_color=(0.192, 0.196, 0.266, 1),
            text_color=(0.803, 0.839, 0.956, 1),
            multiline=False, 
            write_tab=False,
            size_hint_y=None, 
            height=dp(42)
        )
        self.card.add_widget(self.username_input)
        
        # Password Input Section
        self.card.add_widget(Label(
            text="Password", 
            color=(0.803, 0.839, 0.956, 1), 
            halign='left', 
            font_size='14sp',
            size_hint_y=None, 
            height=dp(20), 
            text_size=(dp(280), None)
        ))
        
        self.password_input = ModernTextInput(
            bg_color=(0.192, 0.196, 0.266, 1),
            text_color=(0.803, 0.839, 0.956, 1),
            multiline=False, 
            password=True, 
            write_tab=False, 
            size_hint_y=None, 
            height=dp(42)
        )
        self.card.add_widget(self.password_input)
        
        # Error/Success Feedback Label
        self.status_label = Label(
            text="", 
            color=(0.952, 0.545, 0.658, 1), 
            font_size='13sp', 
            size_hint_y=None, 
            height=dp(25), 
            text_size=(dp(280), None), 
            halign='center'
        )
        self.card.add_widget(self.status_label)
        
        # Action Buttons Layout
        btn_box = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(45))
        
        login_btn = RoundButton(
            text="Log In", 
            bg_color=(0.650, 0.890, 0.631, 1), 
            text_color=(0.066, 0.066, 0.105, 1), 
            font_size='15sp', 
            bold=True, 
            size_hint_x=0.5
        )
        login_btn.bind(on_release=self.perform_login)
        btn_box.add_widget(login_btn)
        
        signup_btn = RoundButton(
            text="Sign Up", 
            bg_color=(0.537, 0.705, 0.980, 1), 
            text_color=(0.066, 0.066, 0.105, 1), 
            font_size='15sp', 
            bold=True, 
            size_hint_x=0.5
        )
        signup_btn.bind(on_release=self.perform_signup)
        btn_box.add_widget(signup_btn)
        
        self.card.add_widget(btn_box)
        
        self.anchor.add_widget(self.card)
        self.scroll.add_widget(self.anchor)
        
        # Bind background updates
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_card_width(self, instance, width):
        self.card.width = min(width - dp(40), dp(320))
        # Update text wrap boundaries on labels inside card
        for child in self.card.children:
            if isinstance(child, Label) and child != self.card.children[-1]: # Skip title
                child.text_size = (self.card.width - dp(30), None)

    def _update_anchor_height(self, instance, width, height):
        self.anchor.height = max(height, dp(450))

    def _update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # Mocha background
            Color(0.094, 0.094, 0.145, 1)
            RoundedRectangle(pos=self.pos, size=self.size)

    def perform_login(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        
        success, msg = login_user(username, password)
        if success:
            self.status_label.text = ""
            self.username_input.text = ""
            self.password_input.text = ""
            self.app_root.current_user = username.lower()
            self.app_root.current_theme = get_user_theme(username)
            self.app_root.load_chat_view()
        else:
            self.status_label.text = msg
            self.status_label.color = (0.952, 0.545, 0.658, 1)

    def perform_signup(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        
        success, msg = register_user(username, password)
        if success:
            self.status_label.text = msg
            self.status_label.color = (0.650, 0.890, 0.631, 1)
            self.password_input.text = ""
        else:
            self.status_label.text = msg
            self.status_label.color = (0.952, 0.545, 0.658, 1)


class ChatScreen(Screen):
    """
    Responsive conversational interface featuring chat histories, text translation triggers,
    and fallback TTS / STT speech interactions.
    """
    def __init__(self, app_root, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        self.app_root = app_root
        self.speech_handler = SpeechHandler()
        
        # Root vertical structure
        self.root_box = BoxLayout(orientation='vertical')
        self.add_widget(self.root_box)

    def setup_ui(self):
        self.root_box.clear_widgets()
        colors = self.app_root.theme_palette[self.app_root.current_theme]
        
        # Update main background canvas
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*colors["bg"])
            RoundedRectangle(pos=self.pos, size=self.size)

        # 1. Top status bar
        top_bar = BoxLayout(orientation='horizontal', padding=(dp(10), dp(8)), spacing=dp(8), size_hint_y=None, height=dp(60))
        
        user_lbl = Label(
            text=f"User: {self.app_root.current_user}", 
            color=colors["accent"], 
            font_size='14sp', 
            bold=True, 
            size_hint_x=0.35, 
            halign='left',
            valign='center'
        )
        user_lbl.bind(size=user_lbl.setter('text_size'))
        top_bar.add_widget(user_lbl)
        
        # Language Dropdown Button
        self.lang_mode = "Auto-Detect"
        self.lang_btn = RoundButton(
            text="Lang: Auto", 
            font_size='11sp', 
            bold=True, 
            bg_color=colors["entry_bg"], 
            text_color=colors["text"], 
            size_hint_x=0.25
        )
        
        dropdown = DropDown()
        for mode in ["Auto-Detect", "English", "Hindi"]:
            btn = Button(
                text=mode, 
                size_hint_y=None, 
                height=dp(48), 
                font_size='11sp', 
                background_color=colors["entry_bg"], 
                color=colors["text"]
            )
            btn.bind(on_release=lambda instance: dropdown.select(instance.text))
            dropdown.add_widget(btn)
            
        self.lang_btn.bind(on_release=dropdown.open)
        dropdown.bind(on_select=self.set_language_mode)
        top_bar.add_widget(self.lang_btn)
        
        # Theme Button
        theme_txt = "Theme: Sun" if self.app_root.current_theme == "dark" else "Theme: Moon"
        theme_btn = RoundButton(
            text=theme_txt, 
            font_size='11sp', 
            bold=True, 
            bg_color=colors["accent"], 
            text_color=(0.066, 0.066, 0.105, 1), 
            size_hint_x=0.22
        )
        theme_btn.bind(on_release=self.toggle_active_theme)
        top_bar.add_widget(theme_btn)
        
        # Logout Button
        logout_btn = RoundButton(
            text="Exit", 
            font_size='11sp', 
            bold=True, 
            bg_color=(0.952, 0.545, 0.658, 1), 
            text_color=(0.066, 0.066, 0.105, 1), 
            size_hint_x=0.18
        )
        logout_btn.bind(on_release=self.perform_logout)
        top_bar.add_widget(logout_btn)
        
        self.root_box.add_widget(top_bar)
 
        # 2. Scrollable conversation viewport
        self.scroll = ScrollView(
            size_hint=(1, 1),
            scroll_type=['content'],
            bar_width=dp(4),
            bar_inactive_color=(0.5, 0.5, 0.5, 0),
            bar_color=(0.5, 0.5, 0.5, 0.5)
        )
        self.chat_history_layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10), size_hint_y=None)
        self.chat_history_layout.bind(minimum_height=self.chat_history_layout.setter('height'))
        self.scroll.add_widget(self.chat_history_layout)
        self.root_box.add_widget(self.scroll)

        # 3. Message Input Panel
        bottom_bar = RoundCard(
            bg_color=colors["card_bg"], 
            radius=0, 
            orientation='horizontal', 
            padding=(dp(10), dp(10)), 
            spacing=dp(8), 
            size_hint_y=None, 
            height=dp(68)
        )
        
        self.message_input = ModernTextInput(
            bg_color=colors["entry_bg"],
            text_color=colors["text"],
            multiline=False, 
            write_tab=False, 
            hint_text="Type a message...",
            size_hint_x=0.58,
            font_size='14sp'
        )
        self.message_input.bind(on_text_validate=self.send_user_message)
        bottom_bar.add_widget(self.message_input)
        
        # Micro Speech Trigger
        self.speak_btn = RoundButton(
            text="🎙 Speak",
            font_size='12sp',
            bold=True,
            bg_color=colors["voice_btn"],
            text_color=(0.066, 0.066, 0.105, 1),
            size_hint_x=0.22
        )
        self.speak_btn.bind(on_release=self.trigger_listening_mode)
        bottom_bar.add_widget(self.speak_btn)
        
        # Send Trigger
        self.send_btn = RoundButton(
            text="Send",
            font_size='12sp',
            bold=True,
            bg_color=colors["send_btn"],
            text_color=(0.066, 0.066, 0.105, 1),
            size_hint_x=0.20
        )
        self.send_btn.bind(on_release=lambda instance: self.send_user_message())
        bottom_bar.add_widget(self.send_btn)
        
        self.root_box.add_widget(bottom_bar)

        # Display Greeting Message
        self.add_message_bubble("Hello! I am PythonBot. How can I help you prepare today? 😊", "Bot")

    def set_language_mode(self, instance, selection):
        self.lang_mode = selection
        lbl = selection.split("-")[0]
        self.lang_btn.text = f"Lang: {lbl}"

    def toggle_active_theme(self, instance):
        new_theme = "light" if self.app_root.current_theme == "dark" else "dark"
        self.app_root.current_theme = new_theme
        set_user_theme(self.app_root.current_user, new_theme)
        self.setup_ui()

    def perform_logout(self, instance):
        self.app_root.current_user = None
        self.app_root.sm.current = 'login'

    def add_message_bubble(self, text, sender):
        colors = self.app_root.theme_palette[self.app_root.current_theme]
        row = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, padding=(0, dp(4)))
        
        if sender == "You":
            avatar = CircularAvatar(image_path="user_avatar.png", fallback_letter="U", fallback_color=colors["accent"])
            bubble = ChatBubble(text=text, sender=sender, theme_colors=colors)
            
            row.add_widget(WidgetSpacer())
            row.add_widget(bubble)
            row.add_widget(avatar)
            
            log_chat_history(self.app_root.current_user, "You", text)
        else:
            avatar = CircularAvatar(image_path="chatbot_avatar.png", fallback_letter="B", fallback_color=(0.961, 0.761, 0.906, 1))
            bubble = ChatBubble(text=text, sender=sender, theme_colors=colors)
            
            row.add_widget(avatar)
            row.add_widget(bubble)
            row.add_widget(WidgetSpacer())
            
            log_chat_history(self.app_root.current_user, "Bot", text)

        # Bind bubble height updates directly to the row height dynamically
        row.height = bubble.height + dp(10)
        bubble.bind(height=lambda inst, val: setattr(row, 'height', val + dp(10)))

        self.chat_history_layout.add_widget(row)
        
        # Scroll to bottom
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

    def trigger_listening_mode(self, instance):
        self.message_input.disabled = True
        self.send_btn.disabled = True
        self.speak_btn.text = "Listening... ⏳"
        self.speak_btn.bg_color = (0.952, 0.545, 0.658, 1)

        lang = 'hi' if self.lang_mode == 'Hindi' else 'en'
        
        def on_speech_complete(result):
            self.message_input.disabled = False
            self.send_btn.disabled = False
            colors = self.app_root.theme_palette[self.app_root.current_theme]
            self.speak_btn.text = "🎙 Speak"
            self.speak_btn.bg_color = colors["voice_btn"]
            
            if "Voice input error" in result:
                self.add_message_bubble(result, "Bot")
            else:
                self.process_raw_query(result)

        self.speech_handler.listen_speech(lang, on_speech_complete)

    def send_user_message(self, *args):
        query = self.message_input.text.strip()
        if not query:
            return
        self.message_input.text = ""
        self.process_raw_query(query)

    def process_raw_query(self, query):
        self.message_input.disabled = True
        self.send_btn.disabled = True
        self.speak_btn.disabled = True
        
        self.add_message_bubble(query, "You")

        if self.lang_mode == "Auto-Detect":
            target_lang = "hi" if is_hindi(query) else "en"
        elif self.lang_mode == "Hindi":
            target_lang = "hi"
        else:
            target_lang = "en"

        typing_text = "बॉट टाइप कर रहा है... 🤔" if target_lang == "hi" else "Bot is typing... 🤔"
        
        colors = self.app_root.theme_palette[self.app_root.current_theme]
        row_typing = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, padding=(0, dp(4)))
        avatar = CircularAvatar(image_path="chatbot_avatar.png", fallback_letter="B", fallback_color=(0.961, 0.761, 0.906, 1))
        bubble = ChatBubble(text=typing_text, sender="Bot", theme_colors=colors)
        
        bubble.msg_label.italic = True
        
        row_typing.add_widget(avatar)
        row_typing.add_widget(bubble)
        row_typing.add_widget(WidgetSpacer())
        
        row_typing.height = bubble.height + dp(10)
        bubble.bind(height=lambda inst, val: setattr(row_typing, 'height', val + dp(10)))
        
        self.chat_history_layout.add_widget(row_typing)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

        def _async_process():
            processed_query = query
            if target_lang == "hi":
                processed_query = translate_text(query, source="hi", target="en")

            try:
                raw_response, tag = chatbot_response(processed_query)
            except Exception as e:
                raw_response, tag = f"Inference error: {e} ❌", "error"

            final_response = raw_response
            if target_lang == "hi" and tag != "error":
                final_response = translate_text(raw_response, source="en", target="hi")

            # Hold thread to let the typing indicator show for exactly 1.5 seconds
            time.sleep(1.5)

            def _on_done(dt):
                self.chat_history_layout.remove_widget(row_typing)
                self.add_message_bubble(final_response, "Bot")
                self.speech_handler.speak(final_response, target_lang)
                
                self.message_input.disabled = False
                self.send_btn.disabled = False
                self.speak_btn.disabled = False
                self.message_input.focus = True

            Clock.schedule_once(_on_done, 0)

        threading.Thread(target=_async_process, daemon=True).start()
