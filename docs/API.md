# IDTCC — API Documentation

Base URL: `http://localhost:8000` · Interactive Swagger: `/docs` · OpenAPI: `/openapi.json`

All schemas are defined in [`backend/app/models/schemas.py`](../backend/app/models/schemas.py)
and mirrored for the frontend in [`frontend/src/types/api.d.ts`](../frontend/src/types/api.d.ts).

## Conventions

- Content type: `application/json` (SSE endpoint returns `text/event-stream`).
- Correlation: send `X-Request-Id` to trace a call across logs; one is generated otherwise.
- Currency: amounts in **₹ crore** (`_crore`) or **₹** (`_inr`) as named.
- Agent outputs all carry `confidence` (0–1) and `explainability {why, inputs_used, evidence}`.

---

## Health & ops

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Basic liveness + version. |
| GET | `/health/live` | Liveness probe (process up). |
| GET | `/health/ready` | Readiness probe — `503` until graph compiled. |
| GET | `/metrics` | Prometheus exposition (app-layer metrics). |
| GET | `/api/v1/metrics/summary` | JSON snapshot: per-agent latency/tokens/success. |
| GET | `/api/v1/config` | Runtime config (provider, model, LangSmith status). |

---

## `POST /api/v1/simulation/run`

Run the full 8-agent pipeline and return the assembled forecast.

**Request — `SimulationRequest`**

| Field | Type | Default | Bounds |
|---|---|---|---|
| `location_code` | string | `"CHN"` | a city code |
| `twin_count` | int | `50000` | 100–100000 |
| `cyclone_name` | string | `"NIVAR"` | — |
| `max_wind_kmh` | float | `180` | 60–300 |
| `landfall_eta_hours` | int | `48` | 6–120 |
| `radius_km` | float | `120` | 20–300 |
| `track_shift_km` | float | `0` | counterfactual track shift |

```bash
curl -X POST http://localhost:8000/api/v1/simulation/run \
  -H "Content-Type: application/json" \
  -d '{"location_code":"VIZ","twin_count":10000,"cyclone_name":"HUDHUD","max_wind_kmh":215,"landfall_eta_hours":36,"radius_km":150}'
```

**Response — `ForecastResponse` (abridged)**

```jsonc
{
  "event_name": "HUDHUD",
  "location": "Visakhapatnam",
  "total_portfolio_twins": 10000,
  "twins_in_impact_radius": 4120,
  "red_twins": 1875,
  "expected_claim_count": 3960,
  "expected_loss_crore": 842.5,
  "reserve_required_crore": 1204.8,
  "adjusters_needed": 33,
  "deployment_zones": 12,
  "fraud_risk_twins": 210,
  "storm_severity_index": 8.4,
  "primary_hazards": ["Extreme wind damage", "Coastal storm surge 2–4 m"],
  "executive_summary": "Cyclone HUDHUD ...",

  "overall_confidence": 0.91,
  "agent_confidences": {"weather":0.95,"risk":1.0,"claims":1.0,"fraud":0.88,"reserve":1.0,"resource":0.93,"alerts":0.9},
  "consistency": {"consistent": true, "consistency_score": 1.0, "issues": []},

  "risk":   { "exposure_pct": 41.2, "by_flood_zone_loss_crore": {...}, "confidence": 1.0, "explainability": {...} },
  "claims": { "...": "...", "confidence": 1.0, "explainability": {...} },
  "fraud":  { "faiss_anomaly_count": 47, "...": "..." },
  "reserve":{ "total_recommended_reserve_crore": 1204.8, "scenarios": {...} },
  "resource":{ "zone_details": [...] },
  "alerts": { "alerts": [{ "policy_id": "POL-...", "message": "..." }] },
  "judge_scores": { "weather": { "overall_score": 8.6, "verdict": "APPROVED", "confidence": 0.86 } }
}
```

---

## `POST /api/v1/simulation/stream`

Same input; streams agent completion events as Server-Sent Events. Events arrive
**incrementally** as each node finishes (not buffered).

```
data: {"agent":"system","status":"start"}
data: {"agent":"weather_agent","status":"done","output":{"weather_output":{...}}}
data: {"agent":"risk_agent","status":"done","output":{"risk_output":{...}}}
...
data: {"agent":"assemble_forecast","status":"done","output":{"forecast":{...}}}
data: {"agent":"system","status":"complete"}
```

`event.status` is one of `start | done | error | complete`. The large
`twins_records` payload is stripped from streamed output.

---

## `GET /api/v1/twins`

Property twins with computed risk.

| Query | Default | Notes |
|---|---|---|
| `location` | `CHN` | city code |
| `n` | `1000` | 10–50000 |
| `max_wind` | `180` | km/h |
| `radius_km` | `120` | impact radius |
| `risk_filter` | — | comma list of `red,orange,yellow,green` |

Returns `TwinsResponse { total, twins[], safe_spaces[] }`.

---

## `GET /api/v1/simulation/locations[/{code}]`

- `/locations` → `{ states[], groups[], total }`; optional `?state=Tamil Nadu`.
- `/locations/{code}` → single city enriched with live OSM + GDACS data.

---

## Error model

| Status | Meaning | Body |
|---|---|---|
| `400` | Invalid request (e.g. unknown `location_code`) | `{"detail": "..."}` |
| `404` | Unknown location code on `/locations/{code}` | `{"detail": "..."}` |
| `422` | Schema validation failed (out-of-bounds field) | FastAPI validation error |
| `503` | Not ready (`/health/ready` during startup) | `{"status":"starting"}` |
| `500` | Unhandled server error | `{"detail": "..."}` |

The frontend client retries `0`, `429`, and `5xx` with exponential backoff; `4xx`
is surfaced immediately as an `ApiError` with `.status` and `.body`.
