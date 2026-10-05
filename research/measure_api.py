"""Measure local demo read latency with five authenticated synthetic users."""

import argparse
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx

USERS = ("reviewer", "clinician", "clinician2", "responder", "admin")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * fraction) - 1)], 3)


def measure(base_url: str, password: str, requests_per_user: int) -> dict:
    if requests_per_user < 1:
        raise ValueError("requests_per_user must be positive")

    def exercise(user_id: str) -> list[float]:
        with httpx.Client(base_url=base_url, timeout=5.0) as client:
            login = client.post("/api/v1/sessions", json={"user_id": user_id, "password": password})
            login.raise_for_status()
            durations = []
            for _ in range(requests_per_user):
                started = time.perf_counter()
                response = client.get("/api/v1/cases")
                durations.append((time.perf_counter() - started) * 1000)
                response.raise_for_status()
                if not isinstance(response.json(), list):
                    raise ValueError("unexpected case list schema")
            return durations

    with ThreadPoolExecutor(max_workers=len(USERS)) as pool:
        all_results = list(pool.map(exercise, USERS))
    times = [duration for user_results in all_results for duration in user_results]
    return {
        "measured_at": datetime.now(UTC).isoformat(), "base_url": base_url,
        "users": len(USERS), "requests_per_user": requests_per_user, "samples": len(times),
        "endpoint": "GET /api/v1/cases", "p50_ms": percentile(times, 0.5),
        "p95_ms": percentile(times, 0.95), "max_ms": round(max(times), 3),
        "scope": "authenticated read only; local PostgreSQL demo; excludes model execution and writes",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests-per-user", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    outcome = measure(args.base_url, os.environ.get("DEMO_PASSWORD", "demo12345"), args.requests_per_user)
    rendered = json.dumps(outcome, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
