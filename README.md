# Relay — CoolBreeze AC Support Assistant

## Author
Mobin Yousefi

## Overview
An agentic customer-support assistant for CoolBreeze AC. The web
layer (Django + DRF, ASGI) and the AI execution layer (a separate
ai-worker process) are two independent processes that talk only
through a RabbitMQ message queue — never a direct function call, and
never inside a single request/response cycle.

Six services: `frontend` (React), `backend` (Django/DRF), `ai-worker`
(LangGraph agent), `postgres`, `rabbitmq`, `chromadb`.

## Running the project
```bash
git clone <repo-url>
cd relay
cp .env.example .env   # fill in real values: GEMINI_API_KEY, TAVILY_API_KEY, LANGFUSE_*
docker compose up -d --build
```

## Infrastructure decisions

**Why service names, not localhost:** each service runs in its own
container with its own network namespace; `localhost` inside the
backend container refers to the backend container itself, not
rabbitmq/postgres/chromadb. Docker Compose's internal DNS resolves
service names (e.g. `chromadb`, `rabbitmq`) to the right container.

**Why depends_on isn't enough:** `depends_on` only waits for the
container process to *start*, not for the service inside it (e.g.
Postgres accepting connections) to be *ready*. `healthcheck` +
`condition: service_healthy` fixes this by waiting for an actual
readiness probe instead of just "the process exists."

**Why named volumes:** without them, data (Postgres tables, ChromaDB
vectors, RabbitMQ queues) lives only inside the container's writable
layer and is destroyed on `docker compose down`. Named volumes
persist that data across container recreation/rebuilds.

## Commands vs. Events

A **command** means "do this" and has exactly one consumer — e.g.
`process_support_message`, published once by the backend and
consumed by exactly the one ai-worker instance that picks it up.

An **event** means "this happened" and may have zero or more
consumers — e.g. `agent_log`, which the admin SSE stream consumes to
update the live activity panel, but nothing requires anyone to be
listening for it to be valid.

Every message on the queue shares one versioned envelope shape:
`event_id`, `correlation_id`, `type`, `version`, `timestamp`, plus
the payload fields flattened at the top level.

| Type | Kind | Producer | Consumer(s) |
|---|---|---|---|
| `process_support_message` | command | backend (`views.chat`) | ai-worker |
| `support_response` | event | ai-worker | backend (`async_response_consumer` → customer SSE) |
| `agent_log` | event | ai-worker (`agents._create_log`) | backend (`async_response_consumer` → admin SSE) |
| `user_message` | event | backend (`views.chat`) | backend (admin SSE, same process) |

## Reliability

**If the same command arrives twice:** each message carries a unique
`event_id`. The worker checks the `ProcessedEvent` table before doing
any work; if the id was already processed, it's a no-op — no
duplicate reply, no duplicate refund.

**If the worker crashes before acking:** RabbitMQ requeues the
unacked message and redelivers it — we hit this for real during
development (a heartbeat timeout during a slow first-run embedding
model download crashed the worker mid-message). The idempotency check
above makes that redelivery safe even though the message gets
processed again. Commands that keep failing after retries exhaust
their exponential backoff (2s, 4s, 8s) are dead-lettered into
`support_events_dlq` instead of being silently dropped.

## Stream vs. Record of System

The source of truth for a conversation is always the `Message` table in
PostgreSQL, never the SSE stream itself. The worker persists the agent's
reply to the database *before* publishing it to RabbitMQ for SSE delivery.

SSE (`/support/events/`) is a live notification channel only — it tells
an already-open tab "a new reply exists," it does not carry the only copy
of that reply.

If the stream is interrupted mid-generation (e.g. the browser tab loses
connection while Maya is still working):
- The agent keeps running server-side regardless of any open SSE
  connection — the reply gets written to the database either way.
- The frontend tracks connection state (`connecting` / `connected` /
  `reconnecting` / `failed`) from real `EventSource` events
  (`onopen` / `onerror` / `readyState`), and shows it instead of failing
  silently.
- On reconnect (`onopen` firing after a prior disconnect), the frontend
  re-fetches the current conversation from `GET /support/dashboard/<id>/`
  — the same database-backed endpoint used when first opening a
  conversation — so any reply that was generated and stored while the
  stream was down is picked up automatically, with no manual refresh
  needed.
- If reconnection keeps failing (5+ consecutive attempts), the UI shows
  a `failed` state and asks the user to refresh, rather than pretending
  everything is fine.

We deliberately do not stream the reply token-by-token. The agent
(support -> tools -> support -> ... -> finalize) runs to completion in
the worker process, and one full `support_response` event is published
at the end. This trivially satisfies the "don't put one message per
token on the queue" requirement, and avoids the added complexity of
partial-message state (partial replies interrupted mid-stream, partial
replies vs. tool-call boundaries) for a project of this scope. The
`agent_log` events (`tool_call` / `tool_result`) already give the admin
panel a live view of progress while the agent works, which we consider
sufficient "liveness" without token-level streaming.

## The four tools

The support agent routes between exactly four tools via a small
LangGraph state machine (`agent` → `tools` → `agent` → ... →
`finalize`, capped at `MAX_STEPS`):

1. **Structured internal data** — `get_order_details`,
   `get_refund_history` (PostgreSQL, filtered by the authenticated
   user/order — `order_id`/`user_id` are injected from the graph
   state, never taken from model-generated arguments)
2. **Unstructured internal data** — `search_knowledge_base` (hybrid
   ChromaDB vector search + PostgreSQL full-text search over company
   documents, returns `{"source": "internal_document", ...}`)
3. **External data** — `search_web` (Tavily, returns
   `{"source": "web", ...}`) — distinct `source` values so internal
   and external citations never look alike
4. **Action tool** — `escalate_to_manager` (routes to a manager
   sub-agent, which can consult a risk sub-agent for fraud
   assessment)

## Observability & cost

Every model call and tool call is logged as a Langfuse
generation/span under a trace keyed by `correlation_id`, so one id
ties together the request, the queued command, the worker's
execution, and every sub-agent call (manager, risk).

Per-conversation cost is tracked from real `usage_metadata` token
counts (not estimates) at official Gemini 2.5 Flash rates, plus a
per-call Tavily credit count, and shown in the staff dashboard next
to the Agent Activity panel.

## Bonus items implemented
- Auto-generated OpenAPI docs (drf-spectacular) — `/api/docs/`
- Automatic fallback to a second Gemini model on primary failure
- Dead-letter queue for commands that exhaust all retries
- User feedback (👍/👎) linked to Langfuse traces
- RBAC: `support_agent` role can view any user's orders/conversations
- Hybrid full-text + vector search for internal documents