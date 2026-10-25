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

NEEDS_FETCH=true

if [ -d "$TARGET_DIR/.git" ] && [ -f "$TARGET_DIR/app.py" ]; then
    cd "$TARGET_DIR"
    command -v git >/dev/null 2>&1 && git pull --quiet || true
    NEEDS_FETCH=false
elif [ -d "$TARGET_DIR" ] && [ ! -f "$TARGET_DIR/app.py" ]; then
    rm -rf "$TARGET_DIR"
fi

if [ "$NEEDS_FETCH" = true ]; then
    CLONED=false
    if command -v git >/dev/null 2>&1; then
        echo "📥 Cloning repository..."
        if git clone --quiet https://github.com/prashanth-karanam/instagram-reel-counter.git "$TARGET_DIR" 2>/dev/null; then
            CLONED=true
        fi
    fi

    if [ "$CLONED" = false ]; then
        echo "📥 Fetching archive..."
        mkdir -p "$TARGET_DIR"
        curl -sSL https://github.com/prashanth-karanam/instagram-reel-counter/archive/refs/heads/main.tar.gz | tar -xz -C "$TARGET_DIR" --strip-components=1
    fi
fi

if [ ! -f "$TARGET_DIR/app.py" ]; then
    echo "❌ Error: Could not locate app.py in $TARGET_DIR"
    exit 1
fi

cd "$TARGET_DIR"

# Dependencies
echo "📦 Installing dependencies..."
$PY_CMD -m pip install --quiet --upgrade pip || true
$PY_CMD -m pip install --quiet instagrapi rich requests

# Launch
echo "🚀 Launching toolkit..."
$PY_CMD "$TARGET_DIR/app.py"
