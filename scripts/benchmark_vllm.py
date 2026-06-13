#!/usr/bin/env python3
"""vLLM throughput / latency benchmark for the IDTCC agent workload.

Runs a representative structured-output prompt at increasing concurrency levels
against an OpenAI-compatible endpoint (vLLM on MI300X) and reports:

  - throughput (req/s and output tokens/s)
  - latency percentiles (p50 / p90 / p99)
  - time-to-first-token (streaming)
  - success rate

Usage:
    python scripts/benchmark_vllm.py \
        --base-url http://localhost:8001/v1 \
        --model Qwen3-14B --api-key abc-123 \
        --concurrency 1 8 32 64 128 --requests 256

Results are written to docs/benchmarks/<model>-<timestamp>.json so they can be
diffed across tuning runs. Requires: httpx  (already in requirements.txt).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# A prompt that mirrors the judge agent — the heaviest structured-output call.
SYSTEM = "You are an insurance risk auditor. Return ONLY compact JSON."
USER = (
    "Score this catastrophe forecast 0-10 on factual_accuracy, completeness, "
    "actionability, financial_soundness. Cyclone NIVAR, 180km/h, Chennai, "
    "12,400 red properties, expected loss 842 Cr, reserve 1204 Cr. "
    'Return {"scores": {...}, "overall_score": n, "verdict": "..."}'
)


async def _one(client: httpx.AsyncClient, url: str, model: str, headers: dict) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": USER}],
        "max_tokens": 200,
        "temperature": 0.2,
        "stream": True,
    }
    t0 = time.perf_counter()
    ttft = None
    out_tokens = 0
    try:
        async with client.stream("POST", url, json=body, headers=headers, timeout=120) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                if ttft is None:
                    ttft = time.perf_counter() - t0
                try:
                    delta = json.loads(payload)["choices"][0].get("delta", {})
                    if delta.get("content"):
                        out_tokens += 1
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass
        return {"ok": True, "latency": time.perf_counter() - t0,
                "ttft": ttft or 0.0, "out_tokens": out_tokens}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "latency": time.perf_counter() - t0, "error": str(exc)}


async def run_level(base_url: str, model: str, headers: dict,
                    concurrency: int, n_requests: int) -> dict:
    url = base_url.rstrip("/") + "/chat/completions"
    limits = httpx.Limits(max_connections=concurrency + 8)
    results: list[dict] = []
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(limits=limits) as client:
        async def _task():
            async with sem:
                results.append(await _one(client, url, model, headers))

        wall0 = time.perf_counter()
        await asyncio.gather(*[_task() for _ in range(n_requests)])
        wall = time.perf_counter() - wall0

    ok = [r for r in results if r["ok"]]
    lat = sorted(r["latency"] for r in ok) or [0]
    ttfts = sorted(r["ttft"] for r in ok) or [0]
    total_out = sum(r.get("out_tokens", 0) for r in ok)

    def pct(data, p):
        if not data:
            return 0.0
        k = max(0, min(len(data) - 1, int(round(p / 100 * (len(data) - 1)))))
        return round(data[k], 3)

    return {
        "concurrency": concurrency,
        "requests": n_requests,
        "success": len(ok),
        "success_rate": round(len(ok) / n_requests, 4) if n_requests else 0,
        "wall_seconds": round(wall, 2),
        "throughput_req_s": round(len(ok) / wall, 2) if wall else 0,
        "output_tokens_per_s": round(total_out / wall, 1) if wall else 0,
        "latency_p50_s": pct(lat, 50),
        "latency_p90_s": pct(lat, 90),
        "latency_p99_s": pct(lat, 99),
        "ttft_p50_s": pct(ttfts, 50),
        "mean_latency_s": round(statistics.mean(lat), 3) if ok else 0,
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1"))
    ap.add_argument("--model", default=os.getenv("VLLM_MODEL", "Qwen3-14B"))
    ap.add_argument("--api-key", default=os.getenv("VLLM_API_KEY", "abc-123"))
    ap.add_argument("--concurrency", nargs="+", type=int, default=[1, 8, 32, 64, 128])
    ap.add_argument("--requests", type=int, default=256)
    args = ap.parse_args()

    headers = {"Authorization": f"Bearer {args.api_key}"}
    print(f"Benchmarking {args.model} @ {args.base_url}\n")
    print(f"{'conc':>5} {'req/s':>8} {'tok/s':>8} {'p50':>7} {'p90':>7} {'p99':>7} {'ttft':>7} {'ok%':>6}")
    print("-" * 60)

    levels = []
    for c in args.concurrency:
        res = await run_level(args.base_url, args.model, headers, c, args.requests)
        levels.append(res)
        print(f"{res['concurrency']:>5} {res['throughput_req_s']:>8} "
              f"{res['output_tokens_per_s']:>8} {res['latency_p50_s']:>7} "
              f"{res['latency_p90_s']:>7} {res['latency_p99_s']:>7} "
              f"{res['ttft_p50_s']:>7} {res['success_rate']*100:>5.1f}")

    out = {
        "model": args.model,
        "base_url": args.base_url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "requests_per_level": args.requests,
        "levels": levels,
    }
    out_dir = Path(__file__).resolve().parent.parent / "docs" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = out_dir / f"{args.model.replace('/', '_')}-{stamp}.json"
    out_file.write_text(json.dumps(out, indent=2))
    print(f"\nSaved → {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
