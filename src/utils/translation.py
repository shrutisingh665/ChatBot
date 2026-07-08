# src/utils/translation.py
# Handles translations and language detection checks.

from deep_translator import GoogleTranslator

def translate_text(text, source='auto', target='en'):
    try:
        if not text.strip():
            return text
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception as e:
        print(f"Translation failed: {e}")
        return text

def is_hindi(text):
    for char in text:
        if '\u0900' <= char <= '\u097f':
            return True
    return False
