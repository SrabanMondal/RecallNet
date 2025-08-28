from __future__ import annotations
from typing import Tuple, List, Dict
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta

from src.core.memory_interface import MemoryInterface
from src.core.llm_interface import LLMInterface
from src.utils.prompting import SUMMARY_SYSTEM_PROMPT


@dataclass
class SummarizerMemory(MemoryInterface):
    """
    Rolling + Time-based hybrid memory:
    - Keeps a rolling buffer of turns (recent + fading summary)
    - Every `window_minutes`, takes a snapshot of the *current rolling summary*
    - Snapshots later can be aggregated into hour/day summaries
    """

    llm: LLMInterface
    window_minutes: int = 2
    max_recent: int = 5

    _turns: deque[Dict] = field(default_factory=lambda: deque(maxlen=6))  # {time, user, ai}
    _summary: str = ""        # rolling compressed summary
    _snapshots: List[Dict] = field(default_factory=list)  # list of {time, summary}
    _last_window: datetime = field(default_factory=datetime.utcnow)

    def add_turn(self, user: str, ai: str) -> None:
        now = datetime.utcnow()
        self._turns.append({"time": now, "user": user, "ai": ai})

        # rolling summarization: fade oldest turn into summary
        if len(self._turns) > self.max_recent:
            oldest = self._turns.popleft()
            self._summary = self._summarize_incremental(oldest)

        # check if snapshot window passed
        if now - self._last_window >= timedelta(minutes=self.window_minutes):
            self._create_snapshot(now)
            self._last_window = now

    def _summarize_incremental(self, turn: Dict) -> str:
        """Update rolling summary with a single old turn"""
        transcript = f"[{turn['time'].isoformat()}]\nUser: {turn['user']}\nAI: {turn['ai']}"
        prompt = (
            f"{SUMMARY_SYSTEM_PROMPT}\n\n"
            f"Existing Summary:\n{self._summary}\n\n"
            f"New Turn:\n{transcript}\n\n"
            f"Update the memory summary now:"
        )
        return self.llm.generate(prompt).strip()

    def _create_snapshot(self, now: datetime) -> None:
        """Freeze current rolling summary into a time-stamped snapshot"""
        if not self._summary:
            return
        self._snapshots.append({
            "time": now.isoformat(),
            "summary": self._summary
        })

    def get_context(self, *, k_recent: int = None) -> str:
        k_recent = k_recent or self.max_recent
        recent = list(self._turns)[-k_recent:]
        recent_txt = "\n".join(
            [f"[{t['time'].isoformat()}]\nUser: {t['user']}\nAI: {t['ai']}" for t in recent]
        )

        parts = []
        if self._summary:
            parts.append(f"[ROLLING SUMMARY]\n{self._summary}")
        if recent:
            parts.append(f"[RECENT TURNS]\n{recent_txt}")
        return "\n\n".join(parts) if parts else ""

    def summary(self) -> str:
        return self._summary

    def snapshots(self) -> List[Dict]:
        """Return all time-based snapshots"""
        return self._snapshots

    def all_turns(self) -> List[Tuple[str, str]]:
        return [(t['user'], t['ai']) for t in self._turns]
