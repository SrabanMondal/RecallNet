from __future__ import annotations
from typing import Protocol, runtime_checkable, Dict, Any, Optional


@runtime_checkable
class LLMInterface(Protocol):
    """Minimal, swappable LLM interface.


    Implementations must be side‑effect free (stateless) and accept a single
    prompt string → return a string response. Any provider‑specific options
    should be passed at construction time or via kwargs.
    """


    def generate(self, prompt: str, *, options: Optional[Dict[str, Any]] = None) -> str:
        """Synchronous text generation.


        Parameters
        ----------
        prompt: str
        The full prompt to send.
        options: Optional[Dict[str, Any]]
        Provider specific generation options (e.g., temperature).
        Returns
        -------
        str: model response text
        """
        ...

