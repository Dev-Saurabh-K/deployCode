#!/bin/bash
set -e

IMAGE_NAME="$1"
REPO_URL="$2"

if [ -z "$IMAGE_NAME" ] || [ -z "$REPO_URL" ]; then
    echo "Usage: $0 <image_name> <repo_url>"
    exit 1
fi

DEPLOY_DIR="/opt/deployCode/$IMAGE_NAME"

# Clean up any stale directory from previous failed runs
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

echo "Cloning repository: $REPO_URL into $DEPLOY_DIR"
# Clone the repository default branch (handles main, master, or any default branch)
git clone --depth 1 "$REPO_URL" "$DEPLOY_DIR"

# Check if package.json exists in root
if [ ! -f "$DEPLOY_DIR/package.json" ]; then
    echo "package.json not found in root, searching in subdirectories..."
    # Search for package.json in immediate subdirectories (e.g. client, frontend, web, app)
    SUBDIR=$(find "$DEPLOY_DIR" -maxdepth 2 -mindepth 2 -name "package.json" -not -path "*/.*/*" -exec dirname {} \; | head -n 1)
    
    if [ -n "$SUBDIR" ] && [ -d "$SUBDIR" ]; then
        echo "Found package.json in: $SUBDIR. Moving subfolder contents to deployment root."
        TEMP_STAGE=$(mktemp -d)
        shopt -s dotglob
        mv "$SUBDIR"/* "$TEMP_STAGE"/
        rm -rf "$DEPLOY_DIR"/*
        mv "$TEMP_STAGE"/* "$DEPLOY_DIR"/
        rmdir "$TEMP_STAGE"
        shopt -u dotglob
    else
        echo "Error: package.json not found in repository root or subfolders."
        exit 1
    fi
fi

echo "Repository successfully cloned and verified:"
echo "$DEPLOY_DIR"