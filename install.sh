#!/usr/bin/env bash
set -e

TARGET_DIR="$HOME/instagram-reel-counter"
echo "⚡ Installing Instagram Reel Counter..."

# Check Python
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
else
    echo "❌ Python is not installed. Please install Python 3.10+ first."
    exit 1
fi

# Clone or download
if [ -d "$TARGET_DIR/.git" ]; then
    cd "$TARGET_DIR"
    command -v git >/dev/null 2>&1 && git pull --quiet || true
elif command -v git >/dev/null 2>&1; then
    echo "📥 Cloning repository..."
    git clone --quiet https://github.com/prashanth-karanam/instagram-reel-counter.git "$TARGET_DIR"
    cd "$TARGET_DIR"
else
    echo "📥 Fetching archive..."
    mkdir -p "$TARGET_DIR"
    curl -sSL https://github.com/prashanth-karanam/instagram-reel-counter/archive/refs/heads/main.tar.gz | tar -xz -C "$TARGET_DIR" --strip-components=1
    cd "$TARGET_DIR"
fi

# Dependencies
echo "📦 Installing dependencies..."
$PY_CMD -m pip install --quiet --upgrade pip || true
$PY_CMD -m pip install --quiet -r requirements.txt

# Launch
echo "🚀 Launching toolkit..."
$PY_CMD app.py
