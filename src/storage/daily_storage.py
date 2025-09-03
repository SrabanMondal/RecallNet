import sqlite3
from datetime import date
from typing import List, Optional
from dataclasses import dataclass
from src.core.memory_interface import DailyMemory


class DailyMemoryStorage:
    def __init__(self, db_path: str = "memory.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_table()

    def _init_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day DATE UNIQUE,
                memory TEXT NOT NULL,
                tags TEXT
            )
        """)
        self.conn.commit()

    def save(self, daily: DailyMemory):
        """Insert or replace a daily memory."""
        tags_str = ",".join(daily.tags) if daily.tags else None
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO daily_memories (day, memory, tags)
            VALUES (?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET
                memory = excluded.memory,
                tags = excluded.tags
        """, (daily.day.isoformat(), daily.memory, tags_str))
        self.conn.commit()

    def get_by_date(self, day: date) -> Optional[DailyMemory]:
        cur = self.conn.cursor()
        cur.execute("SELECT day, memory, tags FROM daily_memories WHERE day = ?", (day.isoformat(),))
        row = cur.fetchone()
        if row:
            tags = row[2].split(",") if row[2] else None
            return DailyMemory(day=date.fromisoformat(row[0]), memory=row[1], tags=tags)
        return None

    def get_range(self, start_day: date, end_day: date) -> List[DailyMemory]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT day, memory, tags FROM daily_memories
            WHERE day BETWEEN ? AND ?
            ORDER BY day ASC
        """, (start_day.isoformat(), end_day.isoformat()))
        rows = cur.fetchall()
        result = []
        for row in rows:
            tags = row[2].split(",") if row[2] else None
            result.append(DailyMemory(day=date.fromisoformat(row[0]), memory=row[1], tags=tags))
        return result
