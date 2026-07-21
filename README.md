# EventFlow

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/framework-Next.js-black.svg)](https://nextjs.org/)

A distributed workflow orchestration engine. EventFlow enables building, monitoring, and executing graph-based workflows across a cluster of workers with durable queues and state management.

EventFlow is designed as a foundational platform for reliable execution. It implements graph-based task routing, resilient retries, and state persistence, wrapped in a developer-friendly REST/gRPC API and accompanied by an elegant, editorial-style Next.js dashboard. 

## Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Design Philosophy](#design-philosophy)
- [Setup & Usage](#setup--usage)
- [Project Structure](#project-structure)

## Architecture

```text
               Client Request / Next.js Dashboard
                      │
                      ▼
            REST API (FastAPI Backend)
           │                        │
           ▼                        ▼
       PostgreSQL (State)       Redis (Queue)
                                    │
                      ┌─────────────┴─────────────┐
                      ▼                           ▼
                 Worker Node                 Worker Node
            (REST/gRPC Transport)         (REST/gRPC Transport)
```

The execution engine coordinates between the API and distributed workers using local Python interfaces, with support for configurable REST or gRPC transport layers.

## Tech Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, Alembic
- **Frontend:** Next.js, React, Tailwind CSS
- **Infrastructure:** PostgreSQL, Redis, Docker Compose
- **Transport:** REST, gRPC (Protobuf)

## Features

- **Graph-Based Workflows:** Define complex execution paths, conditions, and delays.
- **Distributed Execution:** Scale workers horizontally with durable Redis-backed queues.
- **Pluggable Transport:** Switch between REST and gRPC for internal worker-to-API communication.
- **Robust State Management:** PostgreSQL ensures reliable state tracking, retries, and Dead Letter Queues (DLQ).
- **Secure API:** Built-in API key authentication with hashed storage.
- **Premium Dashboard:** A beautiful, responsive Next.js application for monitoring workflows.

## Design Philosophy

The dashboard UI follows a **monochrome, editorial, and calm** design system inspired by typography-first aesthetics.

- **Minimalist & Typographic:** Hierarchy comes from type scale, weight, and generous whitespace — never from bright colors or gradients.
- **Tonal Layering:** Depth is achieved through subtle tonal shifts and hairline strokes, avoiding drop shadows or glassmorphism.
- **Semantic Geometry:** Workflow statuses are communicated primarily through geometric shapes (e.g., solid square for completed, hollow for queued), reserving color (`danger red`) exclusively for failed or critical states.

## Setup & Usage

The easiest way to get EventFlow up and running is to use Docker Compose, which spins up PostgreSQL, Redis, the REST API Backend, two Worker nodes, and the Next.js Frontend.

### 1. Configure Environment Variables
You need `.env` files in both `backend` and `frontend`. Use the provided examples to create them:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```
*(If you don't have `.env.local.example`, create `frontend/.env.local` containing: `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`)*

### 2. Start the Cluster
Run the following from the root directory:
```bash
docker compose up -d --build
```

### 3. Run Database Migrations
Once the database container is healthy and the backend is running, apply the Alembic database migrations:
```bash
docker compose exec backend alembic upgrade head
```

### 4. Create an API Key
Requests to the API must be authenticated with an API key sent in the `X-EventFlow-API-Key` header. Generate one inside the running backend container:
```bash
docker compose exec backend python scripts/create_api_key.py "my key name"
```
The raw key (prefixed `efk_`) is printed **once** — store it now, as only its hash is kept in the database.

### 5. Seed Demo Workflows
To test out the execution engine right away, you can use the seed script to populate the database with several ready-to-run demo workflows (including Linear, Condition, Delay, and Retry-to-DLQ workflows). The script creates its own owner API key and prints it once at the end.
```bash
docker compose exec backend python scripts/seed_demo_workflows.py
```

### 6. Open the Application
Navigate to [http://localhost:3000](http://localhost:3000) to access the EventFlow dashboard. 

### gRPC vs REST Transport
By default, the internal execution engine logic between the workers and the API runs using local Python interfaces / REST. To test EventFlow's internal **gRPC** transport mode:
1. Open `docker-compose.yml`
2. Change `EVENTFLOW_INTERNAL_TRANSPORT=local` to `EVENTFLOW_INTERNAL_TRANSPORT=grpc` in the `backend`, `worker-1`, and `worker-2` services.
3. Restart the cluster: `docker compose up -d`

## Project Structure

```text
  eventflow/
  ├── backend/                     # FastAPI backend and Python workers
  │   ├── alembic/                 # Database migrations
  │   ├── app/                     # API, Models, and Worker logic
  │   └── scripts/                 # DB Seeding and API key generation
  ├── frontend/                    # Next.js dashboard
  │   ├── src/                     # React components and pages
  │   └── public/                  # Static assets
  ├── proto/                       # gRPC protobuf definitions
  ├── docker-compose.yml           # Local cluster setup
  ├── DESIGN.md                    # UI/UX design system principles
  ├── LICENSE
  └── README.md
```

## License

MIT — see [LICENSE](LICENSE) for details.
