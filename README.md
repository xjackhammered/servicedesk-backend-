# ServiceDesk – Real-Time Service Request Management

A full-stack web application where **operators submit service requests** and **supervisors monitor them in real time**. Requests are processed concurrently by background workers, and every status or progress change is pushed to connected users over **WebSockets** (no polling).

> Built for the "Design and Develop a Real-Time Service Request Management System" assignment.

## Contents

* [Features](#features)
* [Architecture overview](#architecture-overview)
* [Technology stack](#technology-stack)
* [Repository structure](#repository-structure)
* [Setup and run](#setup-and-run)
* [Demo walkthrough](#demo-walkthrough)
* [Tests](#tests)
* [API documentation](#api-documentation)
* [WebSocket events](#websocket-events)
* [Database setup](#database-setup)
* [Configuration](#configuration)
* [Assumptions](#assumptions)
* [Known limitations](#known-limitations)
* [Documentation index](#documentation-index)

## Features

* **Roles:** operators create and follow requests; supervisors oversee the requests assigned to them
* **Automatic assignment** of each request to the least-loaded supervisor
* **Concurrent background processing** with staged, live progress (Celery workers)
* **Real-time UI** over WebSockets: status, progress, toasts, connection indicator
* **Search, filter, sort, paginate**, live status counts
* **Cancel and retry** with enforced rules; status history for every request
* **Self-healing:** stalled or undelivered jobs are detected and recovered automatically
* **Responsive** interface (phone, tablet, desktop), automatic dark mode
* **29 automated backend tests**, Docker Compose for infrastructure

## Architecture overview

```
 Browser (React SPA) ──REST/JSON──►  Django API (DRF, function-based views)
        ▲   ▲                                  │
        │   └──WebSocket──◄  Channels          ▼
        │                                 Service layer ──► PostgreSQL (source of truth)
        │                                   │       │
        │                       enqueue after       publish after
        │                          commit             commit
        │                             ▼                 ▼
        │                    Redis (broker)     Redis (channel layer)
        │                             │                 │
        │                      Celery workers ──────────┘
        └──── events ────────────────┘ (progress, status)         Celery beat → recovery sweeper
```

How a request flows:

1. The operator submits the form. The API validates it, saves it as `PENDING`, assigns a supervisor, and returns `201` immediately.
2. After the database commit, a Celery task is queued and a `request.created` event is pushed.
3. A worker **claims** the request with an atomic conditional update (`PENDING` to `PROCESSING`), then runs five stages, saving progress and a heartbeat after each one. Each change is announced over WebSocket.
4. The request ends as `COMPLETED` or `FAILED`. Cancelling a running request makes the worker stop at its next update.
5. A sweeper (Celery beat, every 30 s) re-queues requests whose worker died, and re-sends requests that never reached the queue.

Detailed diagrams (architecture, components, ERD, state machine, WebSocket sequence) are in [docs/02-system-design.md](docs/02-system-design.md).

## Technology stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Django 5, Django REST Framework (function-based views), SimpleJWT |
| Real-time | Django Channels, Daphne (ASGI), Redis channel layer |
| Background work | Celery 5 with Redis broker, Celery beat |
| Database | PostgreSQL 16 (SQLite only for tests) |
| Frontend | React 18, Vite, React Router, Context + `useReducer` |
| Infrastructure | Docker Compose (PostgreSQL, Redis) |

Why these choices is explained in [docs/02-system-design.md](docs/02-system-design.md#29-technology-stack-and-justification).

## Repository structure

```
servicedesk/
├── README.md                  this file
├── docker-compose.yml         PostgreSQL + Redis
├── docs/
│   ├── 01-system-analysis.md  problem, users, assumptions, scope, requirements
│   ├── 02-system-design.md    architecture, components, ERD, WebSocket flow, concurrency
│   └── 03-api-reference.md    REST endpoints and WebSocket events with examples
├── backend/                   Django project (see backend/README.md)
│   ├── config/                settings, urls, asgi, celery
│   └── apps/                  accounts, service_requests
└── frontend/                  React app (see frontend/README.md)
    └── src/
```

## Setup and run

### Prerequisites

* Python 3.11 or newer
* Node.js 18 or newer and npm
* Docker with Docker Compose (for PostgreSQL and Redis)

### 1. Start the infrastructure

From the repository root:

```bash
docker compose up -d
docker compose ps          # both services should be "running" / "healthy"
```

PostgreSQL is published on host port **5433** (to avoid clashing with a local PostgreSQL on 5432). Redis uses 6379.

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                   # defaults match docker-compose.yml
python manage.py migrate
python manage.py seed_demo             # creates sup1, sup2, op1, op2 (password: demo12345)
python manage.py runserver             # API + WebSockets on http://localhost:8000
```

### 3. Background worker and scheduler (two more terminals, same virtualenv)

```bash
cd backend && source .venv/bin/activate
celery -A config worker -l info --concurrency=4
```
```bash
cd backend && source .venv/bin/activate
celery -A config beat -l info
```

The worker processes requests. Beat runs the recovery sweeper every 30 seconds.

### 4. Frontend

```bash
cd frontend
cp .env.example .env                   # VITE_API_URL=http://localhost:8000
npm install
npm run dev                            # http://localhost:5173
```

Production build: `npm run build` (output in `frontend/dist/`).

### Summary: five processes

| # | Process | Command (from) |
|---|---|---|
| 1 | PostgreSQL + Redis | `docker compose up -d` (root) |
| 2 | Django API + WebSockets | `python manage.py runserver` (backend) |
| 3 | Celery worker | `celery -A config worker -l info --concurrency=4` (backend) |
| 4 | Celery beat | `celery -A config beat -l info` (backend) |
| 5 | React dev server | `npm run dev` (frontend) |

### Demo accounts

| Username | Role | Password |
|---|---|---|
| `op1`, `op2` | operator | `demo12345` |
| `sup1`, `sup2` | supervisor | `demo12345` |

Create your own operator on the register page. Create extra supervisors in the Django admin (`python manage.py createsuperuser`, then `/admin/`, set **role = Supervisor**).

### Troubleshooting

| Symptom | Fix |
|---|---|
| `permission denied for schema public` on `migrate` | Using your own PostgreSQL 15+? Make your DB user the owner: `ALTER DATABASE servicedesk OWNER TO servicedesk;` |
| `address already in use` on port 5432 | Local PostgreSQL is running. The compose file already uses 5433; make sure `DB_PORT=5433` in `backend/.env` |
| Requests stay `PENDING` | The Celery worker is not running, or cannot reach Redis |
| UI shows "Reconnecting…" | The backend is not running, or `VITE_API_URL` is wrong |
| Browser blocks API calls (CORS) | Add your frontend origin to `CORS_ALLOWED_ORIGINS` in `backend/.env` |

## Demo walkthrough

1. Open two browser windows. Sign in as `op1` in one and as a supervisor in the other. Auto-assignment alternates between `sup1` and `sup2`, so submit a few requests until one is assigned to the supervisor you are signed in as.
2. Submit several requests quickly as `op1`. Watch both windows update live: the supervisor sees new requests arrive, progress bars move, toasts appear.
3. Cancel a pending request as the operator, and a processing request as the supervisor.
4. Set `SIMULATED_FAILURE_RATE=0.5` in `backend/.env` and restart the worker to see `FAILED`, then **Retry** as the supervisor.
5. Stop the Celery worker mid-job and wait about a minute: the sweeper re-queues the stalled request (visible in its history).
6. Stop the backend for a few seconds: the header shows **Reconnecting…**, then the page re-syncs when it returns.

## Tests

```bash
cd backend
DB_ENGINE=sqlite USE_INMEMORY_CHANNELS=True python manage.py test apps
```

29 tests, no PostgreSQL or Redis required. They cover:

* validation, error envelope, mass-assignment protection, role permissions
* role-based visibility (operators and supervisors cannot see each other's data)
* cancel and retry rules; status history
* exclusive claim, duplicate task delivery, stale-worker fencing, cooperative cancel
* stalled-job recovery, re-dispatch of undelivered jobs, broker outage handling
* WebSocket authentication and per-user event delivery

## API documentation

Complete reference with request and response examples: **[docs/03-api-reference.md](docs/03-api-reference.md)**

| Method and path | Purpose |
|---|---|
| `POST /api/auth/register/` | create an operator account |
| `POST /api/auth/login/` | obtain access and refresh tokens |
| `POST /api/auth/refresh/` | renew the access token |
| `GET /api/auth/me/` | current user and role |
| `GET /api/requests/` | list (filters: `status`, `priority`, `category`, `search`, `ordering`, `page`) |
| `POST /api/requests/` | create a request (operators) |
| `GET /api/requests/{id}/` | details |
| `GET /api/requests/{id}/history/` | status history |
| `GET /api/requests/stats/` | counts per status |
| `POST /api/requests/{id}/cancel/` | cancel |
| `POST /api/requests/{id}/retry/` | retry a failed request (supervisors) |
| `GET /api/health/` | liveness |

Errors always look like `{"error": {"code", "message", "details"}}`. A request you may not see returns `404`.

## WebSocket events

Connect to `ws://localhost:8000/ws/requests/?token=<access_token>`. Unauthenticated connections are closed with code `4401`.

| Event | When | Payload |
|---|---|---|
| `connection.ready` | after connecting | `{role}` |
| `request.created` | a request is submitted | `{request}` |
| `request.status_changed` | claim, completion, failure, cancel, retry, recovery | `{request}` |
| `request.progress` | after each processing stage | `{request}` |

Events go to the request's creator and its assigned supervisor. Details and examples: [docs/03-api-reference.md](docs/03-api-reference.md#34-websocket-events).

## Database setup

PostgreSQL runs from `docker-compose.yml` (database, user and password are all `servicedesk`, host port 5433). Django creates the schema:

```bash
python manage.py migrate
```

Three tables: `accounts_user`, `service_requests_servicerequest`, `service_requests_statushistory`. The ERD, constraints and indexes are in [docs/02-system-design.md](docs/02-system-design.md#25-database-design).

To use a PostgreSQL you installed yourself, set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` in `backend/.env` and make sure the user may create tables in the `public` schema. To run without PostgreSQL, set `DB_ENGINE=sqlite` (fine for tests and quick trials).

## Configuration

All settings come from `backend/.env` (template: `backend/.env.example`) and `frontend/.env` (template: `frontend/.env.example`).

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | dev values | Django basics (change the key outside development) |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | allowed frontend origins |
| `DB_*` | see `.env.example` | database connection |
| `CELERY_BROKER_URL`, `CHANNEL_LAYER_URL` | Redis db 0 and 1 | broker and WebSocket layer |
| `PROCESSING_STAGE_SECONDS` | 4 | seconds per stage (5 stages) |
| `SIMULATED_FAILURE_RATE` | 0.0 | chance each stage fails, for demos |
| `STALL_TIMEOUT_SECONDS` | 60 | no heartbeat for this long = worker considered dead |
| `REDISPATCH_AFTER_SECONDS` | 60 | resend a PENDING request never queued |
| `MAX_PROCESSING_RETRIES` | 2 | automatic re-queues before FAILED |
| `VITE_API_URL` (frontend) | `http://localhost:8000` | backend URL (WebSocket URL derived from it) |

## Assumptions

* The assignment does not say how work is completed, so processing is **simulated** with five timed stages. Only the worker moves a request to processing, completed or failed; humans cannot mark unfinished work as done.
* Requests are assigned **automatically** to the supervisor with the fewest active requests.
* **Visibility is role-based:** operators see their own requests, supervisors see those assigned to them.
* Customers do not log in; operators submit requests on their behalf.
* Supervisor accounts are created by an administrator. Public registration creates operators only.
* Priority is informational and does not reorder the queue.
* Single organization, single region, modern browser with WebSocket support.

The full list with consequences is in [docs/01-system-analysis.md](docs/01-system-analysis.md#14-assumptions).

## Known limitations

* No transactional outbox: a crash between database commit and queue publish is covered by the sweeper (delay up to about a minute) rather than a hard guarantee.
* Priority does not influence processing order.
* The WebSocket access token is passed in the URL; tokens are short-lived (30 minutes) and query strings should not be logged.
* No CI/CD or cloud deployment, and no frontend automated tests.

## Documentation index

| Document | Contents |
|---|---|
| [docs/01-system-analysis.md](docs/01-system-analysis.md) | Problem statement, objectives, users, assumptions, scope, functional and non-functional requirements, business rules, risks |
| [docs/02-system-design.md](docs/02-system-design.md) | Architecture and component diagrams, lifecycle, ERD, API design, WebSocket flow, concurrency model, technology justification, security, trade-offs |
| [docs/03-api-reference.md](docs/03-api-reference.md) | Endpoints, error format, WebSocket events, examples |
| [backend/README.md](backend/README.md) | Backend layout and commands |
| [frontend/README.md](frontend/README.md) | Frontend structure and real-time design |

## How this was built

I approached this project by first breaking down the business requirements and designing the system architecture, request lifecycle, and database structure. I built the application using Django REST Framework, React, PostgreSQL, Celery, Redis, and Django Channels.

I focused on making the system reliable and responsive, particularly around concurrent background processing, real-time updates, request cancellation, retries, and recovery from worker failures. I also wrote automated backend tests and documented the design decisions, trade-offs, and setup process.
