from __future__ import annotations
from dataclasses import dataclass




@dataclass
class LLMConfig:
    provider: str # 'gemini' | 'ollama'
    model: str = ""
    base_url: str = "" # for ollama
    temperature: float = 0.2




@dataclass
class AppConfig:
    llm: LLMConfig
    summarize_every: int = 6