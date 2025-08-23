# Memory‑First LLM – MVP

A **modular memory brain** for stateless LLMs. MVP focuses on:

- pluggable LLM interface (Gemini SDK or Ollama HTTP)
- summarizer‑based long‑term memory + recent‑turn window
- CLI conversation to prove loop & transparency

## Run (Ollama local)

```bash
python -m src.ui.cli --provider ollama --model llama3 --base-url http://localhost:11434
```

## Run (Gemini)

```bash
export GEMINI_API_KEY=... # required
python -m src.ui.cli --provider gemini --model gemini-1.5-pro
```
