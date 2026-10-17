# Realtime ingestion

Python pipeline: RSS poll → Ollama briefs → GPU-gated Kokoro speech → publish MongoDB + S3.

## Run

```bash
# infra
docker compose up -d mongo postgres redis

# optional models
ollama pull llama3.1:8b
# Kokoro-82M + ffmpeg for Opus

python3 -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt
cd ..
python -m realtime_ingestion.main
```

Ops reader: `http://127.0.0.1:8765`

## Modules

| Path | Role |
| --- | --- |
| `poller.py` | RSS + image extract |
| `worker_ai.py` | Briefs, framing, storylines (Ollama) |
| `worker_tts.py` | Kokoro + Opus |
| `tts/gpu_gate.py` | Ollama priority over TTS |
| `publish/` | Mongo + S3 publisher |
| `database.py` | Working SQLite store |
| `ui.py` | Temporary ops UI |

Env: see root `.env.example`.
