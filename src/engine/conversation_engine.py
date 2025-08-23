from __future__ import annotations
from typing import Optional, Dict, Any


from src.core.llm_interface import LLMInterface
from src.core.memory_interface import MemoryInterface




SYSTEM_PREAMBLE = (
    "You are a helpful, concise assistant. Use provided MEMORY if relevant.\n"
    "If information is missing, ask a brief follow-up question."
    )




class ConversationEngine:
    """Coordinates Memory + LLM for a single-session conversation."""


    def __init__(self, llm: LLMInterface, memory: MemoryInterface) -> None:
        self.llm = llm
        self.memory = memory


    def step(self, user_msg: str, *, gen_options: Optional[Dict[str, Any]] = None) -> str:
        memory_ctx = self.memory.get_context()
        prompt_parts = [SYSTEM_PREAMBLE]
        if memory_ctx:
            prompt_parts.append(f"MEMORY:\n{memory_ctx}")
        prompt_parts.append(f"User: {user_msg}\nAI:")
        full_prompt = "\n\n".join(prompt_parts)
        ai = self.llm.generate(full_prompt, options=gen_options)
        self.memory.add_turn(user_msg, ai)
        return ai