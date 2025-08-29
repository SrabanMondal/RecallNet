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
