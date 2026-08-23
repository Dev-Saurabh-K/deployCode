#!/bin/bash

IMAGE_NAME="$1"

if [ -z "$IMAGE_NAME" ]; then
    echo "Usage: $0 <image_name>"
    exit 1
fi

DEPLOY_DIR="/opt/deployCode/$IMAGE_NAME"
UNIVERSAL_DOCKERFILE="deployCode/templates/Dockerfile"

#create deployment folder
mkdir -p "$DEPLOY_DIR"

#copy dockerfile
cp "$UNIVERSAL_DOCKERFILE" "$DEPLOY_DIR/Dockerfile"


#input--> IMAGE_NAME (foldername)