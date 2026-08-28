#!/bin/bash

IMAGE_NAME="$1"
PORT="$2"

if [ -z "$IMAGE_NAME" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <image_name> <port> [KEY=VALUE ...]"
    exit 1
fi

shift 2

DEPLOY_DIR="/opt/deployCode/$IMAGE_NAME"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"
ENV_FILE="$DEPLOY_DIR/.env"

if [ ! -f "$DEPLOY_DIR/Dockerfile" ]; then
    echo "Error: Dockerfile not found in $DEPLOY_DIR"
    exit 1
fi

# Each remaining argument must be a KEY=VALUE environment variable. Docker
# Compose loads this deployment-local file through the env_file setting below.
: > "$ENV_FILE"
for ENV_VAR in "$@"; do
    if [[ "$ENV_VAR" != *=* ]]; then
        echo "Error: environment variables must use KEY=VALUE format"
        exit 1
    fi

    ENV_KEY="${ENV_VAR%%=*}"
    ENV_VALUE="${ENV_VAR#*=}"
    if [[ ! "$ENV_KEY" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
        echo "Error: invalid environment variable name: $ENV_KEY"
        exit 1
    fi

    if [[ "$ENV_VALUE" == *$'\n'* || "$ENV_VALUE" == *$'\r'* ]]; then
        echo "Error: environment variable values cannot contain newlines"
        exit 1
    fi

    printf '%s=%s\n' "$ENV_KEY" "$ENV_VALUE" >> "$ENV_FILE"
done

cat > "$COMPOSE_FILE" <<EOF
services:
  $IMAGE_NAME:
    build: .
    container_name: $IMAGE_NAME
    ports:
      - "$PORT:80"
    env_file:
      - .env
    restart: always
EOF

echo "docker-compose.yml created:"
echo "$COMPOSE_FILE"

#2nd file
