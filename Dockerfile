FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
RUN pip install --no-cache-dir -e .

COPY --from=frontend-build /frontend/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/start.sh /start.sh

RUN chmod +x /start.sh

EXPOSE 80
CMD ["/start.sh"]