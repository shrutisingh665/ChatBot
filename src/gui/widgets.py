# src/gui/widgets.py
# Contains customized and styled widgets used throughout the application.
# Includes RoundCard, CircularAvatar, ChatBubble, ModernTextInput, and RoundButton.

import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Ellipse
from kivy.metrics import dp
from kivy.core.window import Window

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

class RoundCard(BoxLayout):
    """
    Layout container that draws a rounded background card matching the active theme colors.
    """
    def __init__(self, bg_color, radius=dp(12), **kwargs):
        super(RoundCard, self).__init__(**kwargs)
        self.bg_color = bg_color
        self.radius = radius
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])


class CircularAvatar(BoxLayout):
    """
    Draws a cropped circular avatar image, falling back to initials if missing.
    """
    def __init__(self, image_path, fallback_letter, fallback_color, **kwargs):
        super(CircularAvatar, self).__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(40), dp(40))
        
        # Resolve path inside the assets folder if a relative file name was provided
        if not os.path.isabs(image_path):
            self.image_path = os.path.join(ASSETS_DIR, image_path)
        else:
            self.image_path = image_path
            
        self.fallback_letter = fallback_letter
        self.fallback_color = fallback_color
        self.bind(pos=self.draw_avatar, size=self.draw_avatar)

    def draw_avatar(self, *args):
        self.canvas.clear()
        if os.path.exists(self.image_path):
            with self.canvas:
                Color(1, 1, 1, 1)
                Ellipse(pos=self.pos, size=self.size, source=self.image_path)
        else:
            with self.canvas:
                Color(*self.fallback_color)
                Ellipse(pos=self.pos, size=self.size)
            self.clear_widgets()
            lbl = Label(
                text=self.fallback_letter, 
                font_size='15sp', 
                bold=True, 
                color=(0.1, 0.1, 0.1, 1),
                size=self.size,
                pos=self.pos
            )
            self.add_widget(lbl)


class ChatBubble(RoundCard):
    """
    A responsive message bubble that adjusts its size based on message length
    and wraps text at device boundaries.
    """
    def __init__(self, text, sender, theme_colors, **kwargs):
        if sender == "You":
            bg = theme_colors["user_bubble"]
            fg = theme_colors["user_bubble_fg"]
        else:
            bg = theme_colors["bot_bubble"]
            fg = theme_colors["bot_bubble_fg"]
            
        super(ChatBubble, self).__init__(bg_color=bg, orientation='vertical', padding=(dp(12), dp(10)), size_hint=(None, None), **kwargs)
        
        # Set max width to 70% of device screen width to look great on mobile/tablets
        max_width = min(Window.width * 0.70, dp(450))
        
        self.msg_label = Label(
            text=text, 
            color=fg, 
            font_size='14sp', 
            halign='left', 
            valign='top',
            size_hint=(None, None)
        )
        self.msg_label.bind(texture_size=self._update_bubble_size)
        self.add_widget(self.msg_label)
        
        # Wrap text constraints
        self.msg_label.text_size = (max_width - dp(24), None)

    def _update_bubble_size(self, instance, size):
        # Update text width/height based on text texture size
        self.msg_label.width = size[0]
        self.msg_label.height = size[1]
        
        # Bubble card encapsulates the text label with padding
        self.width = size[0] + dp(24)
        self.height = size[1] + dp(20)


class ModernTextInput(TextInput):
    """
    A styled TextInput with customized padding, placeholder, and rounded canvas backgrounds.
    """
    def __init__(self, bg_color, text_color, placeholder_color=(0.5, 0.5, 0.5, 1), radius=dp(8), **kwargs):
        super(ModernTextInput, self).__init__(**kwargs)
        self.padding = (dp(12), dp(10), dp(12), dp(10))
        self.background_active = ""
        self.background_normal = ""
        self.background_color = (0, 0, 0, 0)
        self.foreground_color = text_color
        self.hint_text_color = placeholder_color
        self.cursor_color = (0.537, 0.705, 0.980, 1) # Blue accent
        self.bg_color = bg_color
        self.radius = radius
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])


class RoundButton(Button):
    """
    A styled button with rounded corners and consistent padding.
    """
    def __init__(self, bg_color, text_color, radius=dp(8), **kwargs):
        super(RoundButton, self).__init__(**kwargs)
        self.background_active = ""
        self.background_normal = ""
        self.background_color = (0, 0, 0, 0)
        self.color = text_color
        self.bg_color = bg_color
        self.radius = radius
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])


class WidgetSpacer(BoxLayout):
    """
    Simple empty spacer to balance horizontal alignments of chat bubbles.
    """
    def __init__(self, **kwargs):
        super(WidgetSpacer, self).__init__(**kwargs)
        self.size_hint_x = 0.12
