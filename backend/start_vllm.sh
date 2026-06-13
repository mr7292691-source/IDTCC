#!/usr/bin/env bash
# start_vllm.sh — Launch a tuned vLLM server on AMD MI300X (192 GB HBM3, ROCm).
#
# Run this in a separate terminal BEFORE the FastAPI backend (port 8000).
# Tuning rationale is documented in docs/AMD_DEPLOYMENT.md; the defaults below
# are sized for a single MI300X serving the IDTCC 8-agent workload, which is
# bursty (10 short structured-output calls per simulation) rather than a steady
# chat stream — so we optimise for concurrency + prefix-cache reuse.
set -euo pipefail

MODEL="${VLLM_MODEL:-Qwen/Qwen3-14B}"
SERVED_NAME="${VLLM_SERVED_NAME:-$(basename "$MODEL")}"
PORT="${VLLM_PORT:-8001}"
API_KEY="${VLLM_API_KEY:-abc-123}"

# ── MI300X tuning knobs (override via env) ────────────────────────────────────
# 0.92 leaves headroom for activation spikes on a 192 GB card while maximising
# the KV cache. Drop to 0.85 if you co-locate other processes on the GPU.
GPU_MEM_UTIL="${VLLM_GPU_MEM_UTIL:-0.92}"
# 16K context comfortably covers our largest agent prompt (judge) + outputs.
# Raising max-model-len trades KV-cache slots for longer context — keep it tight.
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-16384}"
# With 192 GB and a 14B model, the KV cache fits hundreds of concurrent seqs;
# 256 saturates the agent fan-out without queueing.
MAX_NUM_SEQS="${VLLM_MAX_NUM_SEQS:-256}"
# Chunked prefill smooths latency when long prompts and decode interleave.
MAX_NUM_BATCHED_TOKENS="${VLLM_MAX_NUM_BATCHED_TOKENS:-8192}"

echo "──────────────────────────────────────────────────────────────"
echo " vLLM on AMD MI300X"
echo "   model            : $MODEL  (served as $SERVED_NAME)"
echo "   port             : $PORT"
echo "   gpu-mem-util     : $GPU_MEM_UTIL"
echo "   max-model-len    : $MAX_MODEL_LEN"
echo "   max-num-seqs     : $MAX_NUM_SEQS"
echo "   batched-tokens   : $MAX_NUM_BATCHED_TOKENS"
echo "──────────────────────────────────────────────────────────────"

# VLLM_USE_TRITON_FLASH_ATTN=0 → use ROCm CK/flash kernels, which are faster on
# MI300X for these head dims than the Triton path.
VLLM_USE_TRITON_FLASH_ATTN=0 \
NCCL_MIN_NCHANNELS=112 \
vllm serve "$MODEL" \
    --served-model-name "$SERVED_NAME" \
    --api-key "$API_KEY" \
    --port "$PORT" \
    --dtype bfloat16 \
    --gpu-memory-utilization "$GPU_MEM_UTIL" \
    --max-model-len "$MAX_MODEL_LEN" \
    --max-num-seqs "$MAX_NUM_SEQS" \
    --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS" \
    --enable-prefix-caching \
    --enable-chunked-prefill \
    --enable-auto-tool-choice \
    --tool-call-parser hermes \
    --trust-remote-code

# Notes:
#  --enable-prefix-caching   : agent system prompts are identical across every
#                              simulation → the shared prefix is cached once,
#                              cutting prefill cost for all 10 calls/run.
#  --tensor-parallel-size N  : add for models that exceed one GPU's memory
#                              (e.g. Qwen2.5-32B at bf16 ≈ 64 GB still fits one
#                              MI300X; only needed for 70B+).
