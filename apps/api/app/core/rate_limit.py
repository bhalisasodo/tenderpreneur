import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, Request, status
from app.core.config import settings


class InMemoryRateLimiter:
    """Sliding-window rate limiter for public API endpoints."""

    def __init__(self, requests_per_minute: int = 20):
        self.requests_per_minute = requests_per_minute
        self._history: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.time()
        window_start = now - 60.0

        # Purge entries older than 60 seconds
        recent = [t for t in self._history[key] if t > window_start]
        self._history[key] = recent

        if len(recent) >= self.requests_per_minute:
            retry_after = int(60.0 - (now - recent[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Too many requests. Please retry after {retry_after} seconds.",
                },
                headers={"Retry-After": str(retry_after)},
            )

        self._history[key].append(now)

    def reset(self) -> None:
        """Clears rate limit history (primarily for tests)."""
        self._history.clear()


_auth_rate_limiter = InMemoryRateLimiter(requests_per_minute=settings.rate_limit_auth_per_minute)


def rate_limit_auth(request: Request) -> None:
    """Dependency that applies rate limiting to public auth endpoints."""
    client_ip = request.client.host if request.client else "unknown_client"
    _auth_rate_limiter.check(client_ip)


def reset_auth_rate_limiter() -> None:
    _auth_rate_limiter.reset()
