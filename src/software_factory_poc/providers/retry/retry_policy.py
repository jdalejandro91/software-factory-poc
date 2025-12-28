from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from tenacity import AsyncRetrying, RetryError, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from software_factory_poc.core.exceptions.provider_error import ProviderError

_T = TypeVar("_T")


def _retryable(exc: BaseException) -> bool:
    return isinstance(exc, ProviderError) and exc.retryable


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3

    async def run(self, fn: Callable[[], Awaitable[_T]]) -> _T:
        try:
            return await self._retrying().call(fn)
        except RetryError as err:
            raise err.last_attempt.result()  # type: ignore[misc]

    def _retrying(self) -> AsyncRetrying:
        return AsyncRetrying(
            retry=retry_if_exception(_retryable),
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential_jitter(initial=0.25, max=5.0),
            reraise=True,
        )
