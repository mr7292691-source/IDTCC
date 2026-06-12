# IDTCC — Insurance Digital Twin Command Center

> 50,000 living property twins · One catastrophe simulation · Seven LangGraph agents · LangSmith tracing

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite + BMW M Design System)                  │
│  Port 5173                                                      │
├─────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + LangGraph + LangSmith)                      │
│  Port 8000                                                      │
│                                                                 │
│  LangGraph Pipeline:                                            │
│  START → TwinGen → Weather → Risk →                             │
│          [Claims ∥ Fraud] → Reserve →                           │
│          [Resource ∥ Alerts] → LLM-as-Judge → Forecast → END   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Backend Setup

```bash
cd backend

# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env and set your keys:
#   ANTHROPIC_API_KEY=sk-ant-...
#   LANGCHAIN_API_KEY=ls__...
#   LANGCHAIN_TRACING_V2=true

# 4. Run
python run.py
# → API available at http://localhost:8000
# → Docs at http://localhost:8000/docs
```

### LLM Options

| Option | Config |
|--------|--------|
| Anthropic (default) | Set `ANTHROPIC_API_KEY` in `.env` |
| vLLM (local) | Set `VLLM_BASE_URL` and `VLLM_MODEL` |
| Offline fallback | Works without any key — agents return rule-based outputs |

### LangSmith Tracing

Set these three env vars in `backend/.env`:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your_key_here
LANGCHAIN_PROJECT=idtcc-production
```

Traces appear at **smith.langchain.com** under the project `idtcc-production`.

---

## Frontend Setup

```bash
cd frontend

# 1. Install
npm install

# 2. Optional: set backend URL
copy .env.example .env
# VITE_API_URL=http://localhost:8000

# 3. Run
npm run dev
# → http://localhost:5173
```

---

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/health` | Health check |
| GET  | `/api/v1/config` | App config |
| GET  | `/api/v1/simulation/locations` | Available city locations |
| POST | `/api/v1/simulation/run` | Full pipeline (sync) |
| POST | `/api/v1/simulation/stream` | Full pipeline (SSE stream) |
| GET  | `/api/v1/twins` | Property twins with risk data |

Interactive API docs: **http://localhost:8000/docs**

---

## LangGraph Agent Pipeline

| # | Agent | Description |
|---|-------|-------------|
| — | Twin Generator | Generates 50K synthetic property twins + cyclone simulation |
| 1 | Weather Intelligence | Cyclone severity, hazards, rainfall forecast |
| 2 | Risk Exposure | Portfolio exposure, flood zone breakdown |
| 3 | Claims Forecast | Expected claims, loss by area |
| 4 | Fraud Detection | Rule-based + FAISS anomaly detection |
| 5 | Reserve Calculation | Cat-loaded reserve + IBNR |
| 6 | Resource Planning | K-Means adjuster deployment zones |
| 7 | Customer Alerts | LLM-generated SMS alerts |
| — | LLM-as-Judge | Independent 5-criterion evaluation of all predictions |
| — | Forecast Assembly | Executive summary + master forecast |

---

## Frontend Views

| View | Description |
|------|-------------|
| Command Center | Master dashboard — KPIs, charts, executive summary |
| Portfolio | Full 50K twin portfolio with filters |
| Live Map | Folium-style Leaflet map with risk heat layer |
| Agents | Per-agent detailed output (7 tabs) |
| Simulator | Counterfactual track-shift simulator |
| Safe Zones | Vulnerable population + shelter assignment |
| Audit | LLM-as-Judge radar + regulatory audit trail |
| **Backend API** | **Trigger LangGraph pipeline, stream agent events, view LangSmith traces** |

---

## Tech Stack

- **Backend**: FastAPI · LangGraph · LangSmith · LangChain · Anthropic (or vLLM)
- **ML**: PyTorch `InsuranceRiskNet` · FAISS · scikit-learn K-Means
- **Data**: OpenStreetMap Overpass API · NOAA IBTrACS · IRDAI
- **Frontend**: React 18 · Vite · Recharts · Leaflet · BMW M Design System
- **Design**: BMW M tricolor palette · BMW Type Next Latin (Inter fallback)
