"""Local-only HTTP load generator for 荣小账.

The script intentionally refuses non-local targets by default. Do not point it
at production without an approved staging window and an explicit
``--allow-remote`` flag.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import time
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

SCENARIOS = {
    "auth_me": ("GET", "/auth/me", 2),
    "ledgers": ("GET", "/ledgers", 3),
    "bills_list": ("GET", "/bills?ledger_id=1&page=1&page_size=20", 4),
    "bill_detail": ("GET", "/bills/6", 2),
    "stats_overview": ("GET", "/stats/overview?ledger_id=1&year=2026&month=7", 3),
    "stats_category": ("GET", "/stats/category?ledger_id=1&year=2026&month=7", 2),
    "budget_status": ("GET", "/budgets/status?ledger_id=1&year=2026&month=7", 2),
}


@dataclass
class Result:
    attempts: int = 0
    latencies: list[float] = field(default_factory=list)
    errors: int = 0
    timeouts: int = 0
    status_counts: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    scenario_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    started: float = 0.0
    finished: float = 0.0


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((p / 100) * (len(ordered) - 1))))
    return ordered[index]


async def login(client: httpx.AsyncClient, base_url: str) -> str:
    response = await client.post(
        f"{base_url}/auth/dev-login",
        json={"nickname": "loadtest"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


async def run_stage(
    base_url: str,
    token: str,
    concurrency: int,
    duration: int,
) -> Result:
    result = Result(started=time.perf_counter())
    deadline = result.started + duration
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(
        base_url=base_url,
        headers=headers,
        timeout=httpx.Timeout(10.0),
        limits=httpx.Limits(
            max_connections=concurrency + 10,
            max_keepalive_connections=concurrency + 10,
        ),
        trust_env=False,
    ) as client:
        async def worker() -> None:
            while time.perf_counter() < deadline:
                name = random.choices(
                    list(SCENARIOS),
                    weights=[item[2] for item in SCENARIOS.values()],
                    k=1,
                )[0]
                method, path, _ = SCENARIOS[name]
                result.attempts += 1
                started = time.perf_counter()
                try:
                    response = await client.request(method, path)
                    elapsed = (time.perf_counter() - started) * 1000
                    result.latencies.append(elapsed)
                    result.status_counts[response.status_code] += 1
                    result.scenario_counts[name] += 1
                    if response.status_code >= 400:
                        result.errors += 1
                except httpx.TimeoutException:
                    result.timeouts += 1
                    result.errors += 1
                except httpx.HTTPError:
                    result.errors += 1

        await asyncio.gather(*(worker() for _ in range(concurrency)))

    result.finished = time.perf_counter()
    return result


def summarize(result: Result) -> dict:
    total = result.attempts
    duration = max(0.001, result.finished - result.started)
    return {
        "requests": total,
        "success": total - result.errors,
        "errors": result.errors,
        "timeouts": result.timeouts,
        "error_rate_percent": round((result.errors / total) * 100, 3) if total else 0,
        "timeout_rate_percent": round((result.timeouts / total) * 100, 3) if total else 0,
        "tps": round(total / duration, 2),
        "avg_ms": round(statistics.fmean(result.latencies), 1) if result.latencies else 0,
        "p50_ms": round(percentile(result.latencies, 50), 1),
        "p95_ms": round(percentile(result.latencies, 95), 1),
        "p99_ms": round(percentile(result.latencies, 99), 1),
        "max_ms": round(max(result.latencies), 1) if result.latencies else 0,
        "status_counts": dict(result.status_counts),
        "scenario_counts": dict(result.scenario_counts),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--stages", default="10,50,100,200,500")
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--allow-remote", action="store_true")
    args = parser.parse_args()

    host = (urlparse(args.base_url).hostname or "").lower()
    if host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_remote:
        raise SystemExit("Refusing non-local target without --allow-remote")

    async with httpx.AsyncClient(trust_env=False) as client:
        token = await login(client, args.base_url)
    print(f"target={args.base_url} stages={args.stages} duration={args.duration}s", flush=True)

    report = {"target": args.base_url, "duration_seconds": args.duration, "stages": []}
    for raw in args.stages.split(","):
        concurrency = int(raw)
        print(f"stage={concurrency} starting...", flush=True)
        result = await run_stage(args.base_url, token, concurrency, args.duration)
        summary = summarize(result)
        summary["concurrency"] = concurrency
        report["stages"].append(summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)

    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    output = Path(__file__).parent / "result.json"
    with output.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
