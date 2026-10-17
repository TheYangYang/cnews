"""WAV helpers and Opus encoding via ffmpeg when available."""

from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from realtime_ingestion import config


def write_wav_from_samples(path: Path, samples: np.ndarray | list, sample_rate: int | None = None) -> int:
    """Write mono PCM WAV. Returns duration milliseconds."""
    rate = sample_rate or config.KOKORO_SAMPLE_RATE
    audio = np.concatenate(list(samples)) if not isinstance(samples, np.ndarray) else samples
    pcm = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())
    duration_ms = int(1000 * len(pcm) / rate)
    return duration_ms


def encode_opus_from_wav(wav_path: Path, opus_path: Path, *, bitrate: str = "32k") -> bool:
    """
    Convert WAV → Opus with ffmpeg.
    Returns True on success. Caller may fall back to WAV upload if False.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    opus_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(wav_path),
        "-c:a",
        "libopus",
        "-b:a",
        bitrate,
        "-ac",
        "1",
        str(opus_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return opus_path.is_file() and opus_path.stat().st_size > 0
    except (subprocess.CalledProcessError, OSError):
        return False
