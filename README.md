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