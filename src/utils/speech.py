# src/utils/speech.py
# Handles cross-platform Text-To-Speech (TTS) and Speech-To-Text (STT) operations.
# Employs native Android bindings on mobile and fallback speech APIs on desktop.

import os
import threading
import queue
from kivy.utils import platform
from kivy.clock import Clock

class SpeechHandler:
    def __init__(self):
        self.tts_engine = None
        self.speech_queue = queue.Queue()
        self.is_android = (platform == 'android')
        
        self.android_tts = None
        self.android_tts_ready = False
        self.activity_bound = False
        self.stt_callback = None
        
        if self.is_android:
            # Initialize Android TTS once
            self._init_android_tts()
        else:
            t = threading.Thread(target=self._init_desktop_tts)
            t.daemon = True
            t.start()

    def _init_android_tts(self):
        try:
            from jnius import PythonJavaClass, java_method, autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
            
            activity = PythonActivity.mActivity
            
            class TTSInitListener(PythonJavaClass):
                __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
                
                def __init__(self, handler):
                    super(TTSInitListener, self).__init__()
                    self.handler = handler
                    
                @java_method('(I)V')
                def onInit(self, status):
                    if status == TextToSpeech.SUCCESS:
                        self.handler.android_tts_ready = True
                        print("Android TTS initialized successfully!")
                    else:
                        print(f"Android TTS initialization failed with status: {status}")
            
            self.tts_listener = TTSInitListener(self)
            self.android_tts = TextToSpeech(activity, self.tts_listener)
        except Exception as e:
            print(f"Android TTS initialization failed: {e}")
            self.android_tts = None

    def _init_desktop_tts(self):
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 155)
            self._start_desktop_speech_worker()
        except Exception as e:
            print(f"Desktop speech synthesis load error: {e}")

    def _start_desktop_speech_worker(self):
        def _worker():
            while True:
                item = self.speech_queue.get()
                if item is None:
                    break
                text, lang_code = item
                try:
                    voices = self.tts_engine.getProperty('voices')
                    selected_voice = None
                    for voice in voices:
                        if lang_code == 'hi' and ('hindi' in voice.name.lower() or 'hi' in voice.id.lower()):
                            selected_voice = voice.id
                            break
                        elif lang_code == 'en' and ('english' in voice.name.lower() or 'en' in voice.id.lower()):
                            selected_voice = voice.id
                    if selected_voice:
                        self.tts_engine.setProperty('voice', selected_voice)
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except Exception as ex:
                    print(f"Desktop TTS play error: {ex}")
                self.speech_queue.task_done()
                
        threading.Thread(target=_worker, daemon=True).start()

    def speak(self, text, lang_code):
        if self.is_android:
            if self.android_tts and self.android_tts_ready:
                try:
                    from jnius import autoclass
                    Locale = autoclass('java.util.Locale')
                    locale = Locale.HINDI if lang_code == 'hi' else Locale.US
                    self.android_tts.setLanguage(locale)
                    # 0 corresponds to TextToSpeech.QUEUE_FLUSH
                    self.android_tts.speak(text, 0, None)
                except Exception as e:
                    print(f"Android TTS speak error: {e}")
            else:
                print("Android TTS is not ready or failed to initialize.")
        else:
            if self.tts_engine:
                self.speech_queue.put((text, lang_code))

    def listen_speech(self, lang_code, callback):
        """
        Listens to user voice input. Handled on Desktop using SpeechRecognition.
        Android voice triggers use native RecognizerIntent via Pyjnius.
        """
        if self.is_android:
            try:
                from android import activity
                from jnius import autoclass
                
                Intent = autoclass('android.content.Intent')
                RecognizerIntent = autoclass('android.speech.RecognizerIntent')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                
                if not self.activity_bound:
                    activity.bind(on_activity_result=self._on_activity_result)
                    self.activity_bound = True
                
                self.stt_callback = callback
                
                intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                lang = 'hi-IN' if lang_code == 'hi' else 'en-US'
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, lang)
                intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                
                PythonActivity.mActivity.startActivityForResult(intent, 1000)
            except Exception as e:
                callback(f"Android Voice input error: {e} ❌")
            return

        # Desktop execution fallback
        def _recognize():
            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                rec_lang = "hi-IN" if lang_code == 'hi' else "en-US"
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.8)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                recognized_text = recognizer.recognize_google(audio, language=rec_lang)
                Clock.schedule_once(lambda dt: callback(recognized_text), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(f"Voice input error: {e} ❌"), 0)

        threading.Thread(target=_recognize, daemon=True).start()

    def _on_activity_result(self, request_code, result_code, intent):
        if request_code == 1000:
            try:
                from jnius import autoclass
                Activity = autoclass('android.app.Activity')
                RecognizerIntent = autoclass('android.speech.RecognizerIntent')
                
                if result_code == Activity.RESULT_OK and intent is not None:
                    results = intent.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                    if results and results.size() > 0:
                        recognized_text = results.get(0)
                        if self.stt_callback:
                            Clock.schedule_once(lambda dt: self.stt_callback(recognized_text), 0)
                    else:
                        if self.stt_callback:
                            Clock.schedule_once(lambda dt: self.stt_callback("Voice input error: No speech detected ❌"), 0)
                else:
                    if self.stt_callback:
                        Clock.schedule_once(lambda dt: self.stt_callback("Voice input error: Cancelled or failed ❌"), 0)
            except Exception as e:
                if self.stt_callback:
                    Clock.schedule_once(lambda dt: self.stt_callback(f"Voice input error: {e} ❌"), 0)
