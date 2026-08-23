#!/bin/bash

IMAGE_NAME="$1"
REPO_URL="$2"

if [ -z "$IMAGE_NAME" ] || [ -z "$REPO_URL" ]; then
    echo "Usage: $0 <image_name> <repo_url>"
    exit 1
fi

DEPLOY_DIR="/opt/deployCode/$IMAGE_NAME"

# Make sure deploy directory exists
mkdir -p "$DEPLOY_DIR"

# Enter deploy directory
cd "$DEPLOY_DIR" || exit 1

# Initialize Git
git init

# Add repository
git remote add origin "$REPO_URL"

# Pull main branch
git pull origin main

echo "Repository successfully pulled into:"
echo "$DEPLOY_DIR"