#!/bin/bash

IMAGE_NAME="$1"
PORT="$2"
USER_PORT="$3"
START_COMMAND="node app.js"

if [ -z "$IMAGE_NAME" ] || [ -z "$PORT" ] || [ -z "$USER_PORT" ]; then
    echo "Usage: $0 <image_name> <port> <user_port> [start_command] [KEY=VALUE ...]"
    exit 1
fi

if [ "$#" -ge 4 ] && [[ "$4" != *=* ]]; then
    START_COMMAND="$4"
    shift 4
else
    shift 3
fi

DEPLOY_DIR="/opt/deployCode/$IMAGE_NAME"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"
ENV_FILE="$DEPLOY_DIR/.env"

if [ ! -f "$DEPLOY_DIR/Dockerfile" ]; then
    echo "Error: Dockerfile not found in $DEPLOY_DIR"
    exit 1
fi

: > "$ENV_FILE"
printf 'START_COMMAND=%s\n' "$START_COMMAND" >> "$ENV_FILE"

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
    command: ["sh", "-c", "$START_COMMAND"]
    container_name: $IMAGE_NAME
    ports:
      - "$PORT:$USER_PORT"
    env_file:
      - .env
    restart: always
EOF

echo "docker-compose.yml created:"
echo "$COMPOSE_FILE"