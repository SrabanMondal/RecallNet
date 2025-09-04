from __future__ import annotations
from typing import Tuple, List, Dict
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta

from src.core.memory_interface import MemoryInterface, SnapShot, Turn
from src.core.llm_interface import LLMInterface
from src.utils.prompting import SUMMARY_SYSTEM_PROMPT
from src.storage.chapter_storage import ChapterStorage
from src.storage.json_storage import RecentStorage
from src.memory.aggregator import Aggregator

@dataclass
class AgentMemory(MemoryInterface):
    """
    Rolling + Time-based hybrid memory:
    - Keeps a rolling buffer of turns (recent + fading summary)
    - Every `window_minutes`, takes a snapshot of the *current rolling summary*
    - Snapshots later can be aggregated into hour/day summaries
    """

    llm: LLMInterface
    chapter_store: ChapterStorage
    aggr: Aggregator
    recent_store: RecentStorage
    snap_counter: int = 10
    chap_counter:int = 10
    max_recent: int = 5
    _turn_counter: int = 0
    _turns: deque[Turn] =  field(init=False) # load from recent_store
    _rolling_snapshot: SnapShot = None # load from recent store
    _snapshots: List[SnapShot] =  field(default_factory=list)  # list of {time, summary}
    #_last_window: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        # load recent turns from storage
        self._turns = self.recent_store.load_turns()
        # load rolling snapshot from storage
        self._rolling_snapshot = self.recent_store.load_snapshot()

    def add_turn(self, user: str, ai: str) -> None:
        now = datetime.now()
        self._turns.append(Turn(time =now, user=user, ai=ai))
        self._turn_counter+=1
        # rolling summarization: fade oldest turn into summary
        if len(self._turns) > self.max_recent:
            oldest = self._turns.popleft()
            self._rolling_snapshot = self._summarize_incremental(oldest)

        # check if snapshot window passed
        if self._turn_counter==self.snap_counter:
            self._create_snapshot()
            self._turn_counter=0
            self.recent_store.save_rolling_snapshot(self._rolling_snapshot)
        
        if len(self._snapshots)==self.chap_counter:
            self._create_chapter()
            
        self.recent_store.save_turn(self._turns[-1])
        

    def _summarize_incremental(self, turn: Turn) -> SnapShot:
        """Update rolling summary with a single old turn"""
        transcript = f"[{turn['time'].strftime("%Y-%m-%d %H:%M:%S")}]\nUser: {turn['user']}\nAI: {turn['ai']}"
        prompt = (
            f"{SUMMARY_SYSTEM_PROMPT}\n\n"
            f"Existing Summary:\n{self._rolling_summary}\n\n"
            f"New Turn:\n{transcript}\n\n"
            f"Update the memory summary now:"
        )
        summary =  self.llm.generate(prompt).strip()
        return SnapShot(day=turn.time, summary=summary)

    def _create_snapshot(self) -> None:
        """Freeze current rolling summary into a time-stamped snapshot"""
        if not self._rolling_snapshot:
            return
        self._snapshots.append(self._rolling_snapshot)

    def get_context(self, *, k_recent: int = None) -> str:
        """Get recent context"""
        k_recent = k_recent or self.max_recent
        recent = list(self._turns)[-k_recent:]
        recent_txt = "\n".join(
            [f"[{t.time.strftime("%Y-%m-%d %H:%M")}]\nUser: {t.user}\nAI: {t.ai}" for t in recent]
        )

        parts = []
        if self._rolling_snapshot:
            parts.append(f"[ROLLING SUMMARY]\n{self._rolling_snapshot.summary}")
        if recent:
            parts.append(f"[RECENT TURNS]\n{recent_txt}")
        return "\n\n".join(parts) if parts else ""
    
    def _create_chapter(self):
        prev_chapter = self.chapter_store.get_last_chapter()
        new_chap = self.aggr.merge_chapter(prev_chapter=prev_chapter, snapshots=self._snapshots)
        self.chapter_store.save(chapter=new_chap)
        self._snapshots.clear()

    def summary(self) -> str:
        return self._rolling_snapshot.summary


    def all_turns(self) -> List[Tuple[str, str]]:
        return [(t['user'], t['ai']) for t in self._turns]
