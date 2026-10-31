# 3. API Reference

REST base URL: `http://localhost:8000/api`
WebSocket URL: `ws://localhost:8000/ws/requests/?token=<access_token>`

All request and response bodies are JSON. All endpoints require `Authorization: Bearer <access_token>` except register, login, refresh and health.

## 3.1 Conventions

### Error format

Every error uses the same envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Validation failed.",
    "details": { "title": ["Ensure this field has at least 5 characters."] }
  }
}
```

| HTTP status | `code` (examples) | Meaning |
|---|---|---|
| 400 | `validation_error` | Invalid input. `details` maps field names to messages |
| 401 | `authentication_failed`, `not_authenticated` | Wrong credentials, or missing or expired token |
| 403 | `permission_denied` | Logged in, but the role or ownership rule forbids the action |
| 404 | `not_found` | Does not exist, **or you are not allowed to see it** |
| 409 | `invalid_transition` | The request's current status does not allow this action |

### Pagination

List responses use page numbers (20 per page):

```json
{ "count": 42, "next": "http://localhost:8000/api/requests/?page=2", "previous": null, "results": [ ... ] }
```

### Request object

```json
{
  "id": 12,
  "title": "AC is not cooling",
  "description": "Living room AC runs but does not cool the room.",
  "category": "REPAIR",
  "priority": "HIGH",
  "status": "PROCESSING",
  "progress": 55,
  "stage": "Executing service work",
  "result": "",
  "error_message": "",
  "created_by": "op1",
  "assigned_supervisor": "sup1",
  "retry_count": 0,
  "created_at": "2026-10-30T10:00:00+06:00",
  "updated_at": "2026-10-30T10:00:12+06:00",
  "started_at": "2026-10-30T10:00:03+06:00",
  "completed_at": null
}
```

* `category`: `REPAIR`, `INSTALLATION`, `MAINTENANCE`, `INSPECTION`, `SUPPORT`
* `priority`: `LOW`, `NORMAL`, `HIGH`, `URGENT`
* `status`: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `CANCELLED`

## 3.2 Authentication

### `POST /auth/register/`

Creates an **operator** account. Public. The role cannot be chosen by the client.

```json
{ "username": "op3", "email": "op3@example.com", "password": "a-strong-password" }
```

**201**
```json
{ "id": 7, "username": "op3", "email": "op3@example.com", "first_name": "", "last_name": "", "role": "OPERATOR" }
```
Errors: **400** (duplicate username or email, weak password).

### `POST /auth/login/`

```json
{ "username": "op1", "password": "demo12345" }
```
**200** `{ "access": "<jwt>", "refresh": "<jwt>" }` (access lasts 30 minutes, refresh 1 day). **401** for wrong credentials.

### `POST /auth/refresh/`

```json
{ "refresh": "<jwt>" }
```
**200** `{ "access": "<jwt>" }`. **401** if the refresh token is invalid or expired.

### `GET /auth/me/`

**200** the current user (same shape as the register response). The client reads `role` from here.

## 3.3 Requests

### Who can do what

| Action | Operator | Supervisor |
|---|---|---|
| List / view requests | only ones they created | only ones assigned to them |
| Create | yes | no (403) |
| Cancel | own request, while `PENDING` | assigned request, while `PENDING` or `PROCESSING` |
| Retry | no (403) | assigned request, while `FAILED` |

### `GET /requests/`

Query parameters (all optional):

| Parameter | Example | Notes |
|---|---|---|
| `status` | `PENDING,PROCESSING` | comma-separated list |
| `priority` | `URGENT` | exact |
| `category` | `REPAIR` | exact |
| `search` | `pump` | case-insensitive match on title or description |
| `ordering` | `-created_at` | one of `created_at`, `-created_at`, `priority`, `-priority`, `progress`, `-progress`, `status` |
| `page` | `2` | an out-of-range page returns 404 |

**200** paginated list of request objects.

### `POST /requests/`

Operators only.

```json
{
  "title": "AC is not cooling",
  "description": "Living room AC runs but does not cool the room.",
  "category": "REPAIR",
  "priority": "HIGH"
}
```

| Field | Rules |
|---|---|
| `title` | required, 5 to 200 characters |
| `description` | required, 10 to 5000 characters |
| `category` | required, one of the categories above |
| `priority` | optional, default `NORMAL` |

Any other field (such as `status` or `progress`) is ignored.

**201** with the request object (status `PENDING`, supervisor already assigned) and a `Location: /api/requests/{id}/` header. Processing starts in the background.
Errors: **400**, **403** (supervisors).

### `GET /requests/{id}/`

**200** request object. **404** if it does not exist or is not visible to the caller.

### `GET /requests/{id}/history/`

**200**
```json
[
  { "id": 1, "old_status": "",        "new_status": "PENDING",    "changed_by": "op1", "changed_at": "...", "note": "Request submitted" },
  { "id": 2, "old_status": "PENDING",  "new_status": "PROCESSING", "changed_by": null,  "changed_at": "...", "note": "Worker claimed (attempt 1)" },
  { "id": 3, "old_status": "PROCESSING","new_status": "COMPLETED", "changed_by": null,  "changed_at": "...", "note": "Processing finished" }
]
```
`changed_by: null` means the system or a worker made the change.

### `GET /requests/stats/`

**200** counts for the requests the caller can see:
```json
{ "PENDING": 1, "PROCESSING": 2, "COMPLETED": 10, "FAILED": 0, "CANCELLED": 1, "total": 14 }
```

### `POST /requests/{id}/cancel/`

No body. **200** the updated request (`CANCELLED`).
Errors: **403** (not your request or not allowed for your role), **404**, **409** (request is already finished or an operator tries to cancel a request that is no longer pending).

### `POST /requests/{id}/retry/`

Supervisors only. No body. **202** the request, back in `PENDING` and queued again.
Errors: **403**, **404**, **409** (request is not `FAILED`).

### `GET /health/`

Public. **200** `{ "status": "ok" }`.

## 3.4 WebSocket events

### Connecting

`ws://localhost:8000/ws/requests/?token=<access_token>`

* Invalid, missing or expired token: the server closes the connection with code **4401**.
* On success the first message is `connection.ready`.
* The connection is receive-only. The only message a client may send is `{"type": "ping"}`, which is answered with `{"type": "pong"}`.

### Who receives events

The request's creator and its assigned supervisor, the same people who can fetch it with REST.

### Event messages

All events except `connection.ready` and `pong` carry a full request snapshot.

**`connection.ready`**
```json
{ "type": "connection.ready", "role": "OPERATOR" }
```

**`request.created`**
```json
{ "type": "request.created", "request": { "id": 12, "status": "PENDING", "progress": 0, "...": "..." } }
```

**`request.status_changed`** (claim, completion, failure, cancel, retry, stall recovery)
```json
{ "type": "request.status_changed", "request": { "id": 12, "status": "COMPLETED", "progress": 100, "...": "..." } }
```

**`request.progress`** (after each processing stage)
```json
{ "type": "request.progress", "request": { "id": 12, "status": "PROCESSING", "progress": 55, "stage": "Executing service work", "...": "..." } }
```

### Processing stages (simulation)

| Progress | Stage label |
|---|---|
| 10 | Validating request details |
| 30 | Scheduling technician |
| 55 | Executing service work |
| 80 | Quality check |
| 95 | Generating service report |
| 100 | Done (status `COMPLETED`) |

Each stage takes `PROCESSING_STAGE_SECONDS` (default 4 s).

### Recommended client pattern

1. Load state with `GET /requests/`.
2. Apply events on top; ignore any event whose `updated_at` is older than what you hold.
3. On reconnect, reload with REST before trusting events again.

## 3.5 Example session (curl)

```bash
# 1. sign in
curl -s -X POST localhost:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"op1","password":"demo12345"}'
# -> {"access":"...","refresh":"..."}

# 2. create a request
curl -s -X POST localhost:8000/api/requests/ \
  -H "Authorization: Bearer $ACCESS" -H 'Content-Type: application/json' \
  -d '{"title":"AC is not cooling","description":"Living room AC runs but does not cool.","category":"REPAIR","priority":"HIGH"}'

# 3. watch it (browser console)
#   const ws = new WebSocket('ws://localhost:8000/ws/requests/?token=' + ACCESS);
#   ws.onmessage = (e) => console.log(JSON.parse(e.data));
```
