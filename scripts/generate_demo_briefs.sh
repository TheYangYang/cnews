#!/usr/bin/env bash
# Local stand-in for Kokoro: speak each seed summary with macOS `say`, encode AAC.
# Production path remains: Ollama brief → Kokoro Opus → S3.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MEDIA="$ROOT/backend/CNews.Api/wwwroot/media"
mkdir -p "$MEDIA"

gen() {
  local id="$1"
  local text="$2"
  local aiff="$MEDIA/${id}.aiff"
  say -v Samantha -r 175 -o "$aiff" "$text"
  afconvert -f m4af -d aac "$aiff" "$MEDIA/${id}.m4a"
  rm -f "$aiff"
  echo "wrote $MEDIA/${id}.m4a"
}

gen story_demo_1 "Prairie storm knocks out power across southern Manitoba. High winds cut power to tens of thousands of homes. Crews are restoring lines overnight while schools delay openings in Winnipeg and Brandon."
gen story_demo_2 "Manitoba storm leaves wide outages and travel disrupted. Global reports highway closures and delayed flights as the weather system moves east. Utilities say full restoration may take days in rural areas."
gen story_demo_3 "Bank of Canada holds the policy rate as inflation cools. Officials kept the rate unchanged, citing slower price growth and a softer labour market. Markets expect cuts later this year if trends continue."
gen story_demo_4 "Canada and allies push a new Arctic research pact. Ottawa joined partners on shared ice mapping and climate monitoring, aiming to expand science access while keeping shipping routes safer."
gen story_demo_5 "Toronto transit plan adds late-night weekend trains. The city will trial extended subway hours on Fridays and Saturdays for nightlife workers and event crowds downtown."
gen story_demo_6 "Health agencies urge early flu shots this fall. Doctors expect an earlier peak and want high-risk groups vaccinated first. Clinics are expanding evening appointments in several provinces."

# Sync into running build output if present
for dest in \
  "$ROOT/backend/CNews.Api/bin/Release/net10.0/wwwroot/media" \
  "$ROOT/backend/CNews.Api/bin/Debug/net10.0/wwwroot/media"
do
  if [[ -d "$(dirname "$dest")" ]]; then
    mkdir -p "$dest"
    cp -f "$MEDIA"/*.m4a "$dest/"
  fi
done
