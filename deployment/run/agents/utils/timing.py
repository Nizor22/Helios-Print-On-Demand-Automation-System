from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def stopwatch() -> Iterator[dict[str, float]]:
    start = time.perf_counter()
    metrics: dict[str, float] = {}
    try:
        yield metrics
    finally:
        metrics["elapsed_s"] = time.perf_counter() - start
