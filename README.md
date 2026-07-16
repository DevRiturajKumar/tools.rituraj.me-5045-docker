# tools.rituraj.me

Flask-based Skills Dashboard - Docker deployment.

## Setup

1. Copy `.env.example` to `config.env`:
   ```bash
   cp .env.example config.env
   ```

2. Edit `config.env` with your credentials.

3. Build and run:
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

4. Verify:
   ```bash
   curl -s http://127.0.0.1:5045/health
   ```

## Environment Variables

See `.env.example` for all required config options.

## Architecture

- Flask with Gunicorn (4 workers)
- 2-step auth (password + TOTP)
- SSH → Docker exec for skill execution
- Designed for `network_mode: bridge`
- Read-only container with /tmp tmpfs

## Design

Uses the best-site-theme design language (emerald/teal gradients, dark mode, glassmorphism).
