# IDTCC — Developer Guide

## 1. Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ (3.12 recommended) |
| Node.js | 18+ (20 recommended) |
| vLLM | ROCm build (or use Anthropic fallback for dev) |

## 2. Local setup (3 terminals)

**Terminal 1 — inference** (or skip and use Anthropic fallback):

```bash
cd backend && bash start_vllm.sh        # Qwen3-14B on :8001
```

**Terminal 2 — backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # edit as needed
python run.py                                        # :8000, docs at /docs
```

No GPU? In `.env` set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...`.
The pipeline runs identically; only narratives come from the cloud model.

**Terminal 3 — frontend:**

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL=http://localhost:8000
npm run dev               # :5173
```

The frontend tries the backend first and **falls back to local JS computation**
if it's unreachable (see `context/IDTCCContext.jsx`), so the UI always works.

## 3. Run quality gates locally

```bash
cd backend
pip install -r requirements-dev.txt
ruff check app          # lint
pytest -q               # unit tests (guardrails, metrics, schema)
python -m compileall -q app
```

## 4. Project layout (key additions)

```
backend/app/core/
  agent_base.py     # @instrument, confidence, explainability envelope
  guardrails.py     # JSON extraction, numeric bounds, cross-agent consistency
  metrics.py        # in-process Prometheus registry
  logging_config.py # structured JSON/console logging + request-id contextvar
  llm.py            # vLLM/Anthropic factory + tenacity retry + call_llm_json
backend/tests/      # pytest suite (no GPU required)
frontend/src/
  api/client.js     # retry + timeout + SSE reader
  types/api.d.ts    # shared contract types (mirror backend schemas)
scripts/
  benchmark_vllm.py # MI300X throughput/latency benchmark
  eval_models.py    # model comparison harness
  generate_ppt.py   # hackathon deck generator
.github/workflows/ci.yml   # lint, tests, build, security scans
```

## 5. Adding a new agent

1. Create `app/agents/<name>.py`. Implement `run(...)` and decorate it:

   ```python
   from app.core.agent_base import instrument, attach, compute_confidence
   from app.core.llm import call_llm_simple

   @instrument("<name>")
   def run(df, ...):
       # ... compute domain payload ...
       narrative = call_llm_simple(SYSTEM, prompt, agent="<name>")
       return attach(
           {...payload...},
           confidence=compute_confidence(data_coverage=1.0,
                                         has_narrative=not narrative.startswith("[LLM unavailable"),
                                         within_expected_range=True),
           why="one-line rationale",
           inputs_used=["field_a", "field_b"],
           evidence={"method": "..."},
       )
   ```

2. Register a node in `graph/orchestrator.py` (`build_graph`) and wire its edges.
3. Add its output field to `graph/state.py` (`IDTCCState`).
4. Add a Pydantic model (subclass `_AgentOutput`) in `models/schemas.py` and the
   matching TS type in `frontend/src/types/api.d.ts`.
5. If it produces a metric the consistency check should enforce, extend
   `guardrails.check_consistency`.

The `@instrument` decorator gives you latency/success metrics, structured logs,
and crash-safety for free.

## 6. Conventions

- Agents must be **pure and crash-safe** — return a degraded envelope, never raise
  (the decorator enforces this, but design for it).
- Keep `confidence` **deterministic** — derive it from data, never ask the LLM.
- Currency fields end in `_crore` or `_inr`; be explicit.
- When you change a schema, update `api.d.ts` in the **same** PR.
