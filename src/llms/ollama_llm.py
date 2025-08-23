from __future__ import annotations
from typing import Optional, Dict, Any
import requests


from src.core.llm_interface import LLMInterface




class OllamaLLM(LLMInterface):
    """Ollama HTTP API client.


    Args:
    base_url: e.g. "http://localhost:11434" (no trailing slash)
    model: e.g. "llama3:8b" or any installed model tag
    """


    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3", **defaults: Any) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.defaults: Dict[str, Any] = {"temperature": 0.2, **defaults}


    def generate(self, prompt: str, *, options: Optional[Dict[str, Any]] = None) -> str:
        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {"model": self.model, "prompt": prompt, **self.defaults, **(options or {})}
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        # Ollama /api/generate streams by lines; when not streaming, response has 'response'
        data = r.json()
        text = data.get("response", "")
        return text.strip()