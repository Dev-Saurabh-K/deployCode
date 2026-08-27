#!/bin/bash

APP_NAME="$1"

if [ -z "$APP_NAME" ]; then
    echo "Usage: $0 <app_name>"
    exit 1
fi

DEPLOY_DIR="/opt/deployCode/$APP_NAME"

echo "Removing deployment: $APP_NAME"

# Remove Nginx symlink
sudo rm -f "/etc/nginx/sites-enabled/$APP_NAME"

# Remove Nginx config
sudo rm -f "/etc/nginx/sites-available/$APP_NAME"

# Test and reload Nginx
if sudo nginx -t; then
    sudo systemctl reload nginx
else
    echo "ERROR: Nginx configuration test failed."
    exit 1
fi

# Docker Compose cleanup
if [ -f "$DEPLOY_DIR/docker-compose.yml" ]; then
    cd "$DEPLOY_DIR" || exit 1

    docker-compose down --rmi all --remove-orphans
else
    echo "docker-compose.yml not found in $DEPLOY_DIR"
fi

# Remove repository
if [ -d "$DEPLOY_DIR" ]; then
    rm -rf "$DEPLOY_DIR"
    echo "Removed: $DEPLOY_DIR"
else
    echo "Deployment directory not found: $DEPLOY_DIR"
fi

echo "Cleanup completed for $APP_NAME"