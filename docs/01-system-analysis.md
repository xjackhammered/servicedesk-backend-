# 1. System Analysis

**Project:** ServiceDesk, a real-time service request management system
**Deliverable:** System Analysis (assignment deliverable 1)

## 1.1 Problem statement

A growing service organization (repairs, installations, maintenance, support) handles customer service requests manually. This causes three problems:

1. **Delayed updates.** Requests move through the organization by phone, chat or paper, so status changes reach people late.
2. **Poor visibility.** Nobody can see at a glance which requests are waiting, in progress, finished or stuck.
3. **No capacity for parallel work.** Long-running work cannot be tracked reliably when several requests are in flight at once.

The organization needs a web system where **operators submit service requests**, **supervisors monitor processing in real time**, several requests are processed **simultaneously**, and the interface stays **responsive** while long operations run in the background.

## 1.2 Business objectives

| ID | Objective | How we will know it is met |
|---|---|---|
| BO-1 | Remove manual hand-offs when logging a request | An operator can submit a request in one form and it is stored immediately |
| BO-2 | Give instant visibility of progress | Status and progress changes appear on screen without a page refresh |
| BO-3 | Handle many requests at once | Multiple requests progress independently and in parallel |
| BO-4 | Keep the system usable during long jobs | Submitting returns immediately; the UI never blocks on processing |
| BO-5 | Create an audit trail | Every status change is recorded with who or what made it and when |
| BO-6 | Be trustworthy under failure | A crashed worker or a broker outage does not leave requests stuck forever |

## 1.3 Users and stakeholders

| Role | Description | Main goals |
|---|---|---|
| **Operator** | Front-line staff who receive customer problems | Log a request quickly, follow it to completion, cancel a mistaken one |
| **Supervisor** | Staff responsible for a group of requests | See everything assigned to them, spot failures, retry or cancel |
| **Administrator** | System owner | Create supervisor accounts, inspect data (Django admin) |

The reviewers of this assignment are an additional stakeholder: they need a design that is explainable, documented and runnable.

## 1.4 Assumptions

| ID | Assumption | Consequence |
|---|---|---|
| A1 | The assignment does not define who does the work or how completion is detected | Processing is **simulated** as a deterministic five-stage job. A real deployment would replace the worker's stage loop with a real integration or a technician's confirmation |
| A2 | The assignment names operators and supervisors but not how requests reach supervisors | Each request is **assigned automatically** to the supervisor with the fewest active requests |
| A3 | Supervisors should not be able to see everyone's data | **Visibility is role-based:** operators see their own requests, supervisors see those assigned to them |
| A4 | Operators submit requests (on behalf of customers) | Customers do not log in. There is no customer portal |
| A5 | A single organization uses the system | No multi-tenancy |
| A6 | Supervisor accounts are privileged | Public registration only creates operators; supervisors are created by an administrator |
| A7 | Users have a modern browser with WebSocket support | No fallback transport (polling is explicitly not acceptable as the primary mechanism) |
| A8 | A single deployment region and a single database | No geographic replication |
| A9 | Request priority is informational | It is shown and filterable but does not reorder the processing queue |

## 1.5 Scope

**In scope**

* Authentication with roles (operator, supervisor)
* Create, list, view requests; search, filter, sort, paginate
* Automatic supervisor assignment
* Concurrent background processing with live progress
* Real-time updates to connected users via WebSockets
* Cancel (rule-based) and retry of failed requests
* Status history (audit trail)
* Automatic recovery of stalled or undelivered jobs
* Responsive web interface
* Automated tests, Docker infrastructure, documentation

**Out of scope**

* Technician scheduling, routing, inventory or parts
* Customer-facing portal, email or SMS notifications
* File uploads and attachments
* Payments and billing
* Multi-tenancy, internationalisation
* Production deployment and CI/CD (listed as future work)

## 1.6 Functional requirements

Priority: **M** = must have (mandatory in the assignment or core to the workflow), **S** = should have.

### Accounts and access

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Users can register as operators with username, optional email and password | M |
| FR-02 | Users can sign in and receive a time-limited access token and a refresh token | M |
| FR-03 | The system renews access tokens without forcing a new sign-in while the refresh token is valid | S |
| FR-04 | The system exposes the current user and role to the client | M |
| FR-05 | Supervisor accounts are created by an administrator, never by self-registration | M |

### Request management

| ID | Requirement | Priority |
|---|---|---|
| FR-10 | An operator can create a service request with title, description, category and priority | M |
| FR-11 | All inputs are validated server-side with field-level error messages | M |
| FR-12 | Clients cannot set system-controlled fields (status, progress, assignee) | M |
| FR-13 | A newly created request starts as PENDING and is assigned to a supervisor automatically | M |
| FR-14 | Users can list the requests they are allowed to see | M |
| FR-15 | Users can view the details of one request | M |
| FR-16 | Users can search by text and filter by status, priority and category; sort and paginate | M |
| FR-17 | Users can see summary counts per status | S |
| FR-18 | Users can view the status history of a request | M |

### Processing and monitoring

| ID | Requirement | Priority |
|---|---|---|
| FR-20 | Each new request is processed asynchronously by a background worker | M |
| FR-21 | Several requests can be processed at the same time | M |
| FR-22 | The worker reports staged progress (percentage and a stage label) | M |
| FR-23 | A request ends in COMPLETED (with a result) or FAILED (with an error message) | M |
| FR-24 | The same request is never processed by two workers at once, even if a task is delivered twice | M |
| FR-25 | If a worker dies mid-job, the request is re-queued automatically up to a limit, then marked FAILED | M |
| FR-26 | A request that was saved but never reached the queue is re-dispatched automatically | M |

### Real-time updates

| ID | Requirement | Priority |
|---|---|---|
| FR-30 | The server pushes events (created, status changed, progress) to connected clients over WebSockets | M |
| FR-31 | Only authenticated users can connect; each user receives events only for requests they may see | M |
| FR-32 | The client shows live status, progress and toasts without refreshing and without polling | M |
| FR-33 | The client reconnects automatically and re-synchronises after a connection loss | S |

### Control actions

| ID | Requirement | Priority |
|---|---|---|
| FR-40 | An operator can cancel their own request while it is PENDING | M |
| FR-41 | A supervisor can cancel a request assigned to them while it is PENDING or PROCESSING; a running job stops cooperatively | M |
| FR-42 | A supervisor can retry a FAILED request assigned to them | S |
| FR-43 | Invalid actions (for example cancelling a completed request) are rejected with a clear error | M |

## 1.7 Business rules

| ID | Rule |
|---|---|
| BR-1 | Allowed status changes: PENDING to PROCESSING or CANCELLED; PROCESSING to COMPLETED, FAILED, CANCELLED or PENDING (stall recovery only); FAILED to PENDING (retry). COMPLETED and CANCELLED are final |
| BR-2 | Only a worker moves a request to PROCESSING, COMPLETED or FAILED. Humans cannot mark work as done |
| BR-3 | Operators see only requests they created. Supervisors see only requests assigned to them. A hidden request is reported as "not found" |
| BR-4 | Every status change creates a history record (old status, new status, actor or system, time, note) |
| BR-5 | Only operators create requests. Only supervisors retry requests |
| BR-6 | Automatic recovery re-queues a stalled request at most MAX_PROCESSING_RETRIES times before failing it |

## 1.8 Non-functional requirements

Targets are design goals for this assignment, not measured production SLAs.

| ID | Category | Requirement | Justification | How it is addressed |
|---|---|---|---|---|
| NFR-1 | Performance | API calls that do not run work respond quickly (target: well under 300 ms for typical calls) | Operators submit requests while customers wait | Work happens in workers; indexed queries; `select_related` to avoid N+1 queries |
| NFR-2 | Responsiveness | Submitting a request never waits for processing | Long jobs would otherwise freeze the form | 201 returned right after commit; processing in Celery |
| NFR-3 | Scalability | Throughput grows by adding worker processes; the API tier holds no per-request state | Load will grow with the organization | Redis broker, `--concurrency`, stateless API, shared state only in PostgreSQL and Redis |
| NFR-4 | Reliability | No duplicate processing; no request stuck forever after a crash | A stuck request is a lost customer | Atomic claim, fencing token, heartbeat sweeper, re-dispatch of undelivered jobs, `acks_late` |
| NFR-5 | Data integrity | Status and history always agree; progress is within 0 to 100 | The audit trail must be trustworthy | Transactions, `CHECK` constraint, lifecycle table, side effects only after commit |
| NFR-6 | Security | Authentication on every endpoint except health; authorisation enforced on the server | Request data is business-sensitive | JWT, queryset-level visibility, write-only input serializers, hashed passwords, no mass assignment, CORS allow-list |
| NFR-7 | Availability | Components fail independently without losing data | Redis or a worker may restart | Persistent database as source of truth; REST re-sync after WebSocket reconnect; sweeper retries after broker outage |
| NFR-8 | Maintainability | Code is layered, small and tested | Reviewers and future developers must understand it | Views, serializers, selectors, services, tasks; 29 automated backend tests |
| NFR-9 | Usability | Clear forms, errors next to fields, live feedback | Operators work quickly | Client and server validation, toasts, progress bar, connection indicator |
| NFR-10 | Responsive design | Usable on phone, tablet and desktop | Staff may use mobile devices | Responsive CSS grid, mobile layout rules |
| NFR-11 | Observability | Failures and recoveries are visible | Operators of the system need to diagnose problems | Structured logging, status history, retry counter on the request |
| NFR-12 | Configurability | No environment-specific values in code | Same code must run in dev, test and production | Environment-based settings (`.env`) |
| NFR-13 | Portability | One command starts the infrastructure | Easy for reviewers to run | Docker Compose for PostgreSQL and Redis |

## 1.9 Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Worker crashes mid-job | Request stuck in PROCESSING | Heartbeat plus periodic sweeper re-queues, then fails after the retry limit |
| Crash between database commit and queue publish | Request stuck in PENDING | Sweeper re-dispatches PENDING requests that were never enqueued (a transactional outbox is the stronger alternative, noted as future work) |
| Redis or broker unavailable | Jobs not delivered, events not sent | Publishing failures are logged and never break the HTTP request; sweeper retries; clients re-sync from REST |
| Duplicate task delivery | Double processing | Atomic claim makes the second run a no-op |
| Stale worker writes after takeover | Corrupted progress | Fencing token (`attempt`) in every worker update |
| Client misses WebSocket events while offline | Out-of-date screen | Client reloads from REST on every (re)connect |
