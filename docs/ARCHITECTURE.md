# IDTCC — Architecture Guide

Insurance Digital Twin Command Center: an AI catastrophe-simulation platform that
generates up to 50,000 synthetic property digital twins and runs an 8-agent
LangGraph pipeline to assess insurance portfolio risk against Indian cyclones.

## 1. System design

```
┌────────────────────────────────────────────────────────────────────────┐
│                              Browser (SPA)                                │
│   React 18 · Vite · Recharts · Leaflet      :5173                         │
│   src/api/client.js  ── retry + timeout + SSE reader ──┐                  │
└────────────────────────────────────────────────────────┼─────────────────┘
                                                          │ REST + SSE
┌──────────────────────────────────────────────────────────▼───────────────┐
│                         FastAPI backend  :8000                             │
│  ┌────────────┐  ┌─────────────────────────┐  ┌────────────────────────┐  │
│  │ routers/   │  │ graph/orchestrator.py    │  │ core/                  │  │
│  │ simulation │→ │ LangGraph DAG (8 agents) │→ │ simulation (twins)     │  │
│  │ twins      │  │ + consistency + conf.    │  │ locations, realtime    │  │
│  └────────────┘  └───────────┬─────────────┘  │ llm (retry, json)      │  │
│  middleware: request-id, metrics              │ guardrails, metrics    │  │
│  /health /health/ready /metrics               │ logging, agent_base    │  │
└───────────────────────────────┼──────────────────────────────┬───────────┘
                                │ OpenAI-compatible HTTP        │ traces
┌────────────────────────────────▼─────────┐      ┌─────────────▼───────────┐
│   vLLM inference server  :8001            │      │  LangSmith (cloud)      │
│   Qwen3-14B · AMD MI300X · ROCm · bf16    │      │  latency/tokens/prompts │
└───────────────────────────────────────────┘      └─────────────────────────┘
```

Three independently deployable services. The backend is **stateless** — every
simulation is computed from the request — so it scales horizontally behind a load
balancer while a shared vLLM pool serves inference.

## 2. Request lifecycle (a simulation)

1. Browser `POST /api/v1/simulation/run` with a `SimulationRequest`.
2. Middleware assigns a correlation `request_id` (in every log line) and starts a
   latency timer.
3. The router builds cyclone params (incl. counterfactual `track_shift_km`) and
   an initial `IDTCCState`, then invokes the compiled LangGraph.
4. Nodes execute along the DAG (§3). Each agent is `@instrument`-wrapped:
   records latency/success metrics, logs, and **never raises** — a failed agent
   returns a degraded envelope so the pipeline always completes.
5. `assemble_forecast` runs the cross-agent **consistency check**, aggregates
   per-agent **confidence**, generates the executive summary, and returns the
   `ForecastResponse`.
6. Response validated against the Pydantic schema (with `extra="allow"`, so agent
   fields are never silently dropped) and returned. `/stream` emits the same
   nodes incrementally over SSE.

## 3. Agent DAG (preserved from the original design)

```
START → generate_twins → weather → risk ─┬─→ claims ─→ reserve ─┬─→ resource ─┐
                                         └─→ fraud ──────────────┴─→ alerts ───┤
                                                                               ▼
                                                       fraud/resource/alerts → judge
                                                                               ▼
                                                                  assemble_forecast → END
```

| # | Agent | Technique | Key output |
|---|---|---|---|
| — | Twin Generator | Faker + NumPy vectorised | 50K property twins + cyclone impact |
| 1 | Weather | deterministic severity + LLM narrative | severity index, hazards |
| 2 | Risk Exposure | pandas aggregation | exposure %, flood-zone breakdown |
| 3 | Claims Forecast | probabilistic loss model | expected claims, loss by area |
| 4 | Fraud Detection | rules + **FAISS** kNN anomaly | flagged twins, exposure |
| 5 | Reserve | actuarial IBNR + cat buffer | reserve, adequacy ratio, scenarios |
| 6 | Resource Planning | **K-Means** clustering | adjuster zones |
| 7 | Customer Alerts | LLM SMS generation | 160-char personalised alerts |
| — | LLM-as-Judge | LLM scoring on 5 criteria | audit scores, verdict |
| — | Forecast Assembly | aggregation + LLM summary | master KPIs, confidence, consistency |

## 4. Cross-cutting concerns

| Concern | Module | Notes |
|---|---|---|
| **Confidence** | `core/agent_base.py` | Deterministic, from data coverage/range/narrative — never asked from the LLM. |
| **Explainability** | `core/agent_base.py` | `{why, inputs_used, evidence}` on every agent. |
| **Guardrails** | `core/guardrails.py` | JSON extraction, numeric bounds, cross-agent consistency. |
| **Resilience** | `core/llm.py` (tenacity) | Exponential-backoff retry; JSON fallback; provider failover (vLLM→Anthropic). |
| **Observability** | `core/metrics.py`, `core/logging_config.py` | Prometheus `/metrics`, JSON logs, LangSmith traces. |
| **Schema integrity** | `models/schemas.py` | `extra="allow"` + shared TS types in `frontend/src/types/api.d.ts`. |

## 5. Data flow & state

`IDTCCState` (TypedDict, `graph/state.py`) is the single source of truth threaded
through the DAG. Twins are serialised as records (`twins_records`) so the state
stays JSON-serialisable for LangGraph checkpointing. The `errors` field uses an
additive reducer so parallel branches can append without clobbering.

## 6. Deployment & operations

- **Processes:** three long-running services — vLLM (`:8001`), uvicorn/FastAPI
  (`:8000`, run with `--workers N` behind a process manager), and the built
  frontend served as static assets (or `vite preview`). Run under systemd,
  supervisor, or any process supervisor.
- **Health:** `/health/live`, `/health/ready` (503 until the graph is warm), and
  `/metrics` (Prometheus) drive supervision, load-balancer health checks, and
  monitoring. See [OPERATIONS.md](OPERATIONS.md).
- **Scaling:** the backend is stateless → run multiple uvicorn instances behind a
  load balancer pointing at a shared vLLM pool; scale vLLM vertically first
  (`--max-num-seqs`), then add replicas. See [AMD_DEPLOYMENT.md](AMD_DEPLOYMENT.md).
- **Same-origin:** the API does not enable CORS; serve the frontend and API from
  one origin (reverse proxy in prod, Vite proxy in dev — `vite.config.js`).
- **CI/CD:** `.github/workflows/ci.yml` — lint, tests, frontend build, and
  security scans (bandit, pip-audit, npm audit, Trivy).
