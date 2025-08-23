from __future__ import annotations
from typing import List, Tuple
from dataclasses import dataclass, field


from src.core.memory_interface import MemoryInterface
from src.core.llm_interface import LLMInterface
from src.utils.prompting import SUMMARY_SYSTEM_PROMPT




@dataclass
class SummarizerMemory(MemoryInterface):
    """Simple memory: running summary + recent turns.


    After every `summarize_every` turns, compress the full history into a
    human‑readable, model‑friendly summary. `get_context()` returns the summary
    plus the last `k_recent` turns to keep recency.
    """


    llm: LLMInterface
    summarize_every: int = 6
    _turns: List[Tuple[str, str]] = field(default_factory=list)
    _summary: str = "" # compressed long‑term memory


    def add_turn(self, user: str, ai: str) -> None:
        self._turns.append((user, ai))
        if len(self._turns) % self.summarize_every == 0:
            self._summary = self._summarize()


    def _summarize(self) -> str:
        # Build a plain transcript for the summarizer
        transcript = "\n".join([f"User: {u}\nAI: {a}" for u, a in self._turns])
        prompt = f"{SUMMARY_SYSTEM_PROMPT}\n\nTranscript:\n{transcript}\n\nWrite the memory summary now:"
        summary = self.llm.generate(prompt)
        return summary.strip()


    def get_context(self, *, k_recent: int = 4) -> str:
        recent = self._turns[-k_recent:]
        recent_txt = "\n".join([f"User: {u}\nAI: {a}" for u, a in recent])
        parts = []
        if self._summary:
            parts.append(f"[LONG-TERM MEMORY]\n{self._summary}")
        if recent:
            parts.append(f"[RECENT TURNS]\n{recent_txt}")
        return "\n\n".join(parts) if parts else ""


    def summary(self) -> str:
        return self._summary


    def all_turns(self) -> List[Tuple[str, str]]:
        return list(self._turns)

