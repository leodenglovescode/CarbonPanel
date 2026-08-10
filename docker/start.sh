#!/bin/sh
set -eu

APP_PORT="${APP_PORT:-8787}"
# This legacy entrypoint must sit behind a TLS-terminating proxy.
# Direct HTTP is intentionally not a supported authentication path.
export COOKIE_SECURE="${COOKIE_SECURE:-true}"

cat > /etc/nginx/conf.d/default.conf <<EOF_CONF
map \$http_x_forwarded_proto \$cp_forwarded_proto {
    default \$http_x_forwarded_proto;
    "" \$scheme;
}

server {
    listen ${APP_PORT};
    root /usr/share/nginx/html;
    index index.html;
    server_tokens off;
    client_max_body_size 22m;

    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob: https:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'" always;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$cp_forwarded_proto;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$http_host;
        proxy_set_header X-Forwarded-Proto \$cp_forwarded_proto;
        proxy_read_timeout 86400;
    }
}
EOF_CONF

python -m alembic upgrade head
python -m app.scripts.seed_admin

uvicorn app.main:app --host 127.0.0.1 --port 8000 &

exec nginx -g 'daemon off;'
