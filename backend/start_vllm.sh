#!/usr/bin/env bash
# start_vllm.sh — Launch vLLM on AMD MI300X (port 8001)
# Mirrors the pattern from build_airbnb_agent_mcp.ipynb (Qwen3 + Hermes tool parser)
# Run this in a separate terminal BEFORE starting the FastAPI backend.

MODEL="${VLLM_MODEL:-Qwen/Qwen3-14B}"
PORT="${VLLM_PORT:-8001}"
API_KEY="${VLLM_API_KEY:-abc-123}"

echo "Starting vLLM server: $MODEL on port $PORT"
echo "FastAPI backend should run on port 8000 (python run.py)"
echo ""

VLLM_USE_TRITON_FLASH_ATTN=0 \
vllm serve "$MODEL" \
    --served-model-name "$(basename $MODEL)" \
    --api-key "$API_KEY" \
    --port "$PORT" \
    --enable-auto-tool-choice \
    --tool-call-parser hermes \
    --trust-remote-code \
    --dtype bfloat16
