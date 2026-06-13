"""Lightweight in-process metrics with a Prometheus text exposition endpoint.

Self-contained (no prometheus_client dependency) so it runs anywhere. Tracks
the four signals the operations guide cares about: throughput, latency, success
rate, and token consumption — sliced by agent. GPU metrics are scraped from the
vLLM `/metrics` endpoint separately (see docs/OPERATIONS.md); this module covers
the application layer.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, List, Tuple

# Histogram buckets in seconds — tuned for multi-second agent LLM calls.
_LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)


class _Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        # counters keyed by (name, labels-tuple) -> value
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = defaultdict(float)
        # histograms keyed similarly -> (bucket_counts, sum, count)
        self._hist: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], List] = {}
        # gauges
        self._gauges: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self._start = time.time()

    @staticmethod
    def _key(name: str, labels: Dict[str, str] | None):
        return (name, tuple(sorted((labels or {}).items())))

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            self._counters[self._key(name, labels)] += value

    def gauge(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self._gauges[self._key(name, labels)] = value

    def observe(self, name: str, value: float, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            if key not in self._hist:
                self._hist[key] = [[0] * len(_LATENCY_BUCKETS), 0.0, 0]
            buckets, total, count = self._hist[key]
            for i, b in enumerate(_LATENCY_BUCKETS):
                if value <= b:
                    buckets[i] += 1
            self._hist[key] = [buckets, total + value, count + 1]

    def render(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines: List[str] = []
        with self._lock:
            lines.append("# HELP idtcc_uptime_seconds Process uptime.")
            lines.append("# TYPE idtcc_uptime_seconds gauge")
            lines.append(f"idtcc_uptime_seconds {time.time() - self._start:.1f}")

            seen_help: set[str] = set()
            for (name, labels), val in sorted(self._counters.items()):
                if name not in seen_help:
                    lines.append(f"# TYPE {name} counter")
                    seen_help.add(name)
                lines.append(f"{name}{_fmt_labels(labels)} {val:g}")

            for (name, labels), val in sorted(self._gauges.items()):
                if name not in seen_help:
                    lines.append(f"# TYPE {name} gauge")
                    seen_help.add(name)
                lines.append(f"{name}{_fmt_labels(labels)} {val:g}")

            for (name, labels), (buckets, total, count) in sorted(self._hist.items()):
                if name not in seen_help:
                    lines.append(f"# TYPE {name} histogram")
                    seen_help.add(name)
                cumulative = 0
                for i, b in enumerate(_LATENCY_BUCKETS):
                    cumulative = buckets[i]
                    le_labels = labels + (("le", str(b)),)
                    lines.append(f"{name}_bucket{_fmt_labels(le_labels)} {cumulative:g}")
                inf_labels = labels + (("le", "+Inf"),)
                lines.append(f"{name}_bucket{_fmt_labels(inf_labels)} {count:g}")
                lines.append(f"{name}_sum{_fmt_labels(labels)} {total:g}")
                lines.append(f"{name}_count{_fmt_labels(labels)} {count:g}")

        return "\n".join(lines) + "\n"

    def snapshot(self) -> Dict:
        """JSON-friendly snapshot for /api/v1/metrics/summary."""
        with self._lock:
            agents: Dict[str, Dict] = {}
            for (name, labels), val in self._counters.items():
                ld = dict(labels)
                agent = ld.get("agent")
                if not agent:
                    continue
                a = agents.setdefault(agent, {"runs": 0, "errors": 0, "tokens": 0})
                if name == "idtcc_agent_runs_total":
                    a["runs"] += val
                elif name == "idtcc_agent_errors_total":
                    a["errors"] += val
                elif name == "idtcc_llm_tokens_total":
                    a["tokens"] += val
            for (name, labels), (buckets, total, count) in self._hist.items():
                ld = dict(labels)
                agent = ld.get("agent")
                if agent and name == "idtcc_agent_latency_seconds" and count:
                    agents.setdefault(agent, {"runs": 0, "errors": 0, "tokens": 0})
                    agents[agent]["avg_latency_ms"] = round(total / count * 1000, 1)
            for a in agents.values():
                runs = a.get("runs", 0)
                a["success_rate"] = round((runs - a.get("errors", 0)) / runs, 4) if runs else None
            return {"uptime_seconds": round(time.time() - self._start, 1), "agents": agents}


def _fmt_labels(labels: Tuple[Tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{k}="{v}"' for k, v in labels)
    return "{" + inner + "}"


# Module-level singleton.
METRICS = _Metrics()
