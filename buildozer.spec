# buildozer.spec
# Configuration file for compilation parameters of Kivy Android apps using Buildozer.

[app]

# (str) Title of your application
title = AI Assistant

# (str) Package name
package.name = aiplacementassistant

# (str) Package domain (needed for android packaging)
package.domain = org.placement.prep

# (str) Source code directory
source.dir = .

# (list) Source files to include (comma separated)
source.include_exts = py,png,jpg,json,txt,db,pkl,zip,pickle

# (list) List of directory patterns to include (comma separated)
source.include_patterns = assets/*, nltk_data/*, documents/*

# (list) List of directory patterns to exclude (comma separated)
exclude_dirs = desktop, training, .git, .github

# (str) Application versioning
version = 1.0

# (list) Application requirements
# Note: TensorFlow is omitted and replaced by pure NumPy weight inference, 
# resulting in extremely lightweight builds (< 20MB) and guaranteed stability.
requirements = python3,kivy==2.3.0,android,pyjnius,numpy,pillow,deep-translator,requests,urllib3,certifi,idna,charset-normalizer,beautifulsoup4,soupsieve,nltk

# (str) Supported orientations (one of landscape, portrait or all)
orientation = portrait

# (bool) Use Android full screen mode (hides navigation and status bar)
fullscreen = 0

# (list) Permissions required by the application
android.permissions = INTERNET, RECORD_AUDIO

# (int) Target Android API level (SDK)
android.api = 33

# (int) Minimum Android API level
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25c

# (bool) If True, then skip trying to update the Android sdk extra packages
android.skip_update = False

# (bool) If True, then automatically accept SDK licenses
android.accept_sdk_license = True

# (str) Android entry point (main Kivy execution script name)
android.entrypoint = main

# (str) Icon file mapping
icon.filename = %(source.dir)s/assets/chatbot_avatar.png

# (str) Presplash screen mapping
presplash.filename = %(source.dir)s/assets/user_avatar.png

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug and stdout)
log_level = 2

# (int) Display warning alerts (0 = none, 1 = normal, 2 = strict)
warn_on_root = 1
