import json
from src.core.llm_interface import LLMInterface
from src.storage.chapter_storage import ChapterStorage
from src.storage.daily_storage import DailyMemoryStorage
from src.utils.prompting import META_COGNITION_SYSTEM_PROMPT

class MetaCognition:
    def __init__(self, llm: LLMInterface, chapter_store:ChapterStorage, daily_store:DailyMemoryStorage):
        self.llm = llm
        self.chapter_store = chapter_store
        self.daily_store = daily_store

    def analyze(self, user_msg: str, context:str):
        """
        Decide retrieval strategy.
        Returns dict like:
        { "strategy": "semantic"|"day"|"hybrid"|"none", "params": {...} }
        """
        # Prompt to LLM for retrieval decision
        analysis_prompt = f"""{META_COGNITION_SYSTEM_PROMPT}

User: {user_msg}
{context}
"""
        decision = self.llm.generate(analysis_prompt)
        try:
            return json.loads(decision)
        except:
            return {"strategy": "none"}
        
    def retrieve(self, decision):
        strategy = decision.get("strategy", "none")
        params = decision.get("params", {})

        if strategy == "semantic":
            query = params.get("query")
            return self.chapter_store.semantic_retrieve_global(query, top_k=5)

        if strategy == "day":
            start = params.get("start_day")
            end = params.get("end_day", start)
            return self.daily_store.get_range(start, end)

        if strategy == "hybrid":
            start = params.get("start_day")
            end = params.get("end_day", start)
            query = params.get("query")
            return self.chapter_store.semantic_retrieve_range(query, top_k=5, start=start,end=end)

        return []

