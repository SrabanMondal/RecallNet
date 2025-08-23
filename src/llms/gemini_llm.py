from __future__ import annotations
from typing import Optional, Dict, Any
import os


try:
    import google.generativeai as genai # type: ignore
except Exception: # pragma: no cover
    genai = None # allow import without dependency during scaffold


from src.core.llm_interface import LLMInterface




class GeminiLLM(LLMInterface):
    """Gemini via Google Generative AI SDK.


    Notes:
    • Requires env var `GEMINI_API_KEY` or key passed in ctor.
    • `model` defaults to a text-capable model (e.g., 'gemini-1.5-pro').
    """


    def __init__(self, model: str = "gemini-1.5-pro", api_key: Optional[str] = None, **defaults: Any) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.defaults: Dict[str, Any] = {"temperature": 0.3, **defaults}
        if not self.api_key:
            raise ValueError("Gemini API key missing. Set GEMINI_API_KEY or pass api_key.")
        if genai is None:
            raise RuntimeError("google-generativeai package not installed. Add it to requirements.")
        genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model)


    def generate(self, prompt: str, *, options: Optional[Dict[str, Any]] = None) -> str:
        params = {**self.defaults, **(options or {})}
        resp = self._model.generate_content(prompt, generation_config=params)
        # SDK returns a rich object; extract text safely
        txt = getattr(resp, "text", None) or (resp.candidates[0].content.parts[0].text if resp.candidates else "")
        return txt.strip()

