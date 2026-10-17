# Local development

How to run the full loop on a laptop: ingest + Ollama + (optional) Kokoro + Dockerized Mongo/S3/API + Expo Go on your phone.

## Machine checklist

| Tool | Why |
| --- | --- |
| Python 3.11+ | `realtime_ingestion` |
| Docker Desktop | MongoDB, PostgreSQL, MinIO, Redis, API container |
| Ollama | `llama3.1:8b` briefs |
| Kokoro-82M | Spoken Opus (optional but desired) |
| .NET 10 SDK | Backend (`CNews.Api` on Kestrel) |
| Node 20+ / Expo Go | Mobile (Expo 57, custom theme, Zustand) |
| Redis | Optional; fakeredis works for solo ingest |

## 1. Ollama 8B (required for good briefs)

```text
# Install from https://ollama.com then:
ollama pull llama3.1:8b
ollama run llama3.1:8b "Say hello in one short sentence."
```

Keep the Ollama app/daemon running. Default URL: `http://127.0.0.1:11434`.

**Disk.** The 8B model is multi‑GB. Pull once on a good network.

**GPU.** On Apple Silicon, Ollama uses Metal. On NVIDIA Linux, it uses CUDA. Kokoro should wait until Ollama is idle (see [pipeline.md](./pipeline.md)).

## 2. Python ingest (today)

From repo root:

```text
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r realtime_ingestion/requirements.txt
python -m realtime_ingestion.main
```

Temporary reader: `http://127.0.0.1:8765` — pipeline debugging only.

## 3. Docker services

Root `docker-compose.yml` is in place. Typical services:

| Service | Image / build | Port | Role |
| --- | --- | --- | --- |
| `mongo` | `mongo:7` | 27017 | Content publish store |
| `postgres` | `postgres:16` | 5432 | Users + preferences |
| `minio` | `minio/minio` | 9000 API / 9001 console | S3-compatible audio |
| `createbuckets` | minio/mc | — | Ensure audio bucket exists |
| `redis` | `redis:7` | 6379 | Streams for ingest |
| `api` | `backend` Dockerfile | 5080 (Kestrel) or 9000 (RIE) | Mobile API |

**Not in Compose (host):** Ollama, Kokoro, and usually `realtime_ingestion` itself — they need GPU and large models.

Example developer flow after Compose exists:

```text
docker compose up -d mongo postgres minio redis
# terminal A
python -m realtime_ingestion.main
# terminal B
dotnet run --project backend/CNews.Api   # or docker compose up api
# terminal C
cd mobile && npx expo start
```

Point ingest at:

```text
MONGODB_URI=mongodb://127.0.0.1:27017
S3_ENDPOINT=http://127.0.0.1:9000
S3_ACCESS_KEY=…
S3_SECRET_KEY=…
S3_BUCKET=cnews-audio
REDIS_URL=redis://127.0.0.1:6379/0
```

Point the API at Mongo + Postgres + MinIO. Point Expo at `http://<your-lan-ip>:5080`. Configure Google OAuth client ids for Expo.

## 4. Lambda RIE simulation

When validating packaging:

```text
docker build -t cnews-api:dev backend
docker run --rm -p 9000:8080 --env-file .env.api cnews-api:dev
```

Invoke with an API Gateway proxy JSON POST to:

```text
http://localhost:9000/2015-03-31/functions/function/invocations
```

Use Kestrel on the LAN for Expo day-to-day; use RIE before shipping an image to ECR.

## 5. Expo Go on a phone

1. Phone and computer on the same Wi‑Fi.
2. macOS firewall allows inbound on the API and Metro ports.
3. `EXPO_PUBLIC_API_BASE_URL=http://192.168.x.x:5080` (no trailing slash).
4. Do not use `localhost` in Expo Go on a physical device.

## 6. Suggested smoke path

1. `ollama pull llama3.1:8b` works.
2. Ingest polls a feed and shows a brief on the temporary reader.
3. With TTS enabled and GPU free, an Opus object appears in MinIO.
4. MongoDB `stories` has `textReady` / `audioStatus`.
5. `GET /v1/home/feed` returns masonry cards (with or without `imageUrl`).
6. Expo Home: immersive wall → full-screen on tap; multi-outlet swipe; center Play speaks ~4 visible wall cards.
7. Google login upserts a Postgres user.

## 7. Troubleshooting

| Symptom | Likely fix |
| --- | --- |
| Extractive briefs only | Start Ollama; verify `OLLAMA_URL` |
| TTS never starts | Check GPU gate; finish Ollama jobs; install Kokoro |
| Expo cannot connect | Use LAN IP; same Wi‑Fi; OS firewall |
| Signed URL fails on device | MinIO endpoint must be reachable from the phone, or proxy audio through the API in dev |
| Lambda RIE 502 | Confirm image CMD / handler string for .NET entry point |

**Dev audio tip.** If the phone cannot reach MinIO directly, add a temporary API route `GET /v1/stories/{id}/audio` that streams bytes from S3/MinIO for local only. Production should keep signed URLs to S3/CloudFront.

## 8. Secrets

Use a gitignored `.env` / `.env.api`. Never commit AWS keys, MinIO root credentials, or Mongo URIs with passwords.
