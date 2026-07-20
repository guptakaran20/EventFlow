# EventFlow

A distributed workflow orchestration engine. EventFlow enables building, monitoring, and executing graph-based workflows across a cluster of workers with durable queues and state management.

## Quick Start (Docker Compose)

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
Once the database container is healthy and the backend is running, apply the Alembic database migrations. You can execute this directly inside the running backend container:
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

## gRPC vs REST Transport
By default, the internal execution engine logic between the workers and the API runs using local Python interfaces / REST. 

To test EventFlow's internal **gRPC** transport mode:
1. Open `docker-compose.yml`
2. Change `EVENTFLOW_INTERNAL_TRANSPORT=local` to `EVENTFLOW_INTERNAL_TRANSPORT=grpc` in the `backend`, `worker-1`, and `worker-2` services.
3. Restart the cluster: `docker compose up -d`
