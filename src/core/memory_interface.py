from __future__ import annotations
from typing import Protocol, List, Tuple, Optional
from dataclasses import dataclass
from datetime import date, datetime

@dataclass
class SnapShot:
    day: date   # yyyy-mm-dd format internally, but we can parse dd-mm-yy
    summary: str
    
    
    def to_dict(self):
        return {
            "day": self.day.isoformat(),
            "summary": self.summary
        }

    @staticmethod
    def from_dict(data: dict) -> "SnapShot":
        return SnapShot(
            day=date.fromisoformat(data["day"]),
            summary=data["summary"]
        )

@dataclass
class Turn:
    time: datetime
    user: str
    ai: str
    def to_dict(self):
        return {
            "time": self.time.isoformat(),
            "user": self.user,
            "ai": self.ai
        }

    @staticmethod
    def from_dict(data: dict) -> "Turn":
        return Turn(
            time=datetime.fromisoformat(data["time"]),
            user=data["user"],
            ai=data["ai"]
        )
    
@dataclass
class Chapter:
    day: date
    memory:str
    tags: Optional[List[str]] = None

@dataclass
class DailyMemory:
    day: date
    memory: str
    tags: Optional[List[str]] = None
    
class MemoryInterface(Protocol):
    """Abstract memory store for conversations.


    MVP responsibilities:
    • hold turns (user, ai)
    • maintain/update a compressed summary
    • emit context for the next prompt (summary + recent turns)
    """


    def add_turn(self, user: str, ai: str) -> None:
        ...


    def get_context(self, *, k_recent: int = 4) -> str:
        ...


    def summary(self) -> str:
        ...


    def all_turns(self) -> List[Tuple[str, str]]:
        ...