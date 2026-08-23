#!/bin/bash

IMAGE_NAME="$1"
PORT="$2"

if [ -z "$IMAGE_NAME" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <image_name> <port>"
    exit 1
fi

DEPLOY_DIR="/opt/deployCode/$IMAGE_NAME"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"

if [ ! -f "$DEPLOY_DIR/Dockerfile" ]; then
    echo "Error: Dockerfile not found in $DEPLOY_DIR"
    exit 1
fi

cat > "$COMPOSE_FILE" <<EOF
services:
  $IMAGE_NAME:
    build: .
    container_name: $IMAGE_NAME
    ports:
      - "$PORT:80"
    restart: always
EOF

echo "docker-compose.yml created:"
echo "$COMPOSE_FILE"