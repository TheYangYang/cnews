"""Share one GPU between Ollama (briefs) and Kokoro (speech) by taking turns.

Order of work on a busy news day: brief first, then speech, then storyline/framing
enrichment. The AI worker owns brief-vs-enrichment; this gate owns LLM-vs-speech.

- LLM calls run whenever no speech turn is active.
- A speech turn starts once the LLM has been quiet for ``idle_grace`` seconds, or
  right away when a brief has waited ``max_lag`` seconds (so speech never starves
  during a long burst).
- During a turn, LLM calls wait. The turn hands the GPU back when speech runs out,
  or when LLM work is waiting and the turn has served its quota (``turn_min`` for an
  idle turn, ``turn_max`` for a forced one). Batching amortizes the model swap.
- ``on_turn_start`` / ``on_turn_end`` hooks swap VRAM (unload Ollama, move Kokoro
  between CPU and GPU) on small cards such as a GTX 1060.

When scheduling is off (gate disabled, or Kokoro runs on CPU), speech never waits on
the LLM; jobs are only serialized.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable

from realtime_ingestion import config

Hook = Callable[[], Awaitable[None]]


class GpuGate:
    def __init__(
        self,
        *,
        idle_grace: float = config.TTS_IDLE_GRACE_SECONDS,
        max_lag: float = config.TTS_MAX_LAG_SECONDS,
        turn_min: int = config.TTS_TURN_MIN,
        turn_max: int = config.TTS_TURN_MAX,
        clock: Callable[[], float] = time.monotonic,
        poll: float = 0.25,
    ) -> None:
        self.scheduling = config.GPU_GATE_ENABLED
        self.idle_grace = idle_grace
        self.max_lag = max_lag
        self.turn_min = turn_min
        self.turn_max = max(turn_max, turn_min)
        self.on_turn_start: Hook | None = None
        self.on_turn_end: Hook | None = None
        self._clock = clock
        self._poll = poll
        self._cond = asyncio.Condition()
        self._llm_active = 0
        self._llm_waiting = 0
        self._llm_busy = 0
        self._last_llm = float("-inf")
        self._turn = False
        self._turn_forced = False
        self._turn_served = 0
        self._tts_active = False
        self._tts_wanted = 0
        self._tts_lock = asyncio.Lock()
        self._last_tts = float("-inf")
        self._ending = False
        self._preempt = False
        # The speech worker re-reads its stream within ~0.2 s between briefs in a turn.
        self.abandon_after = 1.5
        self.last_hook_error: Exception | None = None

    # ----- state the workers read -------------------------------------------------

    @property
    def speech_waiting(self) -> bool:
        """True while speech has a brief in hand that it cannot start yet."""
        return self._tts_wanted > 0

    @property
    def in_turn(self) -> bool:
        return self.scheduling and self._turn

    # ----- LLM side ---------------------------------------------------------------

    @asynccontextmanager
    async def busy(self) -> AsyncIterator[None]:
        """Hold around a whole brief job so speech does not grab the GPU between calls."""
        self._llm_busy += 1
        try:
            yield
        finally:
            self._llm_busy -= 1
            self._last_llm = self._clock()

    @asynccontextmanager
    async def llm(self) -> AsyncIterator[None]:
        """Hold around one Ollama request."""
        self._llm_waiting += 1
        try:
            while self.scheduling and (self._turn or self._preempt):
                if self._turn_abandoned():
                    await self.end_turn()
                    continue
                async with self._cond:
                    try:
                        await asyncio.wait_for(self._cond.wait(), timeout=self._poll)
                    except asyncio.TimeoutError:
                        pass
        finally:
            self._llm_waiting -= 1
        async with self._cond:
            self._llm_active += 1
        try:
            yield
        finally:
            async with self._cond:
                self._llm_active -= 1
                self._last_llm = self._clock()
                self._cond.notify_all()

    # ----- speech side ------------------------------------------------------------

    @asynccontextmanager
    async def tts(self, *, lag_seconds: float, stop: asyncio.Event) -> AsyncIterator[bool]:
        """Hold around one Kokoro render. Yields False if ``stop`` fired while waiting."""
        async with self._tts_lock:
            if not self.scheduling:
                yield not stop.is_set()
                return
            granted = await self._wait_for_turn(lag_seconds, stop)
            if not granted:
                yield False
                return
            self._tts_active = True
            try:
                yield True
            finally:
                self._tts_active = False
                self._last_tts = self._clock()
                self._turn_served += 1
                if self._should_yield():
                    await self.end_turn()

    async def end_turn(self) -> None:
        """Hand the GPU back to the LLM (speech ran out, or quota reached)."""
        if not self._turn or self._tts_active or self._ending:
            return
        self._ending = True
        try:
            await self._run_hook(self.on_turn_end)
        finally:
            async with self._cond:
                self._turn = False
                self._turn_forced = False
                self._turn_served = 0
                self._ending = False
                self._cond.notify_all()

    async def _wait_for_turn(self, lag_seconds: float, stop: asyncio.Event) -> bool:
        loop = asyncio.get_running_loop()
        began = loop.time()
        self._tts_wanted += 1
        try:
            while not stop.is_set():
                if self._turn:
                    return True
                forced = lag_seconds + (loop.time() - began) >= self.max_lag
                if forced:
                    # Starved: new LLM calls queue behind us; the one in flight finishes.
                    self._preempt = True
                if self._llm_active == 0 and (forced or self._llm_idle()):
                    await self._start_turn(forced=forced)
                    return True
                async with self._cond:
                    try:
                        await asyncio.wait_for(self._cond.wait(), timeout=self._poll)
                    except asyncio.TimeoutError:
                        pass
            return False
        finally:
            self._tts_wanted -= 1
            self._preempt = False

    async def _start_turn(self, *, forced: bool) -> None:
        async with self._cond:
            self._turn = True
            self._turn_forced = forced
            self._turn_served = 0
            self._last_tts = self._clock()
        await self._run_hook(self.on_turn_start)

    async def _run_hook(self, hook: Hook | None) -> None:
        # A failed VRAM swap must never leave the gate stuck in a turn.
        if hook is None:
            return
        try:
            await hook()
        except Exception as exc:  # noqa: BLE001 - reported through the worker's event log
            self.last_hook_error = exc

    def _turn_abandoned(self) -> bool:
        """Safety net: speech left a turn open without work in hand (e.g. its worker died)."""
        if self._tts_active or self._tts_wanted or self._ending:
            return False
        return self._clock() - self._last_tts >= self.abandon_after

    def _llm_idle(self) -> bool:
        if self._llm_busy or self._llm_waiting:
            return False
        return self._clock() - self._last_llm >= self.idle_grace

    def _should_yield(self) -> bool:
        if not (self._llm_waiting or self._llm_busy):
            return False
        quota = self.turn_max if self._turn_forced else self.turn_min
        return self._turn_served >= quota


# Shared singleton for AI + TTS workers in one process
GATE = GpuGate()
