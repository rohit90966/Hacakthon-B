"""Performance metrics collector."""
from __future__ import annotations

import time
from typing import Dict


class Metrics:
    def __init__(self):
        self.counters = {
            "requests_total": 0,
            "validation_pass": 0,
            "validation_fail": 0,
            "hallucination_rejections": 0,
            "batch_requests": 0,
        }
        self.durations = {
            "generation_latency_ms": [],
        }

    def record_request(self):
        self.counters["requests_total"] += 1

    def record_validation(self, passed: bool):
        key = "validation_pass" if passed else "validation_fail"
        self.counters[key] += 1

    def record_hallucination_rejection(self):
        self.counters["hallucination_rejections"] += 1

    def record_batch(self):
        self.counters["batch_requests"] += 1

    def record_latency(self, ms: float):
        self.durations["generation_latency_ms"].append(ms)

    def snapshot(self) -> Dict[str, object]:
        avg_latency = 0.0
        latencies = self.durations.get("generation_latency_ms", [])
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
        return {
            "counters": self.counters,
            "average_latency_ms": round(avg_latency, 2),
        }


metrics = Metrics()


def timed(fn):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = fn(*args, **kwargs)
        end = time.time()
        metrics.record_latency((end - start) * 1000)
        return result

    return wrapper
