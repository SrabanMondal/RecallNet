import json, os
from typing import Optional, Dict
from src.core.storage_interface import StorageInterface

class JSONStorage(StorageInterface):
    def __init__(self, path: str = "data/memory_state.json"):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def load(self) -> Optional[Dict]:
        if not os.path.exists(self.path): return None
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: Dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
