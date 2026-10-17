#!/usr/bin/env python3
"""Generate Kokoro → WAV → Opus seed briefs for CrackNews demos.

Requires: .venv with kokoro + torch, ffmpeg on PATH.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from realtime_ingestion.tts.opus import encode_opus_from_wav, write_wav_from_samples  # noqa: E402

MEDIA = ROOT / "backend" / "CNews.Api" / "wwwroot" / "media"
VOICE = "af_heart"

BRIEFS = [
    ("story_demo_1", "Prairie storm knocks out power across southern Manitoba. High winds cut power to tens of thousands of homes. Crews are restoring lines overnight while schools delay openings in Winnipeg and Brandon."),
    ("story_demo_2", "Manitoba storm leaves wide outages and travel disrupted. Global reports highway closures and delayed flights as the weather system moves east. Utilities say full restoration may take days in rural areas."),
    ("story_demo_3", "Bank of Canada holds the policy rate as inflation cools. Officials kept the rate unchanged, citing slower price growth and a softer labour market. Markets expect cuts later this year if trends continue."),
    ("story_demo_4", "Canada and allies push a new Arctic research pact. Ottawa joined partners on shared ice mapping and climate monitoring, aiming to expand science access while keeping shipping routes safer."),
    ("story_demo_5", "Toronto transit plan adds late-night weekend trains. The city will trial extended subway hours on Fridays and Saturdays for nightlife workers and event crowds downtown."),
    ("story_demo_6", "Health agencies urge early flu shots this fall. Doctors expect an earlier peak and want high-risk groups vaccinated first. Clinics are expanding evening appointments in several provinces."),
]


def main() -> None:
    from kokoro import KPipeline

    MEDIA.mkdir(parents=True, exist_ok=True)
    print("Loading Kokoro pipeline (first run downloads model weights)…")
    pipeline = KPipeline(lang_code="a")

    for story_id, text in BRIEFS:
        wav = MEDIA / f"{story_id}.wav"
        opus = MEDIA / f"{story_id}.opus"
        print(f"Rendering {story_id}…")
        chunks = []
        for _g, _p, audio in pipeline(text, voice=VOICE, speed=1.0):
            chunks.append(audio)
        if not chunks:
            raise RuntimeError(f"No audio for {story_id}")
        duration_ms = write_wav_from_samples(wav, chunks)
        if not encode_opus_from_wav(wav, opus):
            raise RuntimeError(f"ffmpeg Opus encode failed for {story_id}")
        # AAC twin for iOS Expo (expo-audio); Opus is the production artifact.
        m4a = MEDIA / f"{story_id}.m4a"
        import subprocess

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(wav),
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                str(m4a),
            ],
            check=True,
            capture_output=True,
        )
        print(
            f"  → {opus.name} ({opus.stat().st_size} B) + {m4a.name} "
            f"({m4a.stat().st_size} B, {duration_ms} ms)"
        )
        for dest in (
            ROOT / "backend" / "CNews.Api" / "bin" / "Release" / "net10.0" / "wwwroot" / "media",
            ROOT / "backend" / "CNews.Api" / "bin" / "Debug" / "net10.0" / "wwwroot" / "media",
        ):
            if dest.parent.exists():
                dest.mkdir(parents=True, exist_ok=True)
                (dest / opus.name).write_bytes(opus.read_bytes())
                (dest / m4a.name).write_bytes(m4a.read_bytes())

    print("Done. Seed uses local/story_demo_N.m4a (iOS) + .opus (prod).")


if __name__ == "__main__":
    main()
