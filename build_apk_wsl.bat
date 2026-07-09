@echo off
REM build_apk_wsl.bat
REM Windows batch script to launch the build process inside WSL (Ubuntu).

echo ==========================================
echo [INFO] Running build_apk_wsl.sh inside WSL (Ubuntu)...
wsl bash build_apk_wsl.sh
if %errorlevel% neq 0 (
    echo [ERROR] WSL compilation failed.
    pause
    exit /b %errorlevel%
)
echo [SUCCESS] WSL build script completed successfully!
pause
