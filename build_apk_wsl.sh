#!/bin/bash
# build_apk_wsl.sh
# Installation and compilation script designed to run inside WSL (Ubuntu).

set -e

echo "=========================================="
echo "[INFO] Updating WSL package listings..."
sudo apt update

echo "[INFO] Installing required dependencies..."
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libssl-dev cmake

echo "[INFO] Upgrading pip and installing Buildozer/Cython..."
pip3 install --user --upgrade pip
pip3 install --user buildozer cython==0.29.36

# Add path to current terminal shell environment
export PATH="$HOME/.local/bin:$PATH"

echo "[INFO] Cleaning old compilation caches..."
buildozer android clean

echo "[INFO] Packaging Android APK in debug mode..."
buildozer android debug

echo "[SUCCESS] Build finished! Check the 'bin/' folder."
