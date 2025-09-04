import json
from collections import deque
from typing import Optional, Deque, List

from src.core.memory_interface import Turn, SnapShot
import os


class RecentStorage:
    def __init__(self, file_path: str = "recent.json"):
        self.file_path = file_path
        # initialize json file if not exists
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({"turns": [], "snapshot": None}, f, indent=2)

    def _read_file(self) -> dict:
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_file(self, data: dict):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_turn(self, turn: Turn):
        """Save a turn, keep only last 5 turns."""
        data = self._read_file()
        turns = data.get("turns", [])
        turns.append(turn.to_dict())
        if len(turns) > 5:
            turns = turns[-5:]  # keep last 5
        data["turns"] = turns
        self._write_file(data)

    def load_turns(self) -> Deque[Turn]:
        """Load all turns as deque (oldest left, newest right)."""
        data = self._read_file()
        turns_data = data.get("turns", [])
        if not turns_data:
            return deque(maxlen=6)   # empty deque with maxlen=6
        turns = [Turn.from_dict(t) for t in turns_data]
        return deque(turns, maxlen=6)


    def save_rolling_snapshot(self, snapshot: SnapShot):
        """Save rolling snapshot, overwrite if exists."""
        data = self._read_file()
        data["snapshot"] = snapshot.to_dict()
        self._write_file(data)

    def load_snapshot(self) -> Optional[SnapShot]:
        """Load current rolling snapshot if available."""
        data = self._read_file()
        snap = data.get("snapshot")
        if snap:
            return SnapShot.from_dict(snap)
        return None
