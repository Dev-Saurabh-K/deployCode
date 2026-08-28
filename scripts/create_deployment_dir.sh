#!/bin/bash
set -e

IMAGE_NAME="$1"

if [ -z "$IMAGE_NAME" ]; then
    echo "Usage: $0 <image_name>"
    exit 1
fi

DEPLOY_DIR="/opt/deployCode/$IMAGE_NAME"
UNIVERSAL_DOCKERFILE="/home/saurabh/deployCode/templates/Dockerfile"
NGINX_CONFIG="/home/saurabh/deployCode/templates/nginx.conf"

# Ensure deployment folder exists
mkdir -p "$DEPLOY_DIR"

# Copy the build assets required by the universal Dockerfile.
cp "$UNIVERSAL_DOCKERFILE" "$DEPLOY_DIR/Dockerfile"
cp "$NGINX_CONFIG" "$DEPLOY_DIR/nginx.conf"

echo "Deployment assets copied to: $DEPLOY_DIR"
