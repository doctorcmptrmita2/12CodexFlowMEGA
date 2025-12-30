# MEGA PROMPT — CF-X (CodexFlow) v3 | Plan-Code-Review AI Orchestration Platform (Monorepo + Multi-Container)
# ROLE: Senior Full-Stack Architect & AI Engineer
# GOAL: Production-grade MVP with strict modularity, cost control, stability, and Roo Code compatibility.

# STACK
# - Dashboard: Next.js (App Router) + Tailwind (dark)
# - Router: Python FastAPI (CF-X Router) — authoritative gatekeeper
# - Proxy: LiteLLM (container) — provider gateway
# - DB/Auth/Logs: Supabase (Postgres + RLS)
# - Reverse Proxy: Traefik (recommended) for path-based routing and SSL
# - VS Code clients: Roo Code compatibility (OpenAI-compatible + SSE streaming)

=====================================================================
0) NON-NEGOTIABLE WORK RULES
=====================================================================
A) Output Format
- Always respond in "Part 1 / Part 2 / Part 3..." format.
- Each Part modifies/creates MAX 3 files total (repo-wide).
- For each file change, use unified diff format compatible with applyUnifiedDiff.
- NEVER rewrite entire files unless explicitly required. Prefer minimal diffs.

B) Anchor-based editing (MANDATORY)
- Before each change, show:
  - Find Anchor: a unique snippet that already exists
  - Replace With: the new snippet
- If creating a new file, provide a full file content diff.
WHY: prevents Cursor from rewriting the repo and reduces merge conflicts.

C) Safety
- Do NOT run terminal commands.
- Do NOT request or output secrets. Use env placeholders.
- Do NOT implement anything that bypasses billing/ToS of providers.
WHY: avoids illegal/unsafe behavior and ensures deployability.

D) Type/Style
- TypeScript strict.
- Clean architecture: separation between UI, API routes, services, shared libs.
- Defensive coding: validation, explicit error handling, null checks.

E) Acceptance Gates (end of each Part)
- Summarize what is done.
- List quick manual checks (no commands).
- Ask for approval before continuing.

F) Part Focus Rule (NEW)
- Each Part must focus on ONE service domain only:
  - Router parts modify router files only.
  - Dashboard parts modify dashboard files only.
  - LiteLLM parts modify only config (if needed).
WHY: avoids context-spill and makes progress predictable.

=====================================================================
1) PROJECT GOAL (MVP)
=====================================================================
CF-X is a 3-stage orchestrator:
- PLAN (Architect): Claude 4.5 → produce plan/spec ONLY (no code)
- CODE (Developer): DeepSeek V3 → implement via unified diffs
- REVIEW (Reviewer): GPT-4o-mini/Nano → security + logic + compatibility checks

All AI calls MUST go through LiteLLM.
All enforcement MUST happen in Router (not dashboard).

Core requirements:
- OpenAI-compatible endpoint for Roo Code (/v1/chat/completions)
- SSE streaming support
- User API keys
- Daily 1000 request limit (authoritative at router)
- Request logs (tokens/cost/latency/status) in Supabase (RLS)

=====================================================================
2) MONOREPO LAYOUT (CREATE/ENFORCE)
=====================================================================
/apps/dashboard
  /app
  /lib
  /components
  /middleware.ts (ONLY lightweight auth checks, NOT authoritative rate limiting)

/services/cfx-router
  main.py (FastAPI entry)
  /cfx (auth, rate_limit, routing, openai_compat, litellm_client, logger, resilience, concurrency)
  requirements.txt

/services/litellm
  (LiteLLM runs in container; config mounted)

/config
  models.yaml (single source for stage→model mapping)
  (optional later) litellm.yaml mapping if required

=====================================================================
3) DEPLOYMENT TOPOLOGY & ROUTING (NEW — MUST FOLLOW)
=====================================================================
We deploy as 3 containers + 1 reverse proxy container:

CONTAINERS:
1) dashboard (Next.js) — serves UI
2) cfx-router (FastAPI) — authoritative gateway (auth, rate limit, routing, SSE)
3) litellm (LiteLLM) — forwards to providers (Anthropic/DeepSeek/etc.)
4) traefik (reverse proxy) — single public entrypoint

PUBLIC ENTRYPOINT:
- Only Traefik exposes ports 80/443 to the internet.
- dashboard, cfx-router, litellm should NOT be directly public (except via Traefik routes).

PATH-BASED ROUTES (single domain):
- "/" and all web paths → dashboard container
- "/v1/*" → cfx-router container
INTERNAL ONLY:
- cfx-router → litellm via internal Docker network (e.g., http://litellm:4000)

WHY THIS MATTERS:
- LiteLLM must never be reachable from the internet (prevents bypass of limits/policy).
- Router is the single "source of truth" for cost control and security.
- UI stays stable even if router is under streaming load.

=====================================================================
4) SECRET OWNERSHIP & SECURITY BOUNDARIES (NEW — MUST FOLLOW)
=====================================================================
Secrets must be split by container responsibility:

A) Dashboard container may have:
- SUPABASE_URL
- SUPABASE_ANON_KEY (public-ish, OK)
- NO service role key
WHY: Browser-exposed keys are dangerous; keep dashboard read-only via RLS.

B) Router container may have:
- SUPABASE_SERVICE_ROLE_KEY (server-only)
- HASH_SALT / KEY_HASH_PEPPER (server-only)
- Internal URLs: LITELLM_BASE_URL=http://litellm:4000
WHY: Router writes logs, verifies API keys, enforces limits; needs privileged DB access.

C) LiteLLM container may have:
- Provider API keys (Anthropic/OpenAI/DeepSeek etc.)
- LiteLLM config mapping
WHY: Provider keys belong to the gateway; keeps blast radius small.

D) Traefik container:
- TLS certificates (if needed) / ACME config
WHY: centralizes SSL and routing.

ABSOLUTE RULE:
- Never put SUPABASE_SERVICE_ROLE_KEY into dashboard code or client-side bundles.
- Never expose provider keys anywhere outside LiteLLM.

=====================================================================
5) INTER-SERVICE CONTRACTS (NEW — MUST FOLLOW)
=====================================================================
Define strict "contracts" between services so upgrades don't break things.

5.1 Router API contract (public via Traefik)
- POST /v1/chat/completions (OpenAI-compatible)
- /health (simple health check)
- Returns headers:
  - X-CFX-Request-Id
  - X-CFX-Stage
  - X-CFX-Model-Used
  - X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset (UTC)
- Status codes:
  - 401 unauthorized
  - 429 rate limit exceeded
  - 503 upstream unavailable (circuit breaker open)
  - 500 internal error

5.2 Router → LiteLLM contract (internal only)
- Base URL: http://litellm:4000
- Router forwards requests to LiteLLM with:
  - strict timeouts
  - streaming support (SSE relay)
  - minimal retry for transient errors (1 retry max)
WHY: streaming is the most fragile path; contract avoids format drift.

5.3 Supabase contract
- RLS enabled so dashboard reads only own user rows.
- Writes (logs, counters, key validation) occur ONLY from router using service role.
WHY: prevents data leaks and maintains trust boundaries.

=====================================================================
6) DATA MODEL (SUPABASE) — LOGS + API KEYS + RATE LIMIT STATE
=====================================================================
Tables design:

A) api_keys
- id (uuid)
- user_id (uuid)
- key_hash (text) // hash only, never raw
- label (text)
- status (active|revoked)
- created_at

B) usage_counters
- id (uuid)
- user_id (uuid)
- day (date) // UTC day bucket
- request_count (int)
- updated_at
UNIQUE (user_id, day)

C) request_logs
- id (uuid)
- user_id (uuid)
- api_key_id (uuid nullable)
- request_id (text)
- session_id (text nullable)
- stage (plan|code|review|direct)
- model (text)
- input_tokens/output_tokens/total_tokens (int nullable)
- cost_usd (numeric nullable)
- latency_ms (int)
- status (success|error|rate_limited)
- error_message (text nullable)
- created_at

=====================================================================
7) STABILITY & RESILIENCE (MUST IMPLEMENT)
=====================================================================
7.1 Rate Limit Backend Abstraction (CRITICAL)
- Implement RateLimiter interface:
  check_and_increment(user_id, day_utc, limit) -> (allowed, remaining, reset_ts)
- MVP: Supabase/Postgres atomic upsert+increment
- Scaling: Redis drop-in implementation later without changing call sites
WHY: Postgres counters can become a bottleneck; abstraction keeps future stable.

7.2 Logging Strategy (CRITICAL)
- Logging MUST be best-effort and must NOT fail the user request.
- Use async/background logging (queue) from router.
- For streaming: log start + completion (best-effort).
WHY: synchronous DB writes increase latency and can take down API under load.

7.3 Streaming Robustness (CRITICAL)
- Handle client disconnects; stop upstream stream; close resources.
- Apply timeouts (connect/read) to avoid hanging sockets.
- Avoid unbounded buffering; flush SSE events promptly.
- Terminate cleanly; log errors if mid-stream failures.
WHY: SSE is long-lived; without this, stability collapses quickly.

7.4 Upstream Resilience (CRITICAL)
- Timeouts for LiteLLM calls
- Retry only transient failures (502/503/504), max 1 retry
- Circuit breaker if repeated upstream failures; return 503
- Per-user concurrency cap for streaming (e.g., max 2)
WHY: prevents cascading failures and abuse via parallel streams.

7.5 Direct Mode Policy (CRITICAL)
- Default: ignore client "model"; route by stage.
- Direct mode optional:
  - allowlist models
  - enforce max_tokens cap
  - deny large/expensive models
- If direct mode not implemented: return 400 "direct mode disabled"
WHY: direct mode can destroy cost control if loose.

=====================================================================
8) CF-X ROUTING LOGIC (AUTHORITATIVE)
=====================================================================
Router responsibilities:
- Authenticate by API key (Bearer)
- Enforce daily limit BEFORE calling LiteLLM
- Enforce per-user streaming concurrency cap
- Determine stage:
  - Use X-CFX-Stage if provided (plan|code|review|direct)
  - Else infer using simple rules; default to plan if uncertain
- Map stage→model via /config/models.yaml
- Forward to LiteLLM
- Relay responses (including SSE)
- Log outcome best-effort (async)

Stage behavior:
- PLAN: produce plan/spec only, no code.
- CODE: produce unified diffs only.
- REVIEW: analyze diffs and risks, no code.

=====================================================================
9) ROO CODE / OPENAI COMPATIBILITY (MINIMUM REQUIRED)
=====================================================================
Implement:
- POST /v1/chat/completions
- Accept OpenAI-style payload: {model, messages, stream, temperature, ...}
- If stream=true: SSE with correct "data:" framing and [DONE]
- Strict error codes and headers as defined above.

=====================================================================
10) UI/DASHBOARD RULES
=====================================================================
Dashboard is read-only for logs/usage (via Supabase + RLS):
- Overview: today usage, remaining quota, latency, stage distribution
- Logs: filters by stage/model/status/time
- API keys: reveal once at creation; never show again
- Do NOT store privileged keys in dashboard.

Also show reset time explicitly:
- Display "Quota resets at 00:00 UTC" to reduce user confusion.

=====================================================================
11) IMPLEMENTATION PLAN (PART SYSTEM | MAX 3 FILES EACH)
=====================================================================
PART 1 — Router Foundation: config + skeleton endpoints
(Only router/config files)
1) /config/models.yaml
2) /services/cfx-router/main.py
3) /services/cfx-router/cfx/config.py
Acceptance:
- Loads models.yaml
- /health returns OK
- /v1/chat/completions stub returns 501 JSON + request-id headers

PART 2 — Router Auth (key hashing, validation skeleton)
1) /services/cfx-router/cfx/auth.py
2) /services/cfx-router/cfx/security.py
3) /services/cfx-router/main.py

PART 3 — Router Rate Limit + concurrency cap (authoritative)
1) /services/cfx-router/cfx/rate_limit.py
2) /services/cfx-router/cfx/concurrency.py
3) /services/cfx-router/main.py

PART 4 — Router LiteLLM forwarding + streaming robustness
1) /services/cfx-router/cfx/litellm_client.py
2) /services/cfx-router/cfx/openai_compat.py
3) /services/cfx-router/main.py

PART 5 — Router async best-effort logging
1) /services/cfx-router/cfx/logger.py
2) /services/cfx-router/cfx/background.py
3) /services/cfx-router/main.py

PART 6 — Dashboard MVP (read-only)
1) /apps/dashboard/app/dashboard/page.tsx
2) /apps/dashboard/components/UsageSummary.tsx
3) /apps/dashboard/lib/supabaseServer.ts

PART 7 — Dashboard Logs UI
1) /apps/dashboard/app/dashboard/logs/page.tsx
2) /apps/dashboard/components/LogsTable.tsx
3) /apps/dashboard/components/Filters.tsx

PART 8 — Deployment scaffolding (Traefik + container wiring)
(Only deployment files)
1) /docker-compose.yml
2) /infra/traefik/traefik.yml
3) /infra/traefik/dynamic.yml
Acceptance:
- Traefik routes "/"→dashboard, "/v1/*"→router
- litellm is internal only

=====================================================================
12) DEPLOYMENT SUMMARY — EASYPANEL
=====================================================================
EasyPanel'de "CodexFlow" diye 1 Project açıyorsun, onun içinde de 3 ayrı Service (container grubu) oluşturuyorsun:

1. dashboard (Next.js)
2. cfx-router (FastAPI)
3. litellm (LiteLLM)

Kritik kural:
- Dış dünyaya açık olanlar: dashboard + cfx-router
- Dış dünyaya kapalı olan: litellm (sadece internal network)

En sorunsuz yönlendirme (EasyPanel'de):
- app.senindomain.com → dashboard
- api.senindomain.com → cfx-router
- LiteLLM → domain bağlama yok

Böyle kurarsan: Roo Code istekleri api. üzerinden router'a gider, router da internal'dan LiteLLM'e konuşur; limit/policy delinemaz.

=====================================================================
13) NET TOPOLOGY (EN NET ÖZET)
=====================================================================
Traefik "tek kapı": dış dünyaya yalnız o açık.

/ → dashboard, /v1/ → router

Router "polis": auth + limit + stage + SSE + log

LiteLLM "arka kapı": sadece router görür (internal network)

EasyPanel deploy:
- app.senindomain.com → dashboard
- api.senindomain.com → cfx-router
- LiteLLM → internal only (no public domain)

=====================================================================
14) START NOW
=====================================================================
Proceed with PART 1 only.
- Create the 3 files exactly as listed.
- Minimal diffs with anchors.
- End with checklist + ask approval for PART 2.

