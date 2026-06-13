#!/usr/bin/env python3
"""Model evaluation harness for IDTCC agent orchestration.

Scores a candidate model on the dimensions that matter for this platform:

  1. json_validity        — fraction of responses that parse as JSON
  2. schema_adherence     — required keys present with correct types
  3. tool_calling         — emits a valid tool call when asked
  4. numeric_grounding    — stays inside stated numeric bounds (anti-hallucination)
  5. latency              — mean seconds/response

Point it at any OpenAI-compatible endpoint and swap --model to compare
Qwen3-14B / Qwen3-32B / DeepSeek-R1-Distill / Llama-3.3 / Phi-4. Results feed
docs/LLM_EVALUATION.md.

    python scripts/eval_models.py --model Qwen3-14B
    python scripts/eval_models.py --model Qwen2.5-32B-Instruct
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from typing import Any, Callable

import httpx


def extract_json(raw: str) -> dict | None:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    cand = fenced.group(1) if fenced else None
    if cand is None:
        i = raw.find("{")
        if i == -1:
            return None
        depth = 0
        for j in range(i, len(raw)):
            depth += (raw[j] == "{") - (raw[j] == "}")
            if depth == 0:
                cand = raw[i:j + 1]
                break
    try:
        return json.loads(re.sub(r",\s*([}\]])", r"\1", cand or ""))
    except (json.JSONDecodeError, TypeError):
        return None


# ── Test cases: (name, system, user, validator) ───────────────────────────────

def _v_judge(d: dict) -> bool:
    return (isinstance(d.get("scores"), dict)
            and isinstance(d.get("overall_score"), (int, float))
            and "verdict" in d)


def _v_weather(d: dict) -> bool:
    return ("severity" in d or "storm_severity_index" in d) and "hazards" in str(d).lower()


def _v_numeric(d: dict) -> bool:
    # Model must not exceed the stated portfolio size (1000) — anti-hallucination.
    val = d.get("red_count") or d.get("red_twins") or 0
    try:
        return 0 <= float(val) <= 1000
    except (TypeError, ValueError):
        return False


CASES: list[tuple[str, str, str, Callable[[dict], bool]]] = [
    ("schema_judge",
     "You are an insurance auditor. Return ONLY JSON.",
     'Score forecast. Return {"scores": {"factual_accuracy": n}, "overall_score": n, "verdict": "APPROVED|REJECTED"}.',
     _v_judge),
    ("schema_weather",
     "You are a meteorologist. Return ONLY JSON.",
     'Cyclone 180km/h. Return {"severity": 0-10, "hazards": ["..."]}',
     _v_weather),
    ("numeric_grounding",
     "Return ONLY JSON. Use ONLY the numbers given; never invent counts.",
     'Portfolio has exactly 1000 properties; 230 are high risk. Return {"red_count": n}',
     _v_numeric),
]

TOOL_PROMPT = {
    "system": "You can call tools. Use the provided function when relevant.",
    "user": "What is the storm surge risk for a 200 km/h cyclone at Chennai?",
    "tools": [{
        "type": "function",
        "function": {
            "name": "get_storm_surge",
            "description": "Estimate storm surge height in metres for a cyclone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wind_kmh": {"type": "number"},
                    "location": {"type": "string"},
                },
                "required": ["wind_kmh", "location"],
            },
        },
    }],
}


def chat(client: httpx.Client, url: str, model: str, headers: dict,
         system: str, user: str, tools: list | None = None) -> tuple[Any, float]:
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": 300,
        "temperature": 0.2,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    t0 = time.perf_counter()
    r = client.post(url, json=body, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json(), time.perf_counter() - t0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1"))
    ap.add_argument("--model", default=os.getenv("VLLM_MODEL", "Qwen3-14B"))
    ap.add_argument("--api-key", default=os.getenv("VLLM_API_KEY", "abc-123"))
    ap.add_argument("--repeat", type=int, default=5, help="runs per case")
    args = ap.parse_args()

    url = args.base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {args.api_key}"}
    results: dict[str, Any] = {"model": args.model, "cases": {}}
    latencies: list[float] = []

    with httpx.Client() as client:
        # Structured-output + grounding cases.
        for name, system, user, validate in CASES:
            valid_json = passed = 0
            for _ in range(args.repeat):
                try:
                    resp, dt = chat(client, url, args.model, headers, system, user)
                    latencies.append(dt)
                    text = resp["choices"][0]["message"]["content"] or ""
                    parsed = extract_json(text)
                    if parsed is not None:
                        valid_json += 1
                        if validate(parsed):
                            passed += 1
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! {name}: {exc}")
            results["cases"][name] = {
                "json_validity": round(valid_json / args.repeat, 3),
                "schema_adherence": round(passed / args.repeat, 3),
            }

        # Tool-calling case.
        tool_ok = 0
        for _ in range(args.repeat):
            try:
                resp, dt = chat(client, url, args.model, headers,
                                TOOL_PROMPT["system"], TOOL_PROMPT["user"], TOOL_PROMPT["tools"])
                latencies.append(dt)
                msg = resp["choices"][0]["message"]
                calls = msg.get("tool_calls") or []
                if calls and calls[0]["function"]["name"] == "get_storm_surge":
                    args_json = extract_json(calls[0]["function"].get("arguments", "{}"))
                    if args_json and "wind_kmh" in args_json:
                        tool_ok += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  ! tool_calling: {exc}")
        results["cases"]["tool_calling"] = {"success_rate": round(tool_ok / args.repeat, 3)}

    results["mean_latency_s"] = round(sum(latencies) / len(latencies), 3) if latencies else 0
    # Composite score (0-1): weighted toward structured output + grounding.
    c = results["cases"]
    composite = (
        0.30 * c["schema_judge"]["schema_adherence"]
        + 0.20 * c["schema_weather"]["schema_adherence"]
        + 0.20 * c["numeric_grounding"]["schema_adherence"]
        + 0.20 * c["tool_calling"]["success_rate"]
        + 0.10 * (sum(cc.get("json_validity", 0) for cc in c.values() if "json_validity" in cc) / 3)
    )
    results["composite_score"] = round(composite, 3)

    print("\n" + json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
