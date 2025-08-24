from __future__ import annotations
from typing import Tuple
from dataclasses import dataclass, field
from collections import deque

from src.core.memory_interface import MemoryInterface
from src.core.llm_interface import LLMInterface
from src.utils.prompting import SUMMARY_SYSTEM_PROMPT


@dataclass
class SummarizerMemory(MemoryInterface):
    """Rolling memory: keeps last 5 turns + incremental summary.

    After every `summarize_every` turns, compress only the oldest turn into
    the long-term summary. `get_context()` returns the summary plus last 5 turns.
    """

    llm: LLMInterface
    summarize_every: int = 5
    max_recent: int = 5
    _turns: deque[Tuple[str, str]] = field(default_factory=lambda: deque(maxlen=6))
    _summary: str = ""  # compressed long-term memory

    def add_turn(self, user: str, ai: str) -> None:
        self._turns.append((user, ai))  # append at rear
        # If we reach summarize_every turns, update summary incrementally
        if len(self._turns) >= self.summarize_every:
            # Remove oldest turn from front to summarize
            oldest_turn = self._turns.popleft()
            self._summary = self._summarize_incremental(oldest_turn)

    def _summarize_incremental(self, last_turn: Tuple[str, str]) -> str:
        """Update summary using existing summary + new turn"""
        transcript = f"User: {last_turn[0]}\nAI: {last_turn[1]}"
        prompt = (
            f"{SUMMARY_SYSTEM_PROMPT}\n\n"
            f"Existing Summary:\n{self._summary}\n\n"
            f"New Turn:\n{transcript}\n\n"
            f"Update the memory summary now:"
        )
        summary = self.llm.generate(prompt)
        return summary.strip()

    def get_context(self, *, k_recent: int = None) -> str:
        # Always last k_recent turns (deque automatically handles maxlen)
        k_recent = k_recent or self.max_recent
        recent = list(self._turns)[-k_recent:]
        recent_txt = "\n".join([f"User: {u}\nAI: {a}" for u, a in recent])
        parts = []
        if self._summary:
            parts.append(f"[LONG-TERM MEMORY]\n{self._summary}")
        if recent:
            parts.append(f"[RECENT TURNS]\n{recent_txt}")
        return "\n\n".join(parts) if parts else ""

    def summary(self) -> str:
        return self._summary

    def all_turns(self) -> list[Tuple[str, str]]:
        return list(self._turns)
