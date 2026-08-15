# ============================================================
# Merged Dockerfile: FastAPI + Celery worker + Next.js frontend
# All three run in ONE container via supervisord, fronted by nginx
# on a single exposed $PORT (required for Render free tier).
#
# Everything is built on Debian (not Alpine) so the Python venv's
# compiled dependencies (numpy, pydantic-core, etc.) don't break
# from a glibc/musl mismatch.
# ============================================================

# ---------- Stage 1: build the Next.js frontend ----------
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_dummy
ARG NEXT_PUBLIC_API_URL=/api
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# ---------- Stage 2: build Python venv for backend/worker ----------
FROM python:3.10-slim AS python-builder
RUN apt-get update && apt-get install -y build-essential curl \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---------- Stage 3: final runtime image (Debian-based) ----------
FROM python:3.10-slim AS runtime

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

# ffmpeg for video processing, nginx + supervisor to run everything
# on one port, curl for healthchecks, gnupg/ca-certs for Node's apt repo
RUN apt-get update && apt-get install -y \
    ffmpeg curl nginx supervisor gnupg ca-certificates gettext-base \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Bring in the Python venv (compiled on the same Debian base — safe)
COPY --from=python-builder /opt/venv /opt/venv

# Backend + worker source code
WORKDIR /app/backend
COPY backend/ .

# Frontend: copy the production build output only (not source/devdeps)
WORKDIR /app/frontend
COPY --from=frontend-builder /frontend/.next ./.next
COPY --from=frontend-builder /frontend/node_modules ./node_modules
COPY --from=frontend-builder /frontend/package.json ./package.json
COPY --from=frontend-builder /frontend/public ./public

WORKDIR /app

# nginx + supervisord config (written below in the same chat response)
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY supervisord.conf /etc/supervisord.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 10000
ENV PORT=10000

ENTRYPOINT ["/entrypoint.sh"]
