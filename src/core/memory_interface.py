from __future__ import annotations
from typing import Protocol, List, Tuple




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