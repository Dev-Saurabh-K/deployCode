#!/bin/bash

IMAGE_NAME="$1"
PORT="$2"

if [ -z "$IMAGE_NAME" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <image_name> <port>"
    exit 1
fi

CONFIG_FILE="/etc/nginx/sites-available/${IMAGE_NAME}.conf"

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

echo "Nginx configuration created:"
echo "$CONFIG_FILE"