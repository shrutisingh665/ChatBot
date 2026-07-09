@echo off
REM build_apk_docker.bat
REM Windows batch script to automate Buildozer packaging via Docker container.

echo ==========================================
REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running or not found.
    echo Please make sure Docker Desktop is launched and active.
    pause
    exit /b %errorlevel%
)

echo [INFO] Building the Buildozer build environment image...
echo This will take a few minutes on the first execution.
docker build -t buildozer-image -f Dockerfile.buildozer .
if %errorlevel% neq 0 (
    echo [ERROR] Docker image build failed.
    pause
    exit /b %errorlevel%
)

echo [INFO] Compiling Android APK in debug mode...
echo The project directory will be mounted inside the container.
docker run --rm -v "%cd%":/home/builder/app buildozer-image
if %errorlevel% neq 0 (
    echo [ERROR] Buildozer compilation failed.
    pause
    exit /b %errorlevel%
)

echo [SUCCESS] APK built successfully! Check the 'bin/' directory.
pause
