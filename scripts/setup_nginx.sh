#!/bin/bash

IMAGE_NAME="$1"
PORT="$2"

if [ -z "$IMAGE_NAME" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <image_name> <port>"
    exit 1
fi

CONFIG_FILE="/etc/nginx/sites-available/${IMAGE_NAME}.conf"
LINK_FILE="/etc/nginx/sites-enabled/${IMAGE_NAME}.conf"

# Create Nginx configuration
cat > "$CONFIG_FILE" <<EOF
server {
    listen 80;
    server_name ${IMAGE_NAME}.dev-saurabh-k.xyz;

    location / {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_buffering off;

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

echo "Created: $CONFIG_FILE"

# Create symbolic link
ln -sf "$CONFIG_FILE" "$LINK_FILE"

echo "Enabled: $LINK_FILE"

# Test Nginx configuration
nginx -t

if [ $? -ne 0 ]; then
    echo "Nginx configuration test failed."
    exit 1
fi

# Reload Nginx
systemctl reload nginx

echo "Nginx reloaded successfully."
echo "Application: $IMAGE_NAME"
echo "Port: $PORT"
echo "Domain: ${IMAGE_NAME}.dev-saurabh-k.xyz"