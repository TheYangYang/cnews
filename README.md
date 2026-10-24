# CrackNews (CNews)

Canadian news middleman: ingest RSS → brief with Ollama → speak with Kokoro → publish to MongoDB/S3 → serve **CrackNews** (Expo) via a .NET 10 API.

## Projects (independent)

| Folder | Stack | Role |
| --- | --- | --- |
| `realtime_ingestion/` | Python | Poll, summarize, TTS, publish |
| `backend/` | .NET 10 | `/v1` API for mobile (Lambda-ready) |
| `mobile/` | Expo / RN | CrackNews — Home wall + Play + Storylines |
| `docs/real-time-ingestion/` | Markdown | Specs, shipped status, upgrade plan |

## Quick start

Full runbook: [docs/real-time-ingestion/DEV.md](docs/real-time-ingestion/DEV.md)

### 1. Infra

```bash
cp .env.example .env
docker compose up -d mongo postgres redis
python3 scripts/seed_demo_mongo.py   # sample content without Ollama
python3 scripts/seed_demo_ads.py     # Home + Storylines display ads
```

### 2. API

```bash
export PATH="$HOME/.dotnet:$PATH"
cd backend
PUBLIC_BASE_URL=http://<LAN_IP>:5080 \
  dotnet run --project CNews.Api --urls http://0.0.0.0:5080
```

Smoke: `curl http://127.0.0.1:5080/v1/health` and `curl http://127.0.0.1:5080/v1/home/feed`

### 3. Mobile

```bash
cd mobile
npm install
# Set EXPO_PUBLIC_API_BASE_URL to your LAN IP (not localhost on a phone)
npx expo start --lan
```

### 4. Live ingest (optional, needs Ollama)

See **[Run ingestion locally](#run-ingestion-locally)** below.

## Run ingestion locally

`realtime_ingestion` polls Canadian RSS feeds, writes a ~50-word brief with Ollama,
speaks it with Kokoro, then publishes the brief to MongoDB and the Opus audio to S3.
The mobile app reads both through the API; it never talks to the ingest computer.

### What you need

| Tool | Why | Install |
| --- | --- | --- |
| Python 3.11+ | runs the pipeline | python.org or your package manager |
| [Ollama](https://ollama.com) + `llama3.1:8b` | writes the briefs | `ollama pull llama3.1:8b` |
| `ffmpeg` | encodes Opus audio | `brew install ffmpeg` / `apt install ffmpeg` |
| `espeak-ng` | Kokoro's phonemes | `brew install espeak-ng` / `apt install espeak-ng` |
| Docker | local Redis (and Mongo/MinIO for a dev setup) | Docker Desktop |

Without Ollama, briefs fall back to the article's first sentences. Without Kokoro,
stories are published as text only. Both keep the pipeline running.

### 1. Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r realtime_ingestion/requirements.txt
```

The first run downloads the Kokoro voice model (~350 MB) from Hugging Face.

**GTX 1060 / NVIDIA box:** install a PyTorch build that still includes Pascal (`sm_61`)
kernels, then check:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_arch_list())"
```

If `sm_61` is missing, set `TTS_DEVICE=cpu` (the worker also falls back to CPU by itself).

### 2. Configure `.env` (repo root, loaded automatically)

```bash
cp .env.example .env
```

| Setting | Local dev (Docker) | Production (Atlas + AWS) |
| --- | --- | --- |
| `MONGODB_URI` | `mongodb://127.0.0.1:27017` | `mongodb+srv://…` from Atlas |
| `S3_ENDPOINT` | `http://127.0.0.1:9000` (MinIO) | *(empty)* |
| `S3_BUCKET` | `cnews-audio` | the `AudioBucket` stack output |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | `cnewsminio` / `cnewsminio` | keys of the IAM user with `IngestPolicyArn` attached |
| `S3_FORCE_PATH_STYLE` | `true` | `false` |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | same (Redis runs on the ingest box) |
| `PRUNE_PUBLISHED` | `false` (keeps demo data) | `true` |

Everything else has defaults tuned for one 6 GB GPU; see `.env.example`.

### 3. Start the services it needs

```bash
docker compose up -d redis                      # always
docker compose up -d mongo                      # local dev only
docker compose --profile audio up -d minio createbuckets   # local dev audio only
ollama serve                                    # if Ollama is not already running
```

Redis is optional: without it the pipeline uses an in-process queue and requeues
unfinished work from its SQLite store on restart.

### 4. Run

```bash
source .venv/bin/activate
python -m realtime_ingestion.main
```

Open the ops page at **http://127.0.0.1:8765** to watch briefs, speech turns, and
uploads (`UI_HOST=0.0.0.0` to open it from another machine on your network).
Stop with Ctrl+C; it finishes the job in hand, then exits.

### 5. Check it's working

- Ops page events: `brief_ready …`, then `gpu turn: Ollama unloaded`, `tts_done …`, `audio put …`.
- `curl http://127.0.0.1:5080/v1/home/feed?mode=listen` (API running) shows new stories.
- Deployed API: `GET /v1/health/ingest` returns 200 while this box is checking in.

### 6. Keep it running (Linux ingest box)

`/etc/systemd/system/cnews-ingest.service`:

```ini
[Unit]
Description=CrackNews ingestion
After=network-online.target docker.service
Wants=network-online.target

[Service]
WorkingDirectory=/home/YOU/cnews
ExecStart=/home/YOU/cnews/.venv/bin/python -m realtime_ingestion.main
Restart=always
RestartSec=10
User=YOU

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now cnews-ingest
journalctl -u cnews-ingest -f        # logs
```

**Windows box:** use [NSSM](https://nssm.cc) to run
`C:\path\to\cnews\.venv\Scripts\python.exe -m realtime_ingestion.main` as a service
(startup directory = the repo), or Task Scheduler "At startup". Ollama for Windows runs
as its own service, and Redis via Docker Desktop.

Keep the machine from sleeping. Local data lives in `data/` (SQLite + audio waiting
to upload) and stays small: text is dropped after briefing, audio after upload, rows
after 7 days.

### Tests

```bash
python -m unittest discover -s realtime_ingestion/tests -t .
```

No GPU or network needed (fake Ollama and Kokoro); the MongoDB tests use a throwaway
database and skip when Mongo isn't running.

## Docs

| Doc | Purpose |
| --- | --- |
| [docs/real-time-ingestion/DEV.md](docs/real-time-ingestion/DEV.md) | Developer handbook |
| [docs/real-time-ingestion/SHIPPED.md](docs/real-time-ingestion/SHIPPED.md) | What is built today |
| [docs/real-time-ingestion/upgrade-plan.md](docs/real-time-ingestion/upgrade-plan.md) | Future prefs / outlet subscribe / recommendations |
| [docs/real-time-ingestion/roadmap.md](docs/real-time-ingestion/roadmap.md) | Phases P0–P7 |
| [docs/real-time-ingestion/README.md](docs/real-time-ingestion/README.md) | Doc index |

## Auth note

Dev Google bypass: `POST /v1/auth/google` with `{ "idToken": "dev:you@example.com" }`.
