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

```bash
ollama pull llama3.1:8b
python3 -m venv .venv && source .venv/bin/activate
pip install -r realtime_ingestion/requirements.txt
python -m realtime_ingestion.main
```

Ops UI: `http://127.0.0.1:8765`  
Kokoro + `ffmpeg` optional for Opus upload.

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
