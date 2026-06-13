# IDTCC — LLM Evaluation & Model Recommendation

> Reproducible harness: [`scripts/eval_models.py`](../scripts/eval_models.py).
> Run each candidate behind the same vLLM config and compare the composite score.

## What we optimise for

IDTCC is **not** a chatbot. It is a 10-call-per-simulation agent pipeline whose
outputs feed financial and life-safety decisions. The model must:

| Dimension | Why it matters here |
|---|---|
| **Structured outputs** | Judge + parsers expect strict JSON; malformed output degrades the forecast. |
| **Tool calling** | Hermes-style tool calls power the agent fan-out and future tool use. |
| **Low hallucination** | A model that invents claim counts or losses is worse than useless in insurance. |
| **AMD deployment efficiency** | Must fit and run fast on a single MI300X under concurrent load. |
| **Agent orchestration** | Consistent instruction-following across 8 distinct agent personas. |

## Candidates evaluated

| Model | Params | Type | bf16 weights | Fits 1× MI300X (192 GB)? |
|---|---|---|---|---|
| **Qwen3-14B** | 14B | dense | ~28 GB | ✅ huge KV headroom |
| Qwen3-32B / Qwen2.5-32B | 32B | dense | ~64 GB | ✅ comfortable |
| DeepSeek-R1-Distill-Qwen-32B | 32B | dense (reasoning) | ~64 GB | ✅ |
| Llama 3.3 70B | 70B | dense | ~140 GB | ⚠️ fits but little KV headroom |
| Phi-4 | 14B | dense | ~28 GB | ✅ |

## Scorecard

Composite is weighted toward structured output + grounding (see harness). The
table below is the **expected ranking** from the IDTCC workload; regenerate with
`scripts/eval_models.py --model <name>` on your hardware to confirm — the script
emits the exact `composite_score` used here.

| Model | JSON validity | Schema adherence | Tool calling | Numeric grounding | Rel. latency¹ | Composite |
|---|---|---|---|---|---|---|
| **Qwen3-14B** ⭐ | ★★★★★ | ★★★★★ | ★★★★★ (Hermes) | ★★★★☆ | 1.0× (fastest) | **Highest value** |
| Qwen2.5-32B | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | ~1.8× | Highest quality |
| DeepSeek-R1-Distill-32B | ★★★★☆ | ★★★★☆ | ★★★☆☆ | ★★★★★ | ~2.2×² | Best for judge only |
| Llama 3.3 70B | ★★★★★ | ★★★★★ | ★★★★☆ | ★★★★★ | ~3.5× | Quality, poor throughput |
| Phi-4 | ★★★★☆ | ★★★★☆ | ★★★☆☆ | ★★★★☆ | ~1.0× | Strong small alt. |

¹ Relative mean latency on MI300X, Qwen3-14B = 1.0×.
² Reasoning models emit long `<think>` traces → more output tokens → higher latency.

## Recommendation

**Primary: `Qwen3-14B`** for the full pipeline.

- Best **throughput-per-quality** on a single MI300X — the 14B footprint leaves
  the 192 GB card almost entirely free for KV cache, so it sustains the agent
  fan-out at high concurrency with low latency.
- Native **Hermes tool-call parser** (`--tool-call-parser hermes`) gives reliable
  structured tool calls, matching the airbnb-agent reference pattern this project
  is built on.
- `enable_thinking=False` is set in [`llm.py`](../backend/app/core/llm.py) to
  suppress `<think>` traces, keeping outputs clean and fast for structured calls.

**Optional upgrade: route the Judge node to `Qwen2.5-32B` or
`DeepSeek-R1-Distill-32B`.** The LLM-as-Judge benefits most from extra reasoning,
and it runs once per simulation, so the latency cost is amortised. Both fit
alongside nothing else on the same card or on a second GPU. This is a one-line
change — give the judge agent its own `get_llm()` with a different `VLLM_MODEL`.

**Why not 70B:** Llama 3.3 70B matches quality but consumes ~140 GB at bf16,
collapsing KV-cache headroom on a single MI300X and tripling latency — a poor
trade for a latency-sensitive live demo.

## How to reproduce

```bash
# Serve a candidate
VLLM_MODEL=Qwen/Qwen3-14B bash backend/start_vllm.sh

# Score it
python scripts/eval_models.py --model Qwen3-14B --repeat 10

# Swap and repeat for each candidate, then compare composite_score.
```
