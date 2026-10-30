"""In-memory Redis double used by backend tests.

It implements the commands these tests actually exercise, with the semantics
that matter for correctness:

* ``SET ... NX EX`` only stores while the key is absent and records a real TTL.
* ``TTL`` counts down, expired keys read as absent.
* ``EVAL`` understands the compare-and-delete script used to release a ledger
  lock, so a wrong token never deletes another request's lock.

Scripts outside that contract raise instead of silently returning a truthy
mock, which keeps tests honest about what is being simulated.
"""

from __future__ import annotations

import time
from collections.abc import Callable


LOCK_RELEASE_MARKERS = (
    'redis.call("get", keys[1]) == argv[1]',
    'redis.call("del", keys[1])',
)
LOCK_RENEW_MARKERS = (
    'redis.call("get", keys[1]) == argv[1]',
    'redis.call("expire", keys[1], argv[2])',
)


class FakeRedis:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self.values: dict[str, str] = {}
        self.expires_at: dict[str, float] = {}
        self.calls: list[tuple] = []
        self._clock = clock or time.time

    # -- helpers ---------------------------------------------------------
    def _purge(self, key: str) -> None:
        deadline = self.expires_at.get(key)
        if deadline is not None and deadline <= self._clock():
            self.values.pop(key, None)
            self.expires_at.pop(key, None)

    def set_calls(self) -> list[tuple]:
        return [call for call in self.calls if call[0] == "set"]

    def acquire_calls(self) -> list[tuple]:
        return [call for call in self.set_calls() if call[3] is True]

    def eval_calls(self) -> list[tuple]:
        return [call for call in self.calls if call[0] == "eval"]

    # -- commands --------------------------------------------------------
    async def set(
        self,
        key,
        value,
        *,
        nx: bool = False,
        xx: bool = False,
        ex=None,
        px=None,
        keepttl: bool = False,
        **_: object,
    ):
        self._purge(key)
        self.calls.append(("set", key, str(value), nx, ex))
        if nx and key in self.values:
            return None
        if xx and key not in self.values:
            return None

        self.values[key] = str(value)
        if keepttl:
            pass
        elif ex is not None:
            self.expires_at[key] = self._clock() + float(ex)
        elif px is not None:
            self.expires_at[key] = self._clock() + float(px) / 1000
        else:
            self.expires_at.pop(key, None)
        return True

    async def get(self, key):
        self.calls.append(("get", key))
        self._purge(key)
        return self.values.get(key)

    async def delete(self, *keys):
        removed = 0
        for key in keys:
            self.calls.append(("delete", key))
            self._purge(key)
            if key in self.values:
                removed += 1
            self.values.pop(key, None)
            self.expires_at.pop(key, None)
        return removed

    async def exists(self, key):
        self._purge(key)
        return int(key in self.values)

    async def ttl(self, key):
        self.calls.append(("ttl", key))
        self._purge(key)
        if key not in self.values:
            return -2
        deadline = self.expires_at.get(key)
        if deadline is None:
            return -1
        return max(1, int(deadline - self._clock()))

    async def expireat(self, key, when):
        self.calls.append(("expireat", key, when))
        self._purge(key)
        if key not in self.values:
            return False
        self.expires_at[key] = (
            when.timestamp() if hasattr(when, "timestamp") else float(when)
        )
        return True

    async def incrbyfloat(self, key, amount):
        self.calls.append(("incrbyfloat", key, amount))
        self._purge(key)
        current = float(self.values.get(key, 0)) + float(amount)
        self.values[key] = str(current)
        return current

    async def publish(self, channel, message):
        self.calls.append(("publish", channel, message))
        return 0

    async def eval(self, script, numkeys, *keys_and_args):
        keys = tuple(keys_and_args[:numkeys])
        args = tuple(keys_and_args[numkeys:])
        self.calls.append(("eval", keys, args))
        normalized = " ".join(script.lower().split())

        if all(marker in normalized for marker in LOCK_RELEASE_MARKERS):
            key = keys[0]
            self._purge(key)
            if self.values.get(key) != str(args[0]):
                return 0
            self.values.pop(key, None)
            self.expires_at.pop(key, None)
            return 1

        if all(marker in normalized for marker in LOCK_RENEW_MARKERS):
            key = keys[0]
            self._purge(key)
            if self.values.get(key) != str(args[0]):
                return 0
            self.expires_at[key] = time.time() + float(args[1])
            return 1

        raise NotImplementedError(f"FakeRedis.eval does not simulate: {script!r}")

    async def aclose(self):
        return None
