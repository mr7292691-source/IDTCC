# IDTCC — Live Demo Script (5–6 minutes)

> Goal: show a cyclone entering a region, the 8-agent pipeline executing live,
> risk predicted, and resources allocated — with confidence + explainability +
> AMD GPU telemetry visible throughout.

## Pre-flight (before judges arrive)

```bash
# T1: vLLM on MI300X
cd backend && bash start_vllm.sh                # wait for "Application startup complete"
# T2: backend
cd backend && python run.py                     # wait for startup.complete log
# T3: frontend
cd frontend && npm run dev                       # open http://localhost:5173
# T4 (optional, impressive): GPU telemetry
watch -n1 rocm-smi --showuse --showmemuse
```

Verify: `curl localhost:8000/health/ready` → `{"status":"ready"}`.
Pre-select **Visakhapatnam (VIZ) / HUDHUD** — a dramatic, real historical storm.

## Beat-by-beat

**0:00 — The problem (15s).**
"Indian cyclones cause billions in insured losses. Insurers react *after*
landfall. IDTCC predicts the loss, the reserve, and the response *before* the
storm hits — across 50,000 live property digital twins."

**0:15 — Command Center (45s).**
Land on the Command Center. Point to the master KPIs and the **executive
summary** written by the LLM. Call out the new **overall confidence** badge and
the **consistency: clean** indicator — "every number is cross-checked."

**1:00 — Trigger a live run on the Backend view (90s).**
Switch to the Backend / pipeline view and start a **streamed** simulation. As SSE
events arrive, narrate the DAG executing **live, agent by agent**:
"Weather scores severity 8.4 → Risk finds 41% of the portfolio in the impact
radius → Claims and Fraud run in parallel → Reserve → Resource + Alerts → the
**LLM-as-Judge** audits the whole thing." Emphasise the events arrive
incrementally — this is real orchestration, not a canned response.

**2:30 — Explainability + confidence (45s).**
Open the Agents view, expand one agent. Show its **`explainability` block** —
*why* the decision was made, *which inputs* fed it, and the *evidence*. Show its
**confidence score**. "No black box — every agent justifies itself, and a failed
agent degrades gracefully instead of crashing the run."

**3:15 — Live Map + Resource allocation (45s).**
Live Map: cyclone track overlay + risk heatmap. Then show the **K-Means adjuster
deployment zones** — "we don't just predict loss, we tell the insurer exactly
where to stage adjusters T-24h before landfall."

**4:00 — Simulator / counterfactual (30s).**
In the Simulator, shift the cyclone track north (`track_shift_km`) and re-run.
Watch the loss and reserve numbers move. "Counterfactual planning in seconds."

**4:30 — AMD performance (45s).**
Switch to the rocm-smi terminal (or `/metrics`). "All of this inference runs on a
single **AMD MI300X**. 14B model, ~28 GB of weights — the other 160 GB is KV
cache, so we serve the entire agent fan-out concurrently." Quote benchmark
throughput from `docs/BENCHMARK_REPORT.md`.

**5:15 — Audit + close (30s).**
Audit Trail view: the LLM-as-Judge radar chart + verdict. "Regulator-ready audit
trail, explainable AI, real-time catastrophe intelligence — on AMD." Close.

## If something breaks

- vLLM down → set `LLM_PROVIDER=anthropic` (narratives still generate) **or** let
  the frontend's local fallback drive the UI. Either way, **the demo continues**.
- Backend down → the frontend computes locally; keep going, fix in the background.
- Slow first call → it's the cold-start prefill; pre-warm by running one
  simulation during pre-flight.

## One-liners to have ready

- "50,000 digital twins, 35 cities, 14 states, 8 agents, one GPU."
- "Confidence is computed from data — never asked from the model — so it can't be
  hallucinated."
- "Prefix caching means all 8 agents share one cached system prompt on the MI300X."
