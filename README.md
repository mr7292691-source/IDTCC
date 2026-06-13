# IDTCC — Insurance Digital Twin Command Center

**AMD AI Hackathon** · 50,000 living property twins · 35 Indian cities · Eight LangGraph agents · Real-time OSM + GDACS data · LangSmith tracing

---

## Production deliverables

| Area | Where |
|---|---|
| Architecture guide | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| API reference | [docs/API.md](docs/API.md) |
| Developer guide | [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) |
| Operations / monitoring / DR | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| AMD MI300X deployment & tuning | [docs/AMD_DEPLOYMENT.md](docs/AMD_DEPLOYMENT.md) |
| Benchmark report + harness | [docs/BENCHMARK_REPORT.md](docs/BENCHMARK_REPORT.md) · [scripts/benchmark_vllm.py](scripts/benchmark_vllm.py) |
| LLM evaluation + harness | [docs/LLM_EVALUATION.md](docs/LLM_EVALUATION.md) · [scripts/eval_models.py](scripts/eval_models.py) |
| Demo script | [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) |
| Judge Q&A prep | [docs/JUDGE_QA.md](docs/JUDGE_QA.md) |
| Hackathon deck | [IDTCC_Hackathon.pptx](IDTCC_Hackathon.pptx) · [scripts/generate_ppt.py](scripts/generate_ppt.py) |
| CI + security scanning | [.github/workflows/ci.yml](.github/workflows/ci.yml) |

**Production features added:** every agent returns `confidence` + `explainability`;
cross-agent consistency guardrails; LLM retry + JSON validation + vLLM→Anthropic
failover; Prometheus `/metrics` + structured logging + readiness/liveness probes;
incremental SSE streaming; shared frontend⇄backend contract types; pytest suite.
Quick start below; details in the docs above.

---

## Architecture

```
Terminal 1                Terminal 2               Terminal 3
──────────────────        ─────────────────        ─────────────────
vLLM server               FastAPI backend           React frontend
Port 8001                 Port 8000                 Port 5173
Qwen3-14B (AMD GPU)       LangGraph pipeline        BMW M Design UI
                          OSM + GDACS data
                          LangSmith traces
```

### LangGraph Pipeline

```
START
  └─ TwinGen (50K property twins + cyclone simulation)
       └─ Weather Agent (severity index, hazard list)
            └─ Risk Agent (portfolio exposure, flood zones)
                 ├─ Claims Agent   ─┐  (parallel)
                 └─ Fraud Agent    ─┤
                                   ▼
                              Reserve Agent
                                   ├─ Resource Agent  ─┐  (parallel)
                                   └─ Alerts Agent    ─┤
                                                      ▼
                                               LLM-as-Judge
                                                      └─ Forecast Assembly → END
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | 3.12 recommended |
| Node.js | 18+ | npm 9+ |
| vLLM | 0.11.1+ | AMD ROCm 6.4+ or CUDA |
| AMD GPU | MI300X | 192 GB HBM3 — any ROCm-capable GPU works |

---

## Quick Start (3 terminals)

### Terminal 1 — vLLM Server

```bash
# Launch Qwen3-14B on port 8001 (keep separate from FastAPI on 8000)
VLLM_USE_TRITON_FLASH_ATTN=0 \
vllm serve Qwen/Qwen3-14B \
    --served-model-name Qwen3-14B \
    --api-key abc-123 \
    --port 8001 \
    --enable-auto-tool-choice \
    --tool-call-parser hermes \
    --trust-remote-code \
    --dtype bfloat16
```

Or use the helper script:

```bash
cd backend
bash start_vllm.sh
```

Wait for the line `INFO:     Application startup complete.` before starting the backend.

---

### Terminal 2 — FastAPI Backend

```bash
cd backend

# 1. Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux

# 4. Edit .env — minimum required:
#    VLLM_BASE_URL=http://localhost:8001/v1
#    VLLM_MODEL=Qwen3-14B
#    LANGCHAIN_API_KEY=ls__your_key   (optional — enables LangSmith traces)

# 5. Start
python run.py
```

Backend starts at **http://localhost:8000**
Interactive docs at **http://localhost:8000/docs**

---

### Terminal 3 — React Frontend

```bash
cd frontend

# 1. Install
npm install

# 2. (Optional) point to backend
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
# VITE_API_URL=http://localhost:8000

# 3. Start
npm run dev
```

Frontend opens at **http://localhost:5173**

---

## Environment Variables

Full reference — copy from `backend/.env.example`.

### LLM Provider

```env
# "vllm" = local AMD GPU (default)   "anthropic" = cloud   "auto" = try vllm first
LLM_PROVIDER=vllm
```

### vLLM (local AMD MI300X) — Primary

```env
VLLM_BASE_URL=http://localhost:8001/v1
VLLM_API_KEY=abc-123
VLLM_MODEL=Qwen3-14B
VLLM_MODEL_HAS_THINKING=true    # strip <think> blocks from Qwen3 outputs
```

**Recommended models** (all under 60B, ROCm-compatible):

| Model | Params | Best for |
|---|---|---|
| `Qwen/Qwen3-14B` | 14B | Default — fast, excellent tool calling |
| `Qwen/Qwen2.5-32B-Instruct` | 32B | Best narrative + tool quality |
| `Qwen/Qwen3-30B-A3B` | 30B MoE (3B active) | Near-32B quality at 8B speed |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | 32B | Best reasoning / judge node |
| `meta-llama/Llama-3.1-8B-Instruct` | 8B | Fastest; good for alert generation |

### Anthropic (cloud fallback)

```env
ANTHROPIC_API_KEY=sk-ant-your_key_here
ANTHROPIC_MODEL=claude-sonnet-4-6
```

### LangSmith Tracing

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your_key_here
LANGCHAIN_PROJECT=idtcc-production
```

All LangChain + LangGraph agent calls are automatically traced. View at **smith.langchain.com**.

### App Settings

```env
DEFAULT_LOCATION=CHN           # default city code
DEFAULT_TWIN_COUNT=50000       # property twins per simulation
LOG_LEVEL=INFO
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/config` | Runtime config |
| `GET` | `/api/v1/simulation/locations` | All 35 cities grouped by state |
| `GET` | `/api/v1/simulation/locations?state=Tamil Nadu` | Filter by state |
| `GET` | `/api/v1/simulation/locations/{code}` | Single city — live OSM + GDACS enriched |
| `POST` | `/api/v1/simulation/run` | Full pipeline (sync) |
| `POST` | `/api/v1/simulation/stream` | Full pipeline (Server-Sent Events) |
| `GET` | `/api/v1/twins` | Property twins with risk scores |

Full Swagger UI: **http://localhost:8000/docs**

### Example — Run a simulation

```bash
curl -X POST http://localhost:8000/api/v1/simulation/run \
  -H "Content-Type: application/json" \
  -d '{
    "location_code": "VIZ",
    "twin_count": 10000,
    "cyclone_name": "HUDHUD",
    "max_wind_kmh": 215,
    "landfall_eta_hours": 36,
    "radius_km": 150
  }'
```

### Example — List all cities

```bash
curl http://localhost:8000/api/v1/simulation/locations
# Returns 35 cities across 14 states, grouped by state
```

---

## Available Cities (35 across 14 states)

| State | Codes | Disaster Types |
|---|---|---|
| Tamil Nadu | CHN, MDU, TRY, CDL, NGL, TUT | Cyclone, Flood |
| Andhra Pradesh | VIJ, VIZ, GNT, NLR | Cyclone, Flood |
| Telangana | HYD, WGL | Urban Flood |
| Odisha | BHU, PRI, CTK | Cyclone, Flood |
| West Bengal | KOL, MDP | Cyclone |
| Maharashtra | MUM, PUN | Cyclone, Urban Flood |
| Kerala | COK, TVM, KZD | Flood, Cyclone, Landslide |
| Gujarat | SRT, AMD, RJK | Cyclone |
| Karnataka | MNG, BLR | Landslide, Urban Flood |
| Bihar | PAT | Flood |
| Assam | GHY | Flood |
| Uttarakhand | DED | Flash Flood |
| Himachal Pradesh | SML | Landslide |
| Rajasthan | JAI | Urban Flood |

---

## Real-Time Data Sources

Location data is enriched live at simulation time (cached 30 min):

| Source | Data | Endpoint |
|---|---|---|
| **OSM Overpass API** | Real neighbourhood names | `overpass-api.de` |
| **OSM Overpass API** | Hospitals, schools, stadiums as safe spaces | `overpass-api.de` |
| **GDACS** | Active tropical cyclone near city | `gdacs.org/gdacsapi` |

If any API is unreachable, the simulation falls back to the curated static catalogue transparently.

---

## LangGraph Agent Pipeline

| # | Agent | Input | Output |
|---|---|---|---|
| — | Twin Generator | location code, twin count | 50K property twins DataFrame |
| 1 | Weather Intelligence | cyclone params | severity index, hazard list, narrative |
| 2 | Risk Exposure | twins + cyclone | exposure %, flood zone breakdown |
| 3 | Claims Forecast | twins | expected claims, loss by area |
| 4 | Fraud Detection | twins | flagged twins, FAISS anomaly score |
| 5 | Reserve Calculation | claims output | IBNR + cat buffer, 3 scenarios |
| 6 | Resource Planning | twins | K-Means adjuster zones |
| 7 | Customer Alerts | twins | LLM-generated 160-char SMS alerts |
| — | LLM-as-Judge | all agent outputs | 5-criterion score, APPROVED/REJECTED |
| — | Forecast Assembly | judge output | executive summary, master KPIs |

---

## Frontend Views

| View | Description |
|---|---|
| Command Center | Master dashboard — KPIs, charts, executive summary |
| Portfolio | Full 50K twin portfolio with risk filters |
| Live Map | Leaflet risk heat-map with cyclone track overlay |
| Agents | Per-agent detailed output (7 tabs) |
| Simulator | Counterfactual track-shift + parameter tuning |
| Safe Zones | Vulnerable population + nearest shelter assignment |
| Audit | LLM-as-Judge radar chart + regulatory audit trail |
| Backend API | Trigger LangGraph pipeline, stream agent events live, view LangSmith trace URL |

---

## Project Structure

```
IDTCC/
├── README.md
├── IDTCC.ipynb                         original notebook
├── DESIGN-bmw-m.md                     design specification
│
├── backend/
│   ├── run.py                          uvicorn entrypoint (port 8000)
│   ├── start_vllm.sh                   vLLM launch helper (port 8001)
│   ├── requirements.txt
│   ├── .env.example                    → copy to .env and fill keys
│   └── app/
│       ├── main.py                     FastAPI app, metrics, health, lifespan
│       ├── config.py                   pydantic-settings (all env vars)
│       ├── models/schemas.py           Pydantic request/response models
│       ├── core/
│       │   ├── locations.py            35-city catalogue + get_location()
│       │   ├── realtime_data.py        OSM + GDACS live fetchers (TTL cache)
│       │   ├── simulation.py           twin generation + cyclone engine
│       │   └── llm.py                  vLLM-primary LLM factory + LangSmith
│       ├── agents/
│       │   ├── weather.py              Agent 1
│       │   ├── risk.py                 Agent 2
│       │   ├── claims.py               Agent 3
│       │   ├── fraud.py                Agent 4 (FAISS)
│       │   ├── reserve.py              Agent 5
│       │   ├── resource.py             Agent 6 (K-Means)
│       │   ├── alerts.py               Agent 7 (SMS)
│       │   └── judge.py                LLM-as-Judge
│       ├── graph/
│       │   ├── state.py                LangGraph TypedDict state
│       │   └── orchestrator.py         Graph build + parallel branches
│       └── routers/
│           ├── simulation.py           /simulation/* endpoints + SSE
│           └── twins.py                /twins endpoint
│
└── frontend/
    ├── .env.example                    → copy to .env (VITE_API_URL)
    ├── package.json
    ├── vite.config.js                  port 5173
    └── src/
        ├── App.jsx
        ├── index.css                   BMW M design tokens
        ├── api/client.js               fetch + SSE stream client
        ├── context/IDTCCContext.jsx    local computation context
        └── components/
            ├── Layout/
            │   ├── TopNav.jsx
            │   └── Footer.jsx
            └── views/
                ├── CommandCenter.jsx
                ├── Portfolio.jsx
                ├── LiveMap.jsx
                ├── AgentsView.jsx
                ├── Simulator.jsx
                ├── SafeZones.jsx
                ├── AuditTrail.jsx
                └── BackendView.jsx     LangGraph pipeline UI
```

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **LLM Inference** | vLLM 0.11.1 · AMD ROCm 6.4 · Qwen3-14B (primary) |
| **Agent Framework** | LangGraph 0.2.60 · LangChain 0.3 · LangSmith |
| **Backend** | FastAPI 0.115 · Uvicorn · Pydantic v2 · SSE |
| **ML** | PyTorch 2.5 · FAISS · scikit-learn (K-Means) |
| **Live Data** | OpenStreetMap Overpass API · GDACS TC feed |
| **Synthetic Data** | Faker (en_IN) · NumPy · Pandas |
| **Frontend** | React 18 · Vite 5 · Recharts · Leaflet |
| **Design** | BMW M Design System · Inter (BMW Type Next Latin fallback) |

---

## Troubleshooting

**vLLM won't start**
```bash
# Check GPU visibility
rocm-smi           # AMD
nvidia-smi         # NVIDIA

# Reduce context length if OOM
vllm serve Qwen/Qwen3-14B --max_model_len 8192 ...
```

**Backend — `No LLM configured` error**
```
# .env must have at least one of:
LLM_PROVIDER=vllm
VLLM_BASE_URL=http://localhost:8001/v1   ← vLLM must be running first

# OR
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

**OSM / GDACS data not loading**
```
# Areas and safe spaces fall back to static catalogue automatically.
# Check internet access from the backend server:
curl "https://overpass-api.de/api/interpreter" -d "data=[out:json];node(1);out;"
```

**Cross-origin request blocked in browser**
```
# The backend does not enable CORS. Serve the frontend and API from the same
# origin (e.g. a reverse proxy), or use the Vite dev proxy in vite.config.js:
#   server: { proxy: { '/api': 'http://localhost:8000', '/health': 'http://localhost:8000' } }
```

**LangSmith traces not appearing**
```env
# Confirm all three vars are set in backend/.env:
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=idtcc-production
```
