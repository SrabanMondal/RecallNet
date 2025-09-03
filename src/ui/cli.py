from __future__ import annotations
import argparse
import sys


from src.config import AppConfig, LLMConfig
from src.llms.gemini_llm import GeminiLLM
from src.llms.ollama_llm import OllamaLLM
from src.memory.agent_memory import AgentMemory
from src.engine.conversation_engine import ConversationEngine
from src.storage.chapter_storage import ChapterStorage
from src.storage.daily_storage import DailyMemoryStorage
from src.storage.json_storage import RecentStorage
from src.memory.aggregator import Aggregator


PROVIDER_CHOICES = ("gemini", "ollama")




def make_llm(cfg: LLMConfig):
    if cfg.provider == "gemini":
        return GeminiLLM(model=cfg.model or "gemini-1.5-pro", temperature=cfg.temperature)
    if cfg.provider == "ollama":
        base = cfg.base_url or "http://localhost:11434"
        model = cfg.model or "llama3"
        return OllamaLLM(base_url=base, model=model, temperature=cfg.temperature)
    raise ValueError(f"Unknown provider: {cfg.provider}")




def main(argv=None):
    parser = argparse.ArgumentParser(description="Memory‑First LLM – CLI")
    parser.add_argument("--provider", choices=PROVIDER_CHOICES, default="ollama")
    parser.add_argument("--model", default="llama3", help="Model name/tag for provider")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama base URL (if provider=ollama)")
    parser.add_argument("--temp", type=float, default=0.2)
    parser.add_argument("--sum-every", type=int, default=6, help="Summarize every N turns")
    args = parser.parse_args(argv)


    app_cfg = AppConfig(llm=LLMConfig(provider=args.provider, model=args.model, base_url=args.base_url, temperature=args.temp), summarize_every=args.sum_every)


    llm = make_llm(app_cfg.llm)
    chapter_store = ChapterStorage("chapters.db")
    daily_store = DailyMemoryStorage("memory.db")
    recent_store = RecentStorage("recent.json")
    aggr = Aggregator(llm, chapter_store, daily_store)
    memory = AgentMemory(llm=llm,chapter_store=chapter_store,recent_store=recent_store, aggr=aggr)
    
    engine = ConversationEngine(llm=llm, memory=memory)


    print("\n>>> Memory‑First LLM (CLI). Type 'exit' to quit.\n")
    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print() ; break
        if user.lower() in {"exit", ":q", "quit"}:
            break
        reply = engine.step(user)
        print(f"AI: {reply}\n")
        # Show debug summary every turn for transparency
        if memory.summary():
            print("[Memory Summary]\n" + memory.summary() + "\n")




if __name__ == "__main__":
    sys.exit(main())