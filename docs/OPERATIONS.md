# IDTCC — Operations Guide

## 1. Service topology

| Service | Port | Scales | State |
|---|---|---|---|
| vLLM (MI300X) | 8001 | vertical first, then replicas / tensor-parallel | model weights + KV cache |
| FastAPI backend | 8000 | horizontal (more uvicorn workers / instances) | **stateless** |
| Frontend (static) | 5173 | horizontal (any static host / CDN) | static |

## 2. Health & probes

| Endpoint | Use |
|---|---|
| `/health/live` | Liveness — restart the process if failing. |
| `/health/ready` | Readiness — returns `503` until the LangGraph is compiled; gates load-balancer traffic. |
| `/metrics` | Prometheus scrape (app layer). |
| `:8001/metrics` | vLLM scrape (KV cache, queue depth, tokens/s). |

Wire these into your process supervisor (systemd/supervisor) and load-balancer
health checks — point the LB at `/health/ready`.

## 3. Monitoring — the four signals

| Signal | Source metric | Where |
|---|---|---|
| Throughput | `idtcc_http_requests_total`, vLLM tokens/s | `/metrics`, `:8001/metrics` |
| Latency | `idtcc_http_request_duration_seconds`, `idtcc_agent_latency_seconds` | `/metrics` |
| Success rate | `idtcc_agent_runs_total` vs `idtcc_agent_errors_total` | `/metrics`, `/api/v1/metrics/summary` |
| Token consumption | `idtcc_llm_tokens_total` (per agent) | `/metrics` |

LLM-level tracing (per-prompt latency, tokens, prompt versions) is in **LangSmith**
— set `LANGCHAIN_API_KEY` and view `smith.langchain.com` → project `idtcc-production`.

Suggested Prometheus alerts:

```promql
# Agent error budget burn
sum(rate(idtcc_agent_errors_total[5m])) / sum(rate(idtcc_agent_runs_total[5m])) > 0.05
# Backend p99 latency
histogram_quantile(0.99, sum(rate(idtcc_http_request_duration_seconds_bucket[5m])) by (le)) > 8
# Readiness flapping → vLLM unreachable
up{job="idtcc-vllm"} == 0
```

## 4. Logging

Structured logs (`JSON_LOGS=true`) with a `request_id` on every line — grep one
simulation end-to-end across all agents. Ship stdout to Loki/ELK/CloudWatch.
Noisy third-party loggers are pinned to WARNING.

## 5. Scaling playbook

| Pressure | Action |
|---|---|
| Backend CPU high | Add uvicorn `--workers` / run more backend instances behind the LB. |
| Inference queue depth rising | Raise vLLM `--max-num-seqs`; then add a vLLM replica behind an LB. |
| KV-cache full (`:8001/metrics`) | Lower `--max-model-len`, or add a GPU. |
| Larger model needed | `--tensor-parallel-size N`. |

The backend holds no session state, so scaling out is just starting more
instances behind the load balancer.

## 6. Disaster recovery

| Failure | Behaviour / response |
|---|---|
| **vLLM down** | Agents degrade gracefully (narrative = `[LLM unavailable]`, confidence drops); set `LLM_PROVIDER=anthropic` to fail over to cloud. Frontend falls back to local computation. |
| **Backend down** | Frontend computes locally (`IDTCCContext.jsx`) — UI stays usable; restart the backend process. |
| **LangSmith down** | Tracing is best-effort; pipeline unaffected. |
| **OSM/GDACS down** | Location enrichment falls back to the static catalogue automatically. |
| **Partial agent failure** | `@instrument` returns a degraded envelope; pipeline completes; consistency score reflects it. |

**Backups:** the platform is stateless and deterministic (seeded) — there is no
primary datastore to back up. To reproduce any past forecast, replay the original
`SimulationRequest` (log it). Persist `/api/v1/metrics/summary` snapshots if you
need historical KPIs.

## 7. Runbooks

**"Readiness stuck at 503"** → graph failed to compile; check backend logs for an
import/agent error at `startup`. **"All confidences low / consistency failing"** →
likely vLLM unreachable; check `:8001/health` and `LLM_PROVIDER`. **"High p99"** →
inspect `idtcc_agent_latency_seconds` per agent; the judge + alerts agents make the
most LLM calls.
