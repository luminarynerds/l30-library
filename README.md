# L30 Library System

L30 is an open-source Integrated Library System (ILS) for small and medium
libraries. Patron accounts, circulation, catalog, events, reading programs,
and more -- packaged as Docker containers that any library can run.

Licensed under AGPL-3.0. Try the [demo](https://demo.l30.org).

This repository is a source release for evaluation and contribution. It is
not a claim that every feature or deployment configuration has passed a
production-readiness audit. Review [KNOWN_ISSUES.md](KNOWN_ISSUES.md) before
using real patron data.

## What is in this repository

- **Backend API** (`backend/`): FastAPI + SQLAlchemy + PostgreSQL + Redis.
- **Frontend app** (`frontend/`): React + Vite + Tailwind.
- **Ops config** (`docker-compose.yml`, `nginx/`): containerized production-style runtime.

## Documentation

Start with the [documentation guide](docs/README.md) to find material for
developers, library staff, administrators, and operators.

## Run a source installation

Clone the complete repository. The Docker build needs the backend, frontend,
nginx configuration, and initialization scripts; downloading only the
Compose and environment files is not sufficient.

Prerequisites: Git, Docker, and Docker Compose v2. For a public server, also
arrange a domain and HTTPS reverse proxy as described in [INSTALL.md](INSTALL.md).

```bash
git clone https://github.com/luminarynerds/l30-library.git
cd l30-library
./setup.sh --domain yourlibrary.example --email admin@yourlibrary.example --name "Your Library"
docker compose -f docker-compose.dist.yml up -d --build
```

Setup generates `.env` and `branding.json`. Keep `.env` private.
The first start builds the images from source and initializes a new database.
Do not use an existing library's database or volumes for an evaluation.

```bash
docker compose -f docker-compose.dist.yml ps
curl -f http://127.0.0.1:8081/health
```

Open `http://localhost:8081` for the setup wizard and create your first
administrator. The backend is accessed through this reverse proxy; the
distribution stack does not publish a separate API port.

See [INSTALL.md](INSTALL.md) for the full server setup,
[SELF_HOSTING.md](SELF_HOSTING.md) for operator configuration, and
[DEVELOPER_SETUP.md](DEVELOPER_SETUP.md) for contributor setup and tests.

## Local developer workflow (without Docker)

### Backend

```bash
cd backend
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite default URL is `http://localhost:5173`.

## Status

- Version: `0.1.0`
- License: AGPL-3.0
- Source release: October 24, 2026
