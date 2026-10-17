"""Serialize heavy GPU work: Ollama briefs win over Kokoro TTS."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from realtime_ingestion import config


class GpuGate:
    """Process-local gate plus optional Ollama /api/ps check."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._ollama_inflight = 0
        self._tts_inflight = 0

    def begin_ollama(self) -> None:
        self._ollama_inflight += 1

    def end_ollama(self) -> None:
        self._ollama_inflight = max(0, self._ollama_inflight - 1)

    async def ollama_busy_remote(self) -> bool:
        if not config.GPU_GATE_ENABLED:
            return False
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{config.OLLAMA_URL}/api/ps")
                if response.status_code != 200:
                    return self._ollama_inflight > 0
                models = response.json().get("models") or []
                return len(models) > 0 or self._ollama_inflight > 0
        except Exception:
            return self._ollama_inflight > 0

    async def wait_for_tts(self, stop: asyncio.Event, *, max_wait_s: float = 120.0) -> bool:
        """Return True when TTS may start; False if stopped or timed out."""
        if not config.GPU_GATE_ENABLED:
            async with self._lock:
                if self._tts_inflight > 0:
                    return False
                self._tts_inflight = 1
                return True

        deadline = time.monotonic() + max_wait_s
        delay = 2.0
        while not stop.is_set():
            remote_busy = await self.ollama_busy_remote()
            async with self._lock:
                local_busy = self._ollama_inflight > 0 or self._tts_inflight > 0
                if not remote_busy and not local_busy:
                    self._tts_inflight = 1
                    return True
            if time.monotonic() >= deadline:
                return False
            await asyncio.sleep(delay)
            delay = min(delay * 1.4, 15.0)
        return False

    def release_tts(self) -> None:
        self._tts_inflight = 0


# Shared singleton for AI + TTS workers in one process
GATE = GpuGate()
