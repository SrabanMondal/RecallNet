from datetime import datetime
from typing import List, Dict
from src.core.llm_interface import LLMInterface
from src.utils.prompting import SUMMARY_SYSTEM_PROMPT

class SnapshotAggregator:
    def __init__(self, llm: LLMInterface):
        self.llm = llm
        self._hourly: Dict[str, str] = {}  # {hour: summary}
        self._daily: Dict[str, str] = {}   # {day: summary}

    def aggregate_hourly(self, snapshots: List[Dict]) -> None:
        """Group snapshots by hour, merge into compact hourly summary"""
        # snapshots already have iso timestamps
        grouped = {}
        for snap in snapshots:
            hour = snap["time"][:13]  # yyyy-mm-ddTHH
            grouped.setdefault(hour, []).append(snap["summary"])

        for hour, chunks in grouped.items():
            merged = "\n".join(chunks)
            prompt = (
                f"{SUMMARY_SYSTEM_PROMPT}\n\n"
                f"Existing Hour Summary:\n{self._hourly.get(hour, '')}\n\n"
                f"Snapshots:\n{merged}\n\n"
                f"Update the hourly memory summary:"
            )
            self._hourly[hour] = self.llm.generate(prompt).strip()

    def aggregate_daily(self) -> None:
        """Group hourly summaries into daily memory"""
        grouped = {}
        for hour, summary in self._hourly.items():
            day = hour[:10]  # yyyy-mm-dd
            grouped.setdefault(day, []).append(summary)

        for day, chunks in grouped.items():
            merged = "\n".join(chunks)
            prompt = (
                f"{SUMMARY_SYSTEM_PROMPT}\n\n"
                f"Existing Daily Summary:\n{self._daily.get(day, '')}\n\n"
                f"Hourly Summaries:\n{merged}\n\n"
                f"Update the daily memory summary:"
            )
            self._daily[day] = self.llm.generate(prompt).strip()

    def get_daily_summary(self, day: str = None) -> str:
        if not day:
            day = datetime.utcnow().date().isoformat()
        return self._daily.get(day, "")
    
    def merge_hour(self, prev_hour_key: str, hour_snapshots: List[Dict]) -> str:
        """Continuity-aware merge: prev hour summary + this hour's snapshots."""
        prev = self.hourly.get(prev_hour_key, "")
        chunks = "\n".join([s["summary"] for s in hour_snapshots])

        prompt = (
            f"{SUMMARY_SYSTEM_PROMPT}\n\n"
            f"Previous Hour Summary (may be empty):\n{prev}\n\n"
            f"Current Hour Snapshots:\n{chunks}\n\n"
            "Update/compose the hour summary:\n"
            "- Merge related points; maintain timeline.\n"
            "- Carry forward [ONGOING] items; mark [RESOLVED]/[CANCELLED] if applicable.\n"
            "- Keep it compact and factual."
        )
        return self.llm.generate(prompt).strip()

    def merge_day(self, day_key: str) -> str:
        hours = [k for k in self.hourly.keys() if k.startswith(day_key)]
        hours.sort()
        merged = "\n".join([self.hourly[h] for h in hours])
        prompt = (
            f"{SUMMARY_SYSTEM_PROMPT}\n\n"
            f"Hourly Summaries for {day_key}:\n{merged}\n\n"
            "Create the daily memory (big-picture, decisions, preferences, [ONGOING]):"
        )
        return self.llm.generate(prompt).strip()
