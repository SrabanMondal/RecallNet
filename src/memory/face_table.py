"""
Fact Table for AI Memory System
--------------------------------
This module defines the fact table for the memory system in a structured way.
It acts as a single source of truth for entities, their scope, lifecycle, and usage.
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class MemoryEntity:
    name: str
    granularity: str
    source: str
    storage_form: str
    lifecycle: str
    usage: str


# Define all entities of the memory system
FACT_TABLE: List[MemoryEntity] = [
    MemoryEntity(
        name="Turn",
        granularity="Single user–AI exchange",
        source="Conversation engine",
        storage_form="JSON rows (user, ai, timestamp)",
        lifecycle="Only last N=5 stored",
        usage="For recency, freshness"
    ),
    MemoryEntity(
        name="Rolling Summary",
        granularity="Compressed running state of past turns",
        source="LLM incremental summarization",
        storage_form="String (updated continuously)",
        lifecycle="Always current (overwrite)",
        usage="For context injection (short history)"
    ),
    MemoryEntity(
        name="Snapshot",
        granularity="Point-in-time capture of rolling summary",
        source="SummarizerMemory _create_snapshot",
        storage_form="JSON list {time, summary}",
        lifecycle="Collect until hour boundary → then popped",
        usage="For temporal anchoring (minute–level)"
    ),
    MemoryEntity(
        name="Hour Memory",
        granularity="Aggregated block of snapshots within the hour",
        source="Aggregator + LLM compression",
        storage_form="JSON {hour, summary}",
        lifecycle="Keep persistent (do not pop)",
        usage="Mid-term context (balanced depth)"
    ),
    MemoryEntity(
        name="Day Memory",
        granularity="Aggregated block of hour memories per day",
        source="Aggregator + LLM compression",
        storage_form="JSON {date, summary}",
        lifecycle="Generated daily, keep persistent",
        usage="Long-term story flow"
    ),
    MemoryEntity(
        name="Persistence State",
        granularity="Current in-RAM state to disk",
        source="File DB (JSON/SQLite)",
        storage_form="JSON/SQL tables",
        lifecycle="Written on checkpoint/exit",
        usage="Reload on restart"
    ),
    MemoryEntity(
        name="Vector Store Docs",
        granularity="Embedding representation of memories",
        source="Hour/Day memories (raw or notes)",
        storage_form="Vector index",
        lifecycle="Append-only (no update)",
        usage="Semantic retrieval"
    ),
    MemoryEntity(
        name="Continuity Blocks",
        granularity="Rolling merge of prev hour + current hour snapshots",
        source="Aggregator + LLM merge",
        storage_form="JSON {hour, merged_summary}",
        lifecycle="Replace prev block each new hour",
        usage="To preserve narrative continuity"
    ),
]


def as_dict() -> List[Dict]:
    """Export the fact table as a list of dictionaries."""
    return [entity.__dict__ for entity in FACT_TABLE]


if __name__ == "__main__":
    # Pretty print fact table for quick inspection
    from pprint import pprint
    pprint(as_dict())
