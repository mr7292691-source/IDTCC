# IDTCC — AMD MI300X Deployment & Tuning Guide

Target: **AMD Instinct MI300X** (192 GB HBM3) on **ROCm 6.x** running **vLLM**.

## 1. Host prerequisites

```bash
rocm-smi                       # confirm GPU(s) visible
rocminfo | grep "Marketing"    # confirm MI300X
# ROCm 6.1+ and a vLLM build with ROCm support (rocm/vllm image or source build)
```

The user running vLLM must be in the `render` and `video` groups and have access
to `/dev/kfd` and `/dev/dri`.

## 2. Launch (tuned)

Use [`backend/start_vllm.sh`](../backend/start_vllm.sh). Key flags and the
reasoning behind each:

| Flag | Value | Why |
|---|---|---|
| `--dtype` | `bfloat16` | Native MI300X datatype; full quality, no quantization needed at 14B–32B. |
| `--gpu-memory-utilization` | `0.92` | Maximises KV cache while leaving headroom for activation spikes on a 192 GB card. |
| `--max-model-len` | `16384` | Covers the largest agent prompt+output; keeping it tight preserves KV slots. |
| `--max-num-seqs` | `256` | The 8-agent fan-out bursts many short requests; high concurrency avoids queueing. |
| `--max-num-batched-tokens` | `8192` | Continuous-batching budget tuned for mixed prefill/decode. |
| `--enable-prefix-caching` | on | Agent **system prompts are identical** across every run → prefix cached once, prefill cost amortised across all 10 calls. |
| `--enable-chunked-prefill` | on | Smooths latency when long prompts interleave with decode. |
| `--tool-call-parser hermes` + `--enable-auto-tool-choice` | — | Reliable structured tool calls for Qwen3. |
| `VLLM_USE_TRITON_FLASH_ATTN=0` | env | Use ROCm CK/flash kernels (faster than Triton path on MI300X for these head dims). |

## 3. Memory budget (MI300X, 192 GB)

| Component | Qwen3-14B bf16 | Qwen2.5-32B bf16 |
|---|---|---|
| Model weights | ~28 GB | ~64 GB |
| Activation / workspace | ~8–12 GB | ~12–18 GB |
| **KV cache (remaining @ 0.92 util)** | **~135 GB** | **~95 GB** |
| Approx. concurrent 16K-token sequences | hundreds | ~150+ |

The takeaway: at 14B the card is **KV-cache-bound, not weight-bound**, so IDTCC
can serve the entire agent pipeline at high concurrency from one GPU.

## 4. Tuning knobs by symptom

| Symptom | Action |
|---|---|
| `CUDA/HIP out of memory` at startup | Lower `--gpu-memory-utilization` to 0.85, or `--max-model-len` to 8192. |
| High p99 latency under load | Lower `--max-num-seqs`; raise `--max-num-batched-tokens`. |
| Throughput plateaus below GPU saturation | Raise `--max-num-seqs`; confirm prefix caching is on. |
| Model too large for one GPU (70B) | Add `--tensor-parallel-size 2`. |
| Reasoning model emits huge outputs | Keep `enable_thinking=False`; cap `max_tokens`. |

## 5. Scaling out

- **Vertical:** one MI300X handles the demo and well beyond. Increase
  `--max-num-seqs` before adding GPUs.
- **Horizontal:** run multiple vLLM replicas behind a load balancer; point
  `VLLM_BASE_URL` at the LB. The FastAPI layer is stateless and scales
  independently — run multiple uvicorn instances (`--workers`) behind a load
  balancer.
- **Tensor parallel:** `--tensor-parallel-size N` for models exceeding one card.

## 6. Verify the deployment

```bash
curl http://localhost:8001/health
curl http://localhost:8001/v1/models -H "Authorization: Bearer abc-123"
python scripts/benchmark_vllm.py --model Qwen3-14B --concurrency 1 32 128
```

GPU telemetry while benchmarking:

```bash
watch -n1 rocm-smi --showuse --showmemuse --showpower
```

vLLM also exposes Prometheus metrics at `:8001/metrics` (queue depth, KV-cache
usage, tokens/s) — scrape alongside the IDTCC backend `/metrics`.
