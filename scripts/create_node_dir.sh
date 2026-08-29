#!/bin/bash

IMAGE_NAME="$1"

if [ -z "$IMAGE_NAME" ]; then
    echo "Usage: $0 <image_name>"
    exit 1
fi

DEPLOY_DIR="/opt/deployCode/$IMAGE_NAME"
UNIVERSAL_DOCKERFILE="/home/saurabh/deployCode/templates/nodeJS.Dockerfile"

mkdir -p "$DEPLOY_DIR"

cp "$UNIVERSAL_DOCKERFILE" "$DEPLOY_DIR/Dockerfile"
