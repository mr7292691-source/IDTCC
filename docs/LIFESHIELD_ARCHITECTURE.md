# LifeShield AI — Architecture

> **Digital Twins + Multi-Agent Intelligence for Disaster Preparedness and Response**
>
> *Formerly: Insurance Digital Twin Command Center (IDTCC). LifeShield AI is the
> same proven engine, promoted from "predicting insurance losses" to "protecting
> human lives, infrastructure, and communities before disaster strikes."*

---

## 1. Strategic thesis

The original IDTCC engine already modelled human vulnerability **per household**
(`has_infants` / `has_elderly` / `has_disabled` and a `social_vuln` score in
`core/simulation.py`). LifeShield AI promotes that human layer from a *column*
into a **first-class CitizenTwin graph** and adds **life-safety agents** that run
on the **exact same agent contract** as the insurance agents.

Nothing is rebuilt. The platform now exposes **two lenses over one twin
substrate**:

| Lens | Question it answers | Graph |
|------|--------------------|-------|
| **A — Insurance** (existing) | "What will this cost, and how do we reserve/deploy?" | `graph/orchestrator.py` |
| **B — Life-Safety** (new) | "Who can't get out, where do they go, and how do we reach them?" | `graph/safety_orchestrator.py` |

Both share: `core/agent_base.py` (deterministic confidence + explainability),
`agents/judge.py` (LLM-as-judge), `core/guardrails.py`, `core/llm.py`,
`core/metrics.py`, and the SSE streaming pattern.

---

## 2. What was added (this implementation)

```
backend/app/
├── core/
│   ├── geo.py                     # NEW shared vectorised haversine + nearest-facility
│   └── twins/                     # NEW twin substrate
│       ├── citizen.py             #   synthesize_citizens(): explode households → citizens
│       └── shelter.py             #   build_shelter_twins() / build_hospital_twins()
├── agents/safety/                 # NEW Lens-B agents (same @instrument/attach contract)
│   ├── vulnerable.py              #   Vulnerable Population
│   ├── shelter.py                 #   Shelter Allocation
│   ├── evacuation.py              #   Evacuation Planning
│   ├── rescue.py                  #   Rescue Prioritization
│   ├── sensor.py                  #   Sensor Intelligence
│   └── infrastructure.py          #   Infrastructure Risk
├── graph/
│   ├── state.py                   # EXTENDED: + SafetyState TypedDict
│   └── safety_orchestrator.py     # NEW Lens-B LangGraph DAG
├── models/twin_schemas.py         # NEW citizen/shelter + safety response schemas
├── routers/safety.py              # NEW /api/v1/safety/{run,stream}
└── main.py                        # EXTENDED: include safety router + pre-warm graph
```

Damage Assessment (multimodal / Qwen2.5-VL) is specified in §8 but intentionally
left as the next agent so the pipeline runs without a vision endpoint.

---

## 3. Digital twin substrate

### CitizenTwin (privacy-first)
Synthesised from property twins so the human layer is spatially and
demographically consistent with the risk layer. **No real PII** — every citizen
carries an opaque `pii_token` (a deterministic pseudonym); contact details, if
ever attached, live only in a privacy vault keyed by that token. Analytic agents
operate on `citizen_id` + features, never on identity.

Key columns: `age, gender, lat, lng, ward, district, state, disability_status,
chronic_diseases, medical_dependency, pregnancy_status, owns_vehicle,
can_walk_unassisted, transport_access, preferred_language, alert_channels,
hazard_exposure` and the agent-written `vulnerability_score, evacuation_priority,
rescue_priority, assigned_shelter_id`.

A 50,000-property city → ~180,000–200,000 citizen twins. That city-scale number
is what the MI300X story is built on.

### Other twins
`ShelterTwin` (capacity, wheelchair/medical/generator flags), `HospitalTwin`
(beds, ICU, dialysis/oxygen), plus a synthesised critical-asset inventory inside
the Infrastructure agent (roads, bridges, power, water, hospitals, schools).

---

## 4. Life-safety LangGraph DAG (Lens B)

```
START → ingest (citizens + shelters)
          ├──────────────┬───────────────┐
       sensor_agent  infra_agent   vulnerable_agent      (parallel)
                                          │  (writes vulnerability + priority)
                                          ▼
                                    shelter_agent         (writes assigned_shelter_id)
                                          ├───────────────┐
                                  evacuation_agent   rescue_agent   (parallel)
                                          └───────┬───────┘
                                            judge_agent  (REUSED from Lens A)
                                                  ▼
                                            assemble  (confidence + consistency + brief)
                                                  ▼
                                                 END
```

**Write-safety:** only `ingest`, `vulnerable_agent` and `shelter_agent` write the
`citizen_records` channel, and they execute in strictly sequential super-steps —
no concurrent writes. Sensor / infrastructure / evacuation / rescue are
read-only on the twin substrate and emit their own output channels.

`SafetyState` mirrors `IDTCCState` conventions: DataFrames stored as lists of
dicts (checkpointer-serialisable), `errors` is an `operator.add` additive channel.

---

## 5. Agent contract (unchanged)

Every safety agent is a plain `run(...)` decorated with `@instrument(name)` that
returns the shared envelope via `attach(out, confidence=…, why=…, inputs_used=…,
evidence=…)`:

- **Deterministic scoring** — vulnerability, rescue, fragility, sensor risk are
  pure pandas/numpy math with explicit weights in `evidence`. The LLM **never**
  produces a score; it only writes the narrative. Scores cannot be hallucinated.
- **Graceful degradation** — `@instrument` converts any exception into a
  confidence-0 degraded envelope, so one failing agent never crashes a plan.
- **Auditability** — `why` + `inputs_used` + `evidence` (weights, thresholds,
  policy) accompany every decision.

### Scoring summary

| Agent | Deterministic core | Confidence penalty |
|-------|--------------------|--------------------|
| Vulnerable | weighted frailty (age/disability/pregnancy/medical-dep) ⊕ hazard exposure → bands | — |
| Shelter | vulnerability-first greedy nearest-with-capacity, accessibility/medical constrained | ∝ unmet demand |
| Evacuation | ward-batched routes to assigned shelter, flood-zone aware, phased timeline | drop if longest route > landfall ETA |
| Rescue | 0.5·vuln + 0.35·hazard + 0.15·isolation → bands; ordered queue | — |
| Sensor | per-sensor warn/danger thresholds → risk + river breach ETA | lower coverage if feed is derived |
| Infrastructure | per-type fragility × proximity × age × condition + dependency cascades | — |

---

## 6. API

All under `/api/v1`, same FastAPI + Pydantic (`extra="allow"`) + SSE conventions
as the insurance router.

```
POST /safety/run      → run Lens-B pipeline, returns ResponsePlan        (sync)
POST /safety/stream   → SSE: each agent streams as it completes          (graph.stream)
```

`SafetyRunRequest`: `location_code, twin_count (property twins),
hazard_name/type, max_wind_kmh, radius_km, landfall_eta_hours, sensor_snapshot`.

`ResponsePlan`: top-line (`total_citizens, citizens_at_risk, critical_rescues,
shelters_activated, citizens_assigned, unmet_demand, overall_confidence,
consistency, executive_summary`) + nested per-agent outputs + `judge_scores`.

**Roadmap endpoints** (designed, not yet built): `/sensors/ingest`,
`WS /sensors/live`, `/alerts/dispatch`, `/citizens/{ward}` (anonymised).

---

## 7. Privacy, security & event-driven design

- **Consent-based, no Aadhaar.** Identity is pseudonymous (`pii_token`); the
  platform is designed to run entirely on synthetic/consented data.
- **Privacy vault** (roadmap `core/privacy/`): AES-GCM-encrypted contact data,
  resolvable only by token, gated by RBAC + purpose; only the alerting layer ever
  resolves a token → contact.
- **RBAC / audit / anonymize** (roadmap): field-level scopes per role
  (`gov_admin / dm_authority / responder / insurer / auditor`), append-only audit
  of every PII resolution, k-anonymity ward aggregates for public/insurer lenses.
- **Event-driven sensors** (roadmap): MQTT/WebSocket → `asyncio.Queue` (the exact
  primitive already used by the SSE producer) → threshold breach event → targeted
  re-inference of `sensor_agent` → critical alert, all on one stream.

---

## 8. Multimodal pipeline (next agent)

`agents/safety/damage.py` will call **Qwen2.5-VL via vLLM** over geo-tagged
drone/satellite/CCTV frames, returning structured `{flooding, structural_damage,
road_blocked}` per tile that overlays the map and updates the road network used
by the Evacuation agent. vLLM serves Qwen3-14B (text) and Qwen2.5-VL (vision)
**co-resident** — pure MI300X 192 GB HBM3 headroom.

---

## 9. AMD MI300X alignment

| Capability | Exploited by |
|------------|--------------|
| 192 GB HBM3 | 180k+ citizen twins + FAISS + **two models** resident, no swap |
| Continuous batching | 16 agents (9 insurance + 7 safety) as concurrent vLLM requests |
| Large context | full ward dossiers (twins + sensors + infra) in one judge prompt |
| Streaming inference | sensor breach → re-inference → alert in one SSE stream |
| Multimodal co-residency | text + vision agents share one GPU without OOM |

**Headline:** *one MI300X = one city's complete disaster brain, 16 agents in
parallel, refreshed in seconds.*

---

## 10. Run it

```bash
cd backend
# property twins are exploded into citizens automatically
curl -X POST localhost:8000/api/v1/safety/run \
  -H 'content-type: application/json' \
  -d '{"location_code":"CHN","twin_count":20000,"hazard_name":"NIVAR","max_wind_kmh":180,"landfall_eta_hours":12}'

# live agent-by-agent stream (SSE)
curl -N -X POST localhost:8000/api/v1/safety/stream \
  -H 'content-type: application/json' -d '{"location_code":"CHN","twin_count":20000}'
```

When `LLM_PROVIDER=vllm` is unreachable, agents still complete — narratives fall
back to `[LLM unavailable: …]` and confidence reflects the missing narrative, by
design. All deterministic scores are unaffected.
```
