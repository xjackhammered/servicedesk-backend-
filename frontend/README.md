# ServiceDesk – Frontend (React + Vite)

Live dashboard for the ServiceDesk backend. Operators submit and track requests; supervisors monitor
the requests assigned to them. Status and progress update in real time over WebSockets (no polling).

## Quick start

```bash
cp .env.example .env     # VITE_API_URL=http://localhost:8000
npm install
npm run dev              # http://localhost:5173
```

The backend must be running first (see the backend README). Demo logins after `python manage.py seed_demo`:
`op1` / `op2` (operators) and `sup1` / `sup2` (supervisors), password `demo12345`.

Production build: `npm run build` (output in `dist/`), preview with `npm run preview`.

## Features

* Sign in / register (operators), JWT with silent token refresh
* Role-based UI: operators submit and cancel their pending requests; supervisors monitor, cancel and retry failed ones
* Dashboard with live status counts, search, status/priority/category filters, pagination
* Request detail with live progress bar, current stage, result/error and status history timeline
* Form validation on the client (mirrors backend rules) plus server errors mapped onto fields
* Toast notifications on live status changes; connection indicator (Live / Reconnecting / Offline)
* Responsive layout (desktop, tablet, phone) and automatic dark mode

## Structure

```
src/
├── api/
│   ├── client.js           fetch wrapper: JWT, auto-refresh, error envelope -> ApiError
│   └── endpoints.js        one function per REST endpoint
├── context/
│   ├── AuthContext.jsx     current user, signIn / signOut
│   ├── RequestsContext.jsx real-time store: WebSocket + reducer (byId map, version counter)
│   └── ToastContext.jsx    notifications
├── components/             Layout, RequestCard, Filters, StatsBar, ProgressBar, ...
├── pages/                  Login, Register, Dashboard, NewRequest, RequestDetail
├── utils/                  validation.js, format.js
└── constants.js            statuses, priorities, categories
```

## How real-time works

1. On sign-in, `RequestsContext` opens `ws://<api>/ws/requests/?token=<access>`.
2. Every event carries a full request snapshot. The reducer stores it in `byId`, so the dashboard
   cards and the detail page update instantly. Stale events (older `updated_at`) are ignored.
3. `request.progress` events only update `byId`. `request.created` / `request.status_changed` also bump a
   `version` counter; pages watching it re-fetch their list from REST (debounced), because a status change
   can move a request in or out of the current filter.
4. If the socket drops it reconnects with exponential backoff (1s, 2s, 4s ... max 15s) and re-syncs from REST
   once the server says `connection.ready`. A ping every 25s detects dead connections.

REST is the source of truth; WebSocket events are fast hints on top of it.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend base URL. The WebSocket URL is derived from it (`http` -> `ws`). |

The backend must allow your frontend origin in `CORS_ALLOWED_ORIGINS` (default includes `http://localhost:5173`).
