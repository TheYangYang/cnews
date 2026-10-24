"""Redis Streams broker.

Uses a local Redis server when one is listening. Otherwise the same XADD /
XREADGROUP / SET commands run against an in-process Redis so the workers stay
decoupled from polling without an extra install.
"""

from __future__ import annotations

import asyncio
import time

import redis.asyncio as aioredis
import fakeredis.aioredis
from redis.exceptions import ResponseError

from realtime_ingestion import config


class RedisBroker:
    def __init__(self, client: aioredis.Redis, label: str, *, durable: bool = True) -> None:
        self.redis = client
        self.label = label
        # False for the in-process fallback: its streams vanish when the process exits.
        self.durable = durable

    async def ensure_group(self, stream: str, group: str) -> None:
        try:
            await self.redis.xgroup_create(stream, group, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def publish(self, stream: str, fields: dict[str, str]) -> str:
        message_id = await self.redis.xadd(
            stream, fields, maxlen=config.STREAM_MAXLEN, approximate=True
        )
        return str(message_id)

    async def read(
        self,
        stream: str,
        group: str,
        consumer: str,
        *,
        count: int = 1,
        block_ms: int = 2000,
    ) -> list[tuple[str, dict[str, str]]]:
        started = time.monotonic()
        raw = await self.redis.xreadgroup(
            group,
            consumer,
            {stream: ">"},
            count=count,
            block=block_ms,
        )
        messages = _entries(raw)
        # The in-process server returns immediately when a stream is empty.
        # Sleep out the requested block so socket work on the loop can run.
        if not messages and (time.monotonic() - started) < (block_ms / 1000) / 2:
            await asyncio.sleep(block_ms / 1000)
        return messages

    async def read_pending(
        self, stream: str, group: str, consumer: str, *, count: int = 100
    ) -> list[tuple[str, dict[str, str]]]:
        """Messages this consumer received but never acked (crash or shutdown mid-job).

        A ">" read never returns these again, so workers drain them on startup.
        """
        raw = await self.redis.xreadgroup(group, consumer, {stream: "0"}, count=count)
        # Entries trimmed from the stream come back with no fields; ack them away.
        messages = []
        for message_id, fields in _entries(raw):
            if fields:
                messages.append((message_id, fields))
            else:
                await self.ack(stream, group, message_id)
        return messages

    async def ack(self, stream: str, group: str, message_id: str) -> None:
        await self.redis.xack(stream, group, message_id)

    async def mark_seen(self, url_hash: str, title_hash: str, ttl_seconds: int) -> bool:
        """Return False when this URL or title was already claimed in the window."""
        url_key = f"seen:url:{url_hash}"
        title_key = f"seen:title:{title_hash}"
        if await self.redis.exists(url_key) or await self.redis.exists(title_key):
            return False
        await self.redis.set(url_key, "1", ex=ttl_seconds)
        await self.redis.set(title_key, "1", ex=ttl_seconds)
        return True

    async def close(self) -> None:
        await self.redis.aclose()


def _entries(raw) -> list[tuple[str, dict[str, str]]]:
    messages: list[tuple[str, dict[str, str]]] = []
    for item in raw or []:
        for message_id, fields in item[1]:
            messages.append(
                (str(message_id), {str(key): str(value) for key, value in (fields or {}).items()})
            )
    return messages


def enqueued_at(message_id: str) -> float:
    """Wall-clock seconds when Redis accepted the message (ids are '<ms>-<seq>')."""
    try:
        return int(message_id.split("-", 1)[0]) / 1000
    except ValueError:
        return time.time()


async def open_broker(url: str) -> RedisBroker:
    probe = aioredis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=0.6,
        socket_timeout=0.6,
    )
    try:
        await probe.ping()
    except Exception:
        try:
            await probe.aclose()
        except Exception:
            pass
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        return RedisBroker(
            fake, "in-process Redis Streams (Redis server not running)", durable=False
        )
    await probe.aclose()
    client = aioredis.from_url(url, decode_responses=True)
    return RedisBroker(client, "Redis Streams")
