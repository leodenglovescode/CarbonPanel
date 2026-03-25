#!/bin/sh
set -eu

APP_PORT="${APP_PORT:-8787}"

cat > /etc/nginx/conf.d/default.conf <<EOF_CONF
server {
    listen ${APP_PORT};
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }
}
EOF_CONF

python -m alembic upgrade head
python -m app.scripts.seed_admin

uvicorn app.main:app --host 127.0.0.1 --port 8000 &

exec nginx -g 'daemon off;'
