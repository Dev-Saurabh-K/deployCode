from pathlib import Path

def create_nginx_config(app_name, domain, port):
    config = f"""
server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:{port};

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

    path = Path(f"/etc/nginx/sites-available/{app_name}.conf")
    path.write_text(config)

    return path