# Backend (`CNews.Api`)

.NET 10 Web API for the CNews mobile app. Clean architecture, Lambda-hostable, runs on Kestrel for local Expo.

## Layout

```text
backend/
  CNews.Api/             # HTTP host, /v1 endpoints, JWT
  CNews.Application/     # use-cases + DTOs
  CNews.Domain/          # entities
  CNews.Infrastructure/  # Mongo, Postgres, S3, Google/JWT
  CNews.Api.Tests/
  Dockerfile
```

## Run locally

```bash
# from repo root
docker compose up -d mongo postgres redis
python3 scripts/seed_demo_mongo.py
python3 scripts/seed_demo_ads.py

export PATH="$HOME/.dotnet:$PATH"
cd backend
dotnet run --project CNews.Api --urls http://0.0.0.0:5080
```

| Check | Command |
| --- | --- |
| Health | `curl http://127.0.0.1:5080/v1/health` |
| Feed | `curl 'http://127.0.0.1:5080/v1/home/feed?mode=listen&topics=Canada,Local,Business,Health'` |
| Ads | `curl 'http://127.0.0.1:5080/v1/ads/display?slot=home_wall'` |
| Dev login | `curl -X POST http://127.0.0.1:5080/v1/auth/google -H 'Content-Type: application/json' -d '{"idToken":"dev:you@example.com"}'` |

| Ingest health | `curl http://127.0.0.1:5080/v1/health/ingest` (200 fresh, 503 stale) |

## Config

Local dev values (localhost Mongo/Postgres, MinIO, LAN URL) live in
`CNews.Api/appsettings.Development.json`. Outside Development the API refuses to
start without `JWT_SIGNING_KEY` (32+ chars) and `MONGODB_URI`, the `dev:` login is
off, and S3 uses real AWS with the Lambda role's credentials.
Note `ASPNETCORE_URLS` sets the port (`--urls` is ignored).

## Deploy to AWS (Lambda + HTTPS API + S3)

`template.yaml` creates: the API Lambda (container image, arm64), an HTTPS HTTP API
with throttling, the private audio bucket, 30-day logs, and an IAM policy for the
ingest box. Needs the AWS CLI + SAM CLI, Docker, and an AWS account.

```bash
cd backend
sam build
sam deploy --guided --resolve-image-repos --capabilities CAPABILITY_IAM
#   AudioBucketName: cracknews-audio-<unique>   MongoUri: mongodb+srv://...
#   JwtSigningKey:   $(openssl rand -hex 32)     Region: ca-central-1
```

After deploy, use the stack outputs:

1. `ApiUrl` → `EXPO_PUBLIC_API_BASE_URL` in `mobile/eas.json` (preview + production).
2. `IngestPolicyArn` → attach to an IAM user for the ingest box; put its access keys in
   the box's `.env` as `S3_ACCESS_KEY` / `S3_SECRET_KEY`, with `S3_BUCKET=<AudioBucket>`,
   `S3_REGION=ca-central-1`, and `S3_ENDPOINT=` / `S3_FORCE_PATH_STYLE=false`.
3. `IngestHealthUrl` → add an HTTP monitor (UptimeRobot / Better Stack, free) that
   alerts on non-200. It goes red when the box stops checking in for 15 min or has
   produced no brief for 3 h.
4. MongoDB Atlas → Network Access: Lambda has no fixed IP, so allow `0.0.0.0/0` and use
   a strong, app-only database user; also allow the ingest box.

Redeploy after code changes: `sam build && sam deploy`. Secrets are NoEcho parameters
but end up as Lambda environment variables (visible to anyone with console access to
the function); move them to Secrets Manager when more people share the AWS account.

Local Lambda check (the base image includes the Lambda emulator):

```bash
docker build -t cnews-api:dev .
docker run --rm -p 9000:8080 -e JWT_SIGNING_KEY=$(openssl rand -hex 32) \
  -e MONGODB_URI=mongodb://host.docker.internal:27017 cnews-api:dev
```

## Independence

Sibling of `mobile/` and `realtime_ingestion/`. Contract: [../docs/real-time-ingestion/api.md](../docs/real-time-ingestion/api.md).
