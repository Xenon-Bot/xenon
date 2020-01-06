import asyncio

import time
import uuid

from aioredis import Redis


ACQUIRE_SCRIPT = """
if redis.call('setnx', KEYS[1], ARGV[1]) == 1 then
    redis.call('pexpire', KEYS[1], ARGV[2])
    return 1
else
    return 0
end
"""

RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""

EXTEND_SCRIPT = """
if redis.call('get', KEYS[1]) ~= ARGV[1] then
    return 0
end
local expiration = redis.call('pttl', KEYS[1])
if expiration < 0 then
    return 0
end
redis.call('pexpire', KEYS[1], expiration + ARGV[2])
return 1
"""

RENEW_SCRIPT = """
if redis.call('get', KEYS[1]) ~= ARGV[1] or redis.call('pttl', KEYS[1]) < 0 then
    return 0
end
redis.call('pexpire', KEYS[1], ARGV[2])
return 1
"""


class LockTimeoutError(Exception):
    """
    Raised if an instance is unable to acquire a lock
    Only raised when using the Context Manager
    """


class RedisLock:
    """
    Implementation of distributed locking with aioredis.
    """

    # Used internally for storing the SHA of loaded lua scripts
    _acquire_script = None
    _extend_script = None
    _release_script = None
    _renew_script = None

    def __init__(self, redis: Redis, key: str, timeout: int = 30, wait_timeout: int = 30, *, token: str = None):
        self.redis = redis
        self.key = key
        self.timeout = timeout
        self.wait_timeout = wait_timeout  # Can be None to wait forever
        self._token = token or str(uuid.uuid4())

    async def acquire_script(self) -> str:
        if self._acquire_script is None:
            self._acquire_script = await self.redis.script_load(ACQUIRE_SCRIPT)

        return self._acquire_script

    async def extend_script(self) -> str:
        if self._extend_script is None:
            self._extend_script = await self.redis.script_load(EXTEND_SCRIPT)

        return self._extend_script

    async def release_script(self) -> str:
        if self._release_script is None:
            self._release_script = await self.redis.script_load(RELEASE_SCRIPT)

        return self._release_script

    async def renew_script(self) -> str:
        if self._renew_script is None:
            self._renew_script = await self.redis.script_load(RENEW_SCRIPT)

        return self._renew_script

    async def __aenter__(self):
        if await self.acquire(self.timeout, self.wait_timeout):
            return self

        raise LockTimeoutError("Unable to acquire lock within timeout")

    async def __aexit__(self, *args, **kwargs):
        await self.release()

    async def is_owner(self) -> bool:
        """Determine if the instance is the owner of the lock"""
        lock_owner = await self.redis.get(self.key)
        return lock_owner == self._token.encode()

    async def acquire(self, timeout: int = None, wait_timeout: int = None) -> bool:
        """
        Attempt to acquire the lock
        """
        timeout = timeout or self.timeout
        wait_timeout = wait_timeout or self.wait_timeout

        start = int(time.time())
        while True:
            if await self._exec_script(
                await self.acquire_script(),
                keys=[self.key],
                args=[self._token, timeout * 1000],
            ):
                return True

            if wait_timeout is not None and int(time.time()) - start > wait_timeout:
                return False

            await asyncio.sleep(0.1)

    async def extend(self, added_time: int) -> bool:
        """
        Attempt to extend the lock by the amount of time, this will only extend
        if this instance owns the lock. Note that this is _incremental_, meaning
        that adding time will be on-top of however much time is already available.
        """
        return await self._exec_script(
            await self.extend_script(),
            keys=[self.key],
            args=[self._token, added_time * 1000],
        )

    async def release(self) -> bool:
        """
        Release the lock, this will only release if this instance of the lock
        is the one holding the lock.
        """
        return await self._exec_script(
            await self.release_script(),
            keys=[self.key],
            args=[self._token]
        )

    async def renew(self, timeout: int = None) -> bool:
        """
        Renew the lock, setting expiration to now + timeout (or self.timeout if not provided).
        This will only
        succeed if the instance is the lock owner.
        """
        return await self._exec_script(
            await self.renew_script(),
            keys=[self.key],
            args=[self._token, (timeout or self.timeout) * 1000],
        )

    async def _exec_script(self, sha: str, keys: [str], args: [str]) -> bool:
        """
        Execute the script with the provided keys and args.
        """
        return bool(await self.redis.evalsha(sha, keys=keys, args=args))
