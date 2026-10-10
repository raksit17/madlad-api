# Subtitle translation comparison

Run identical EN/JA subtitle samples through both providers and review
meaning, conversational Thai, proper names, emotion and completeness.

1. Set `TRANSLATION_PROVIDER=madlad` in `.env` and restart FastAPI.
2. Run `python experiments/translation_comparison/run.py`.
   This saves `results/madlad.json`.
3. Set `TRANSLATION_PROVIDER=qwen` and restart FastAPI (Ollama running).
4. Run the same `run.py` command again for `results/qwen.json`.
5. Run `python experiments/translation_comparison/compare.py`.

`cases.json` contains editable examples. All results are obtained from
your running API, not fabricated examples. The generated `results/`
folder is gitignored to keep local subtitles private.
