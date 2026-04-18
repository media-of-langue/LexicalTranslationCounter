import json
import os
import time
from contextlib import contextmanager


def _timing_enabled():
    value = os.environ.get("LTC_TIMING", "1").lower()
    return value not in ("0", "false", "no", "off")


class TimingRecorder:
    def __init__(self):
        self.enabled = _timing_enabled()
        self.metadata = {}
        self.stats = {}

    def set_metadata(self, key, value):
        if self.enabled:
            self.metadata[key] = value

    def record(self, name, elapsed_seconds, items=1, metadata=None):
        if not self.enabled:
            return

        stat = self.stats.setdefault(
            name,
            {
                "calls": 0,
                "items": 0,
                "total_seconds": 0.0,
                "min_seconds": None,
                "max_seconds": 0.0,
                "max_metadata": None,
            },
        )

        stat["calls"] += 1
        stat["items"] += items
        stat["total_seconds"] += elapsed_seconds
        if stat["min_seconds"] is None or elapsed_seconds < stat["min_seconds"]:
            stat["min_seconds"] = elapsed_seconds
        if elapsed_seconds > stat["max_seconds"]:
            stat["max_seconds"] = elapsed_seconds
            stat["max_metadata"] = metadata

    def snapshot(self):
        stats = {}
        for name, stat in sorted(self.stats.items()):
            calls = stat["calls"]
            items = stat["items"]
            total = stat["total_seconds"]
            stats[name] = {
                **stat,
                "avg_seconds_per_call": total / calls if calls else None,
                "avg_seconds_per_item": total / items if items else None,
            }
        return {
            "enabled": self.enabled,
            "metadata": self.metadata,
            "stats": stats,
        }

    def dump_json(self, path):
        if not self.enabled:
            return

        with open(path, "w") as f:
            json.dump(self.snapshot(), f, indent=2, sort_keys=True)
            f.write("\n")


TIMER = TimingRecorder()


@contextmanager
def timed(name, items=1, metadata=None):
    if not TIMER.enabled:
        yield
        return

    start = time.perf_counter()
    try:
        yield
    finally:
        TIMER.record(name, time.perf_counter() - start, items=items, metadata=metadata)
