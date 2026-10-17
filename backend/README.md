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

## Config

See root `.env.example` and `CNews.Api/appsettings.json`.

## Lambda

```bash
docker build -t cnews-api:dev .
docker run --rm -p 9000:8080 --env-file ../.env cnews-api:dev
```

Base image: `public.ecr.aws/lambda/dotnet:10`.

## Independence

Sibling of `mobile/` and `realtime_ingestion/`. Contract: [../docs/real-time-ingestion/api.md](../docs/real-time-ingestion/api.md).
