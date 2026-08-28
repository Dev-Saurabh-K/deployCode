#!/bin/bash
set -e

IMAGE_NAME="$1"
REPO_URL="$2"

if [ -z "$IMAGE_NAME" ] || [ -z "$REPO_URL" ]; then
    echo "Usage: $0 <image_name> <repo_url>"
    exit 1
fi

DEPLOY_DIR="/opt/deployCode/$IMAGE_NAME"

# Check if repository is public and accessible
export GIT_TERMINAL_PROMPT=0
if ! git ls-remote -h "$REPO_URL" > /dev/null 2>&1; then
    echo "ERROR: Repository is private or does not exist. You must provide a public GitHub repository link." >&2
    exit 1
fi

# Make sure deploy directory exists
mkdir -p "$DEPLOY_DIR"

# Enter deploy directory
cd "$DEPLOY_DIR" || exit 1

# Initialize Git
git init
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

# Pull main branch
git pull origin main

echo "Repository successfully pulled into: $DEPLOY_DIR"