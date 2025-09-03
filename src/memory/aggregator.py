from dataclasses import dataclass
from datetime import date
from typing import List
from src.core.llm_interface import LLMInterface
from src.utils.prompting import SUMMARY_SYSTEM_PROMPT
from src.core.memory_interface import Chapter, SnapShot, DailyMemory
from src.storage.daily_storage import DailyMemoryStorage
from src.storage.chapter_storage import ChapterStorage
import threading
import datetime

class Aggregator:
    def __init__(self, llm: LLMInterface, chapter_store: ChapterStorage, daily_store: DailyMemoryStorage):
        self.llm = llm
        # self._hourly: dict[str, str] = {}
        # self._daily: dict[str, str] = {}
        self.daily_store = daily_store
        self.chapter_store = chapter_store
        t = threading.Thread(target=self._daily_rollup, daemon=True)

        t.start()

    # ... existing methods ...

    def merge_chapter(self, prev_chapter: Chapter | None, snapshots: List[SnapShot]) -> Chapter:
        """
        Merge a previous chapter memory with a list of snapshots using LLM.
        - prev_chapter: Chapter object with existing memory (can be None)
        - snapshots: List of SnapShot objects
        Returns:
            New Chapter object with merged memory and date = last snapshot date
        """
        if not snapshots:
            # If no snapshots, return prev_chapter or empty chapter
            if prev_chapter:
                return prev_chapter
            else:
                return Chapter(day=date.today(), memory="", tags=None)

        snapshot_text = "\n".join([s.summary for s in snapshots])

        # Prepare LLM prompt
        if prev_chapter and prev_chapter.memory.strip():
            prompt = (
                f"{SUMMARY_SYSTEM_PROMPT}\n\n"
                f"Previous Chapter Memory:\n{prev_chapter.memory}\n\n"
                f"Current Snapshots:\n{snapshot_text}\n\n"
                "Compose a new chapter memory:\n"
                "- Merge previous memory and snapshots.\n"
                "- Keep it factual and concise.\n"
                "- Maintain timeline, carry forward ongoing items, mark resolved/cancelled if any."
            )
        else:
            prompt = (
                f"{SUMMARY_SYSTEM_PROMPT}\n\n"
                f"Current Snapshots:\n{snapshot_text}\n\n"
                "Compose a new chapter memory:\n"
                "- Use only the snapshots provided.\n"
                "- Keep it factual and concise.\n"
                "- Maintain timeline, carry forward ongoing items, mark resolved/cancelled if any."
            )

        merged_memory = self.llm.generate(prompt).strip()

        # Date for new chapter = last snapshot's date
        new_date = snapshots[-1].day

        # Carry forward tags if available
        tags = prev_chapter.tags if prev_chapter else None

        return Chapter(day=new_date, memory=merged_memory, tags=tags)

    def _daily_rollup(self):
        """Roll up last active day's chapters into a daily memory block."""
        today = datetime.utcnow().date()

        # last saved chapter find karo
        last_chapter = self.chapter_store.get_last_chapter()
        if not last_chapter:
            return

        last_active_day = last_chapter.day
        if last_active_day == today:
            return  # current day ko abhi roll-up mat karo

        # check agar daily memory already saved hai us din ke liye
        if self.daily_store.get_by_date(last_active_day):
            return  # already summarized

        # fetch all chapters from last active day
        chapters: List[Chapter] = self.chapter_store.get_by_day(last_active_day)
        if not chapters:
            return

        merged = "\n".join([c.memory for c in chapters])
        prompt = (
            f"{SUMMARY_SYSTEM_PROMPT}\n\n"
            f"Chapters for {last_active_day.isoformat()}:\n{merged}\n\n"
            "Create a single daily memory capturing key events, decisions, preferences, and [ONGOING] items."
        )
        day_memory = self.llm.generate(prompt).strip()

        # save as daily memory (SQL table)
        daily_mem = DailyMemory(day=last_active_day, memory=day_memory, tags=["daily-summary"])
        self.daily_store.save(daily_mem)