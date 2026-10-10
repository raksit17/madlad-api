# MADLAD / Qwen Translation API

FastAPI translator with **selectable MADLAD or experimental Qwen** backends.
The default remains MADLAD. Both backends preserve the existing NestJS
`/v1/translate` and `/v1/translate/batch` API contracts.

## Layout

- `app/services/madlad.py`: original MADLAD backend
- `app/experimental/qwen/`: Qwen via Ollama and its Thai subtitle prompt
- `experiments/translation_comparison/`: repeatable translation comparisons
- `app/main.py`: creates only the selected provider

## Configure in .env

Copy `.env.example` to `.env` (Windows CMD: `copy .env.example .env`).

For the current MADLAD model:

```env
TRANSLATION_PROVIDER=madlad
```

To test Qwen (no MADLAD model weights are loaded):

```env
TRANSLATION_PROVIDER=qwen
QWEN_MODEL=qwen3.5:4b
QWEN_BASE_URL=http://host.docker.internal:11434
```

**Restart FastAPI every time you switch providers.** For Qwen mode,
install and run Ollama on your Windows host first:

```powershell
ollama pull qwen3.5:4b
ollama list
```

Docker Desktop reaches host Ollama via `host.docker.internal:11434`.
If FastAPI runs directly on Windows, use
`QWEN_BASE_URL=http://localhost:11434` instead.
The API checks Ollama and model availability at startup. It never
downloads the model automatically.

## Docker

```powershell
docker compose up -d --build
docker compose logs -f madlad-api
```

The provided compose uses NVIDIA GPU support and retains a Hugging Face
cache volume for MADLAD. Ollama is a **separate host application** and is
not launched by this compose file.

Check which model is active:

```powershell
curl.exe http://localhost:8000/ready
```

Expected `provider`: `madlad` or `qwen`. The `model` field reflects
the selection, and `ready` indicates the provider initialized.

## Test a translation (Windows CMD)

```cmd
curl.exe -X POST "http://localhost:8000/v1/translate" -H "Content-Type: application/json" -d "{\"text\":\"I might have an idea of it.\",\"source\":\"en\",\"target\":\"th\"}"
```

Both providers support source `en` and `ja`, destination `th`, and
`max_new_tokens`. The `num_beams` request field is accepted but
**ignored by Qwen** because Ollama does not expose MADLAD's beam search.
Batch requests are executed sequentially in Qwen mode to minimize VRAM use.

## Compare translations

See `experiments/translation_comparison/README.md`. Generate saved
output once with each backend, then print both versions side by side.

Notes:
- MADLAD limits input by `MAX_INPUT_TOKENS`; Qwen instead uses
  `QWEN_MAX_INPUT_CHARS` (different units).
- Qwen's `device=ollama` identifies the backend, not a GPU claim.
- Output quality is not guaranteed; compare real EN/JA subtitle lines.
- The NestJS subtitle alignment and timestamps are unchanged.
