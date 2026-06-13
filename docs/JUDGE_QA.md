# IDTCC — Judge Q&A Preparation Guide

Anticipated questions grouped by the AMD hackathon judging axes, with crisp
answers and the evidence to back each one.

## Technical depth

**Q: Is this real multi-agent orchestration or just sequential LLM calls?**
Real LangGraph DAG with parallel branches (claims∥fraud, resource∥alerts) joining
at the judge. State is a typed `IDTCCState`; the graph is compiled and streamed.
See `graph/orchestrator.py` and the DAG in `docs/ARCHITECTURE.md`.

**Q: How do you stop the LLM from hallucinating financial numbers?**
Three guardrail layers (`core/guardrails.py`): (1) structured-output validation
robustly extracts/validates JSON; (2) fact verification clamps numbers to
plausible bounds; (3) a **cross-agent consistency check** catches contradictions
(e.g. claims > portfolio, reserve < expected loss). Critically, the financial
math is **deterministic Python**, not the LLM — the model writes narratives, the
code computes the numbers.

**Q: Where does the confidence score come from?**
It's computed deterministically from data coverage, whether outputs fell in
expected ranges, and whether the narrative generated — **never asked from the
LLM** (`core/agent_base.compute_confidence`). So it can't be gamed by a confident-
but-wrong model. The overall forecast confidence is the agent mean × the
consistency score.

**Q: What happens when an agent fails?**
`@instrument` wraps every agent: it records metrics, logs, and returns a degraded
envelope (confidence 0, `degraded: true`) instead of raising. The pipeline always
completes; the consistency/confidence reflect the degradation.

## AMD / GPU

**Q: Why is this a good fit for MI300X specifically?**
At 14B/bf16 the model is ~28 GB, so on a 192 GB MI300X the workload is
**KV-cache-bound, not weight-bound** — we serve the entire 10-call agent fan-out
at high concurrency from one card. We use ROCm CK attention kernels
(`VLLM_USE_TRITON_FLASH_ATTN=0`) and prefix caching of the shared agent system
prompts. Details + memory budget in `docs/AMD_DEPLOYMENT.md`.

**Q: What did you actually tune?**
`gpu-memory-utilization 0.92`, tight `max-model-len 16384`, `max-num-seqs 256`,
chunked prefill, prefix caching, and `enable_thinking=False` to cut output
tokens. Each change and its effect is tabulated in `docs/BENCHMARK_REPORT.md §4`.

**Q: Do you have numbers?**
Yes — `scripts/benchmark_vllm.py` sweeps concurrency and reports req/s, tokens/s,
and p50/p90/p99 + TTFT, writing versioned JSON. The report documents the expected
near-linear scaling to ~128 concurrency. (Run it live on the booth GPU to show
real figures.)

**Q: Which model did you pick and why?**
Qwen3-14B for the pipeline (best throughput-per-quality + Hermes tool calling),
with the option to route just the Judge to Qwen2.5-32B for extra reasoning. Full
comparison in `docs/LLM_EVALUATION.md`, reproducible via `scripts/eval_models.py`.

## Product / impact

**Q: Who uses this and what's the value?**
P&C insurers and reinsurers. Pre-landfall it delivers: expected loss, required
reserve (IBNR + cat buffer), fraud-risk flags, optimal adjuster deployment, and
personalised customer alerts — turning a reactive claims process into proactive
catastrophe management. Reduces leakage (fraud), speeds response (pre-staged
adjusters), and produces a regulator-ready audit trail.

**Q: Is the data real?**
Twins are synthetic (Faker + a calibrated vulnerability model) — privacy-safe and
scalable to 50K. Location data is enriched **live** from OpenStreetMap (areas,
hospitals/shelters) and GDACS (active cyclones), with a static fallback.

**Q: Why digital twins vs. a spreadsheet model?**
Per-property granularity: each twin has construction type, flood zone, elevation,
social vulnerability (infants/elderly/disabled), and prior-claim history — so risk,
fraud, and evacuation are computed at the property level, then aggregated, not
estimated top-down.

## Production readiness

**Q: Could this actually ship?**
The backend is stateless — run multiple uvicorn workers behind a load balancer
against a shared vLLM pool. It ships with liveness/readiness endpoints, Prometheus
metrics, structured logging with request correlation, LangSmith tracing,
retry/failover (vLLM→Anthropic), and CI with security scanning (bandit, pip-audit,
npm audit, Trivy). See `docs/OPERATIONS.md`.

**Q: How do you keep frontend and backend in sync?**
Shared contract types in `frontend/src/types/api.d.ts` mirror the Pydantic
schemas; response models use `extra="allow"` so agent fields are never silently
dropped (this fixed a real schema-drift bug where the frontend was falling back to
synthesised values). The client adds retry/timeout/error normalisation.

## Curveballs

**Q: Show me it's not faked — break it.**
Stop vLLM mid-demo: agents degrade to `[LLM unavailable]`, confidence drops,
consistency still computes — the pipeline completes. Or kill the backend: the
frontend computes locally. Resilience is the demo.

**Q: Biggest limitation?**
The loss/vulnerability model is calibrated, not trained on real claims — a
production deployment would fit it on the insurer's historical book. The
architecture (twins → agents → guardrails) is unchanged; only the coefficients
improve.

**Q: What's next?**
Floods, earthquakes, wildfires; reinsurance optimization; agentic underwriting.
See the roadmap slide.
