from __future__ import annotations
from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel

from src.core.llm_interface import LLMInterface
from src.core.memory_interface import MemoryInterface
from src.memory.aggregator import Aggregator
from src.memory.metacognition import MetaCognition


SYSTEM_PREAMBLE = (
    "You are a helpful, concise assistant. Use provided MEMORY if relevant.\n"
    "If information is missing, ask a brief follow-up question."
    )




class ConversationEngine:
    """Coordinates Memory + LLM for a single-session conversation."""


    def __init__(self, llm: LLMInterface, memory: MemoryInterface, aggr: Aggregator, meta:MetaCognition) -> None:
        self.llm = llm
        self.memory = memory
        self.aggr = aggr
        self.meta = meta


    def step(self, user_msg: str, *, gen_options: Optional[Dict[str, Any]] = None) -> str:
        memory_ctx = self.memory.get_context()
        prompt_parts = [SYSTEM_PREAMBLE]
        daily_summary = self.aggr.get_daily_summary()
        if daily_summary:
            prompt_parts.append(f"Previous Day Summary:\n{daily_summary}")
        if memory_ctx:
            prompt_parts.append(f"MEMORY:\n{memory_ctx}")
        prompt_parts.append(f"User: {user_msg}\nAI:")
        full_prompt = "\n\n".join(prompt_parts)
        ai = self.llm.generate(full_prompt, options=gen_options)
        self.memory.add_turn(user_msg, ai)
        return ai

    def stepv2(self, user_msg: str, *, gen_options=None) -> str:
        mem_ctx = self.memory.get_context()

        # 1. Analyze retrieval need
        decision = self.meta.analyze(user_msg, mem_ctx)

        # 2. Perform retrieval
        retrievals = self.meta.retrieve(decision)

        # 3. Build prompt
        prompt_parts = [SYSTEM_PREAMBLE]

       
        if mem_ctx:
            prompt_parts.append(f"MEMORY:\n{mem_ctx}")

        if retrievals:
            prompt_parts.append("Retrieved Knowledge:\n" + "\n".join([r.memory for r in retrievals]))

        prompt_parts.append(f"User: {user_msg}\nAI:")
        full_prompt = "\n\n".join(prompt_parts)

        # 4. Generate
        print('-'*50)
        console = Console()
        console.print(Panel(full_prompt, title="FULL PROMPT", expand=False))
        print('-'*50)
        ai = self.llm.generate(full_prompt, options=gen_options)
        self.memory.add_turn(user_msg, ai)
        return ai