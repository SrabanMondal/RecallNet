# orchestrator.py
from datetime import datetime, timedelta
from typing import Dict, List
from src.memory.summarizer_memory import SummarizerMemory
from src.memory.aggregator import SnapshotAggregator
from src.core.storage_interface import StorageInterface

class MemoryOrchestrator:
    def __init__(self, mem: SummarizerMemory, agg: SnapshotAggregator, store: StorageInterface):
        self.mem = mem
        self.agg = agg
        self.store = store

    def load(self):
        state = self.store.load()
        if not state: return
        self.mem.load_state(state["summarizer"])
        self.agg.hourly = state["aggregator"].get("hourly", {})
        self.agg.daily  = state["aggregator"].get("daily", {})
        self.agg.last_hour_done = state["aggregator"].get("last_hour_done")
        self.agg.last_day_done  = state["aggregator"].get("last_day_done")

    def save(self):
        self.store.save({
            "summarizer": self.mem.state(),
            "aggregator": {
                "hourly": self.agg.hourly,
                "daily":  self.agg.daily,
                "last_hour_done": self.agg.last_hour_done,
                "last_day_done":  self.agg.last_day_done
            },
            "facts": { "table": {} }  # optional for now
        })

    def on_turn_committed(self, now: datetime | None = None):
        """Call after add_turn() completes."""
        now = now or datetime.utcnow()
        # HOUR ROLLOVER
        current_hour_key = now.strftime("%Y-%m-%dT%H")
        if self.agg.last_hour_done != current_hour_key:
            # drain snapshots strictly before current hour start
            hour_start_iso = now.replace(minute=0, second=0, microsecond=0).isoformat()
            drained = self.mem.drain_snapshots_before(hour_start_iso)
            if drained:
                prev_hour_key = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H")
                hour_key = prev_hour_key  # summarizing the just-finished hour
                merged = self.agg.merge_hour(prev_hour_key, drained)
                self.agg.hourly[hour_key] = merged
            self.agg.last_hour_done = current_hour_key

        # DAY ROLLOVER
        current_day_key = now.strftime("%Y-%m-%d")
        if self.agg.last_day_done != current_day_key:
            # finalize previous day
            prev_day_key = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            if any(k.startswith(prev_day_key) for k in self.agg.hourly.keys()):
                self.agg.daily[prev_day_key] = self.agg.merge_day(prev_day_key)
            self.agg.last_day_done = current_day_key

        self.save()
