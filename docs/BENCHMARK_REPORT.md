# IDTCC — vLLM Benchmark Report (AMD MI300X)

> **Methodology note.** The numbers in §3 are **reference projections** for a
> single MI300X serving the IDTCC judge-style structured-output prompt. They are
> the expected output of [`scripts/benchmark_vllm.py`](../scripts/benchmark_vllm.py).
> Run that script on your hardware to produce authoritative figures — it writes
> JSON to `docs/benchmarks/` so results are versioned and diffable. Do not quote
> §3 as measured numbers without a confirming run.

## 1. Workload profile

IDTCC issues **~10 LLM calls per simulation** (7 agents + judge × 3 + executive
summary), each a short structured-output request (≤300 output tokens). The
profile is **bursty and concurrency-heavy**, not a single long stream — so the
benchmark sweeps concurrency rather than measuring a single request.

- Prompt: judge-equivalent (system + ~120-token user, 200 max output tokens)
- Datatype: bf16, model Qwen3-14B
- Tuning: per [`start_vllm.sh`](../backend/start_vllm.sh) (`gpu-mem-util 0.92`,
  `max-num-seqs 256`, prefix caching on)

## 2. How to run

```bash
python scripts/benchmark_vllm.py \
    --base-url http://localhost:8001/v1 \
    --model Qwen3-14B --api-key abc-123 \
    --concurrency 1 8 32 64 128 256 --requests 512
```

## 3. Reference results (projected — confirm on hardware)

| Concurrency | Throughput (req/s) | Output tok/s | p50 (s) | p90 (s) | p99 (s) | TTFT p50 (s) | Success |
|---|---|---|---|---|---|---|---|
| 1   |  3–5    |   60–110   | 0.2–0.3 | 0.3 | 0.4 | 0.05 | 100% |
| 8   |  25–35  |   500–800  | 0.25    | 0.4 | 0.6 | 0.06 | 100% |
| 32  |  90–130 | 1,800–2,600| 0.30    | 0.5 | 0.8 | 0.08 | 100% |
| 64  | 150–220 | 3,000–4,400| 0.40    | 0.7 | 1.1 | 0.10 | 100% |
| 128 | 230–320 | 4,600–6,400| 0.55    | 1.0 | 1.6 | 0.14 | 100% |
| 256 | 280–380 | 5,600–7,600| 0.85    | 1.6 | 2.6 | 0.20 | ~100% |

**Interpretation**

- Throughput scales near-linearly to ~128 concurrency, then KV-cache pressure
  begins to flatten gains — the expected knee for a 14B model on one MI300X.
- TTFT stays well under the demo's interactive threshold even at high load,
  thanks to chunked prefill + prefix caching of the shared agent system prompts.
- A full IDTCC simulation's 10 calls complete comfortably within a few seconds
  end-to-end at demo concurrency.

## 4. Optimization impact (before → after tuning)

| Change | Effect |
|---|---|
| Default util 0.90 → **0.92** + tight `max-model-len` | More KV slots → higher max concurrency before queueing. |
| **Prefix caching on** | Shared agent system prompts cached once; prefill cost amortised across all calls in a run. |
| **Chunked prefill on** | Lower p99 under mixed prefill/decode load. |
| ROCm CK kernels (`TRITON_FLASH_ATTN=0`) | Faster attention on MI300X head dims. |
| `enable_thinking=False` (Qwen3) | Fewer output tokens per call → lower latency, higher req/s. |

## 5. Application-layer metrics

Beyond GPU throughput, the backend exposes per-agent latency, token consumption,
and success rate at `/metrics` (Prometheus) and `/api/v1/metrics/summary` (JSON).
Correlate these with vLLM's `:8001/metrics` (KV-cache usage, queue depth) for a
full-stack view during load.
