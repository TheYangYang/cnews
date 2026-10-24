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
| `worker_ai.py` | Briefs first; framing + storylines when the GPU is free (Ollama) |
| `worker_tts.py` | Kokoro + Opus, batched GPU turns |
| `tts/gpu_gate.py` | Turn-taking between Ollama and Kokoro on one GPU |
| `llm.py` | Shared Ollama client (same `num_ctx` / `keep_alive` on every call) |
| `publish/` | Mongo + S3 publisher (runs on its own thread) |
| `database.py` | Working SQLite store |
| `ui.py` | Temporary ops UI |
| `maintenance.py` | Retries failed S3 uploads (10 min); prunes the working store (hourly) |

Env: see root `.env.example` (loaded automatically from the repo-root `.env`).

## Tests

```bash
python -m unittest discover -s realtime_ingestion/tests -t .
```

Fake Ollama + Kokoro, in-process Redis, temp SQLite — no GPU or network needed.

## Deploying on a GTX 1060 box

The defaults target one 6 GB card running both models. Each speech turn unloads
Ollama, speaks a batch of briefs on the GPU, then hands the card back
(see `docs/real-time-ingestion/pipeline.md`, "GPU scheduling").

1. Install the NVIDIA driver, Ollama, `ffmpeg`, and `espeak-ng`; `ollama pull llama3.1:8b`.
2. Install a PyTorch build that still ships Pascal kernels, then check it lists `sm_61`:

   ```bash
   python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_arch_list())"
   ```

   If `sm_61` is missing, set `TTS_DEVICE=cpu` (the worker also falls back to CPU on
   the first failed GPU render). Kokoro-82M on CPU is slower but fine for ~50-word briefs.
3. Copy `.env.example` to `.env`, point `MONGODB_URI` / `S3_*` / `REDIS_URL` at the real
   stores, and run headless if you can (a desktop session holds VRAM on the same card).
4. Run under a supervisor so it restarts on reboot, e.g. a systemd unit with
   `ExecStart=/path/to/.venv/bin/python -m realtime_ingestion.main`, `Restart=always`,
   `WorkingDirectory=/path/to/cnews`. SIGTERM finishes the job in hand, then exits.

Retention (`maintenance.py`, hourly):

| Where | Rule |
| --- | --- |
| Local text | Article text is dropped as soon as the brief is written |
| Local audio | Deleted once S3 has it; kept as `upload_failed` and retried every 10 min if not |
| Local rows | Small rows kept 7 days so RSS items aren't briefed twice, then deleted |
| MongoDB + S3 stories | Removed 14 days after publishing, unless a live storyline lists them |
| Storylines | Auto-closed after 7 days without an update; removed with their stories 30 days after closing |

S3 objects are deleted before their Mongo docs, so a failed S3 call never leaves the app
pointing at missing audio. `PRUNE_PUBLISHED=false` turns off the MongoDB/S3 part.

Tuning when news keeps coming: raise `ARTICLE_BACKLOG_MAX` to keep more articles
during a burst (at the cost of freshness); lower `TTS_MAX_LAG_SECONDS` if audio lags
too far behind text. A 1060 **3 GB** cannot hold an 8B model: use a 3B model
(`OLLAMA_MODEL=llama3.2:3b`) or expect most layers on CPU.
