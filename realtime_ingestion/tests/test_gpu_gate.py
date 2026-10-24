"""GPU turn-taking rules. Run: python -m unittest discover -s realtime_ingestion/tests"""

from __future__ import annotations

import asyncio
import unittest

from realtime_ingestion.tts.gpu_gate import GpuGate


def _gate(**kwargs) -> GpuGate:
    options = dict(idle_grace=0.15, max_lag=60.0, turn_min=2, turn_max=4, poll=0.01)
    options.update(kwargs)
    gate = GpuGate(**options)
    gate.scheduling = True
    return gate


class GpuGateTest(unittest.IsolatedAsyncioTestCase):
    async def test_speech_waits_for_llm_quiet_then_llm_waits_for_turn(self) -> None:
        gate = _gate()
        events: list[str] = []

        async def start() -> None:
            events.append("turn_start")

        async def end() -> None:
            events.append("turn_end")

        gate.on_turn_start, gate.on_turn_end = start, end
        stop = asyncio.Event()

        async with gate.llm():
            events.append("llm")

        async def speak() -> None:
            async with gate.tts(lag_seconds=0, stop=stop) as granted:
                self.assertTrue(granted)
                events.append("tts")
                await asyncio.sleep(0.05)

        loop = asyncio.get_running_loop()
        began = loop.time()
        await speak()
        self.assertGreaterEqual(loop.time() - began, 0.1, "speech should wait out the idle grace")
        self.assertTrue(gate.in_turn)

        async def llm_call() -> None:
            async with gate.llm():
                events.append("llm2")

        waiter = asyncio.create_task(llm_call())
        await asyncio.sleep(0.03)
        self.assertNotIn("llm2", events, "LLM must wait while a speech turn is open")
        await gate.end_turn()
        await waiter
        self.assertEqual(events, ["llm", "turn_start", "tts", "turn_end", "llm2"])

    async def test_busy_brief_job_blocks_speech_until_forced_by_lag(self) -> None:
        gate = _gate(max_lag=0.3)
        stop = asyncio.Event()
        order: list[str] = []

        async def brief_burst() -> None:
            async with gate.busy():
                for _ in range(40):
                    async with gate.llm():
                        await asyncio.sleep(0.01)
            order.append("burst_done")

        async def speak() -> None:
            async with gate.tts(lag_seconds=0, stop=stop):
                order.append("tts")

        burst = asyncio.create_task(brief_burst())
        await asyncio.sleep(0.02)
        await asyncio.gather(speak(), burst)
        # The burst runs ~0.4s+; lag 0.3s forces speech in before it finishes.
        self.assertEqual(order[0], "tts")

    async def test_turn_yields_to_waiting_llm_after_quota(self) -> None:
        gate = _gate(turn_min=2)
        stop = asyncio.Event()
        spoken: list[int] = []

        async def speak(index: int) -> None:
            async with gate.tts(lag_seconds=0, stop=stop):
                spoken.append(index)
                await asyncio.sleep(0.02)

        await speak(0)
        llm_done = asyncio.Event()

        async def llm_call() -> None:
            async with gate.llm():
                llm_done.set()

        waiter = asyncio.create_task(llm_call())
        await asyncio.sleep(0.01)
        await speak(1)  # second brief meets turn_min=2 with LLM waiting -> yield
        await asyncio.wait_for(waiter, timeout=1)
        self.assertTrue(llm_done.is_set())
        self.assertFalse(gate.in_turn)

    async def test_llm_reclaims_abandoned_turn(self) -> None:
        gate = _gate()
        gate.abandon_after = 0.05
        stop = asyncio.Event()
        async with gate.tts(lag_seconds=0, stop=stop):
            pass
        self.assertTrue(gate.in_turn)
        # Nobody calls end_turn (speech worker died); the LLM must not hang.
        async def llm_call() -> None:
            async with gate.llm():
                pass

        await asyncio.wait_for(llm_call(), timeout=1)
        self.assertFalse(gate.in_turn)

    async def test_failed_swap_hook_does_not_wedge_gate(self) -> None:
        gate = _gate()

        async def broken() -> None:
            raise RuntimeError("unload failed")

        gate.on_turn_start = broken
        gate.on_turn_end = broken
        stop = asyncio.Event()
        async with gate.tts(lag_seconds=0, stop=stop) as granted:
            self.assertTrue(granted)
        await gate.end_turn()
        self.assertFalse(gate.in_turn)
        self.assertIsInstance(gate.last_hook_error, RuntimeError)

    async def test_stop_while_waiting_is_not_granted(self) -> None:
        gate = _gate(idle_grace=10)
        stop = asyncio.Event()
        async with gate.llm():
            pass

        async def speak() -> bool:
            async with gate.tts(lag_seconds=0, stop=stop) as granted:
                return granted

        task = asyncio.create_task(speak())
        await asyncio.sleep(0.03)
        stop.set()
        self.assertFalse(await asyncio.wait_for(task, timeout=1))
        self.assertFalse(gate.speech_waiting)

    async def test_without_scheduling_speech_never_waits(self) -> None:
        gate = _gate(idle_grace=10)
        gate.scheduling = False
        stop = asyncio.Event()
        async with gate.busy():
            async with gate.llm():
                async with gate.tts(lag_seconds=0, stop=stop) as granted:
                    self.assertTrue(granted)
        self.assertFalse(gate.in_turn)


if __name__ == "__main__":
    unittest.main()
