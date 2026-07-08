# AI Chatbot - Desktop to Android Migration

This repository contains a bilingual, speech-enabled AI Chatbot designed to help users prepare for placements. The application has been fully converted from a Tkinter desktop GUI to a modern, responsive, and lightweight **Kivy-based Android application**.

---

## 📂 Project Directory Structure & File Map

Here is the explanation of every directory and file in the project:

### 1. Root Directory Configurations
*   **[main.py](file:///c:/Users/lenovo/OneDrive/Documents/AI_Chatbot/main.py)**: The main entry point for the Kivy application. It initializes the screens, registers NLTK directories, sets up the Catppuccin themes (Mocha and Latte), and manages window transitions. Compatible with both Android and desktop test environments.
*   **[buildozer.spec](file:///c:/Users/lenovo/OneDrive/Documents/AI_Chatbot/buildozer.spec)**: The configuration file for Android packaging using Buildozer. It defines requirements (excluding TensorFlow for size optimization), permissions (Internet, Audio Recording), API targets, orientations, and build tools.
*   **[requirements.txt](file:///c:/Users/lenovo/OneDrive/Documents/AI_Chatbot/requirements.txt)**: Development dependencies required for local execution, training, and testing.

### 2. Assets Folder (`/assets`)
Shared static resources and runtime configuration files compiled for packaging:
*   **`chatbot_avatar.png` / `user_avatar.png`**: Rounded profile graphics displayed beside bot and user chat bubbles.
*   **`intents.json`**: Intent definitions containing pattern questions, response templates, and tag labels.
*   **`words.pkl` / `classes.pkl`**: Vocabulary tokens and class list extracted during training for Bag-of-Words mapping.
*   **`model_weights.json`**: A lightweight layer-by-layer weight and bias matrix extracted from the Keras model, enabling fast NumPy predictions on Android.

### 3. NLTK Data Folder (`/nltk_data`)
*   **`corpora/wordnet.zip`**: Database of english word mappings, loaded locally by Kivy to lemmatize words.
*   **`tokenizers/punkt/` / `punkt.zip`**: Local sentence tokenization resource parameters. Prepackaged to ensure the chatbot works offline.

### 4. Source Logic Folder (`/src`)
*   **`src/core/classifier.py`**: Handles cleaning, tokenization, lemmatization of queries, and feedforward neural network prediction using pure NumPy.
*   **`src/database/db_manager.py`**: Manages SQLite operations for user credentials and theme selections. On Android, it reads/writes safely inside `App.get_running_app().user_data_dir` to satisfy sandbox restrictions.
*   **`src/gui/screens.py`**: Declares mobile-optimized `LoginScreen` and `ChatScreen` classes.
*   **`src/gui/widgets.py`**: Houses custom drawing logic for widgets like `RoundCard`, `CircularAvatar`, `ChatBubble`, `ModernTextInput`, and `RoundButton`.
*   **`src/utils/logger.py`**: Performs thread-safe conversation history writes to `chat_history.txt` under local directories or Android private storage.
*   **`src/utils/speech.py`**: Contains the speech synthesis (TTS) and voice recognition (STT) interface. On Android, it leverages native APIs via Pyjnius (`TextToSpeech` and `RecognizerIntent`), falling back to `pyttsx3`/`SpeechRecognition` on Windows/Desktop.
*   **`src/utils/translation.py`**: Supports Hindi/English translation utilizing `deep-translator` and auto-language detection via Devanagari Unicode checks.

### 5. Legacy Desktop GUI (`/desktop`)
*   **`desktop/app.py`**: The original Tkinter desktop GUI, modified to run seamlessly from the sub-folder while sharing the database, logs, and assets.
*   **`desktop/chatbot.py`**: Command-line terminal interface and backend import module used by the Tkinter app.

### 6. Training Suite (`/training`)
*   **`training/train.py`**: Neural network training script that reads `assets/intents.json` and outputs a compiled model.
*   **`training/export_weights.py`**: Extracts weights and biases from the trained Keras model and dumps them to `assets/model_weights.json`.
*   **`training/chatbot_model.keras`**: The fully-trained TensorFlow Keras model file. Excluded from the Android package directory to prevent APK bloat.

---

## 🚀 Execution Instructions

### A. Run Kivy App (Local Desktop Mode)
Ensure you have the dependencies from `requirements.txt` and `Kivy` installed:
```bash
pip install -r requirements.txt
pip install kivy[base]
python main.py
```

### B. Run Legacy Desktop Tkinter GUI
To run the original Tkinter dashboard:
```bash
python desktop/app.py
```

### C. Retraining the Neural Network
If you change intent patterns inside `assets/intents.json`:
1.  Train the model to save the updated Keras weights:
    ```bash
    python training/train.py
    ```
2.  Export Keras weights to the mobile JSON format:
    ```bash
    python training/export_weights.py
    ```

---

## 🤖 Preparing and Building APK for Android (Buildozer)

Buildozer packages the Kivy app into a standalone `.apk` using Docker or a Linux environment (WSL is fully supported on Windows).

### 1. Prerequisites (on Ubuntu/Debian environment)
Install Android compiler requirements:
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libssl-dev cmake
pip3 install --user buildozer
```

### 2. Compilation and Deploy Commands
From the project root folder (containing `buildozer.spec`):
*   **Clean build caches**:
    ```bash
    buildozer android clean
    ```
*   **Compile the APK in debug mode**:
    ```bash
    buildozer android debug
    ```
    *The generated APK will be placed in the `bin/` directory.*
*   **Deploy, install, and run on a connected USB device**:
    ```bash
    buildozer android debug deploy run
    ```
*   **Stream debug logs from the device (helpful for logging Python traceback crashes)**:
    ```bash
    buildozer android logcat
    ```

### 3. Key Configurations in `buildozer.spec`
*   `requirements = python3, kivy==2.3.0, numpy, pillow, deep-translator, requests, urllib3, certifi, idna, charset-normalizer, beautifulsoup4, soupsieve, nltk`
*   `android.permissions = INTERNET, RECORD_AUDIO` (Required for translations and voice commands).
*   `source.include_patterns = assets/*, nltk_data/*, documents/*` (Ensures training code and `.keras` models are excluded, keeping the app lightweight at < 20MB).
