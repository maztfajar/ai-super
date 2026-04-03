#!/bin/bash
# AI SUPER ASSISTANT — Package Script
# Script to create a clean, ready-to-install package

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARENT_DIR="$(dirname "$DIR")"
BASE_DIR="$(basename "$DIR")"
OUTPUT_DIR="/home/maztfajar/Downloads/MENTAH"
mkdir -p "$OUTPUT_DIR"

NAME="ai-super-assistant"
VERSION="1.0"
FILE="$OUTPUT_DIR/${NAME}-ready-to-install.tar.gz"

echo -e "\033[0;36m━━━ Packaging AI SUPER ASSISTANT ━━━\033[0m"

# Ensure all scripts are executable before packaging
chmod +x "$DIR/install.sh" "$DIR/scripts/"*.sh

# Create the archive
# We rename the root folder from 'pitakonku' to 'ai-super-assistant' inside the tar
tar -czf "$FILE" \
    --exclude="*/venv" \
    --exclude="*/node_modules" \
    --exclude="*/.git" \
    --exclude="*/__pycache__" \
    --exclude="*/data/logs/*" \
    --exclude="*/data/uploads/*" \
    --exclude="*.db" \
    --exclude="*.log" \
    --exclude="frontend/dist" \
    --exclude="frontend/.next" \
    --transform "s|^$BASE_DIR|$NAME|" \
    -C "$PARENT_DIR" "$BASE_DIR"

if [ $? -eq 0 ]; then
    echo -e "\033[0;32m[✓] Success!\033[0m"
    echo -e "File location: \033[1;33m$FILE\033[0m"
    echo -e "Contents: Source code + updated install.sh (ready for new PC)"
else
    echo -e "\033[0;31m[✗] Packaging failed!\033[0m"
    exit 1
fi
