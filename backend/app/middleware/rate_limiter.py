"""Rate limiting middleware for API endpoints."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests: int  # Maximum number of requests
    seconds: int  # Time window in seconds
    key_prefix: str = "rate_limit"  # Prefix for the rate limit key


@dataclass
class ClientState:
    """Tracks request state for a single client."""

    timestamps: list[float] = field(default_factory=list)
    blocked_until: float = 0.0


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for development and small-scale deployments.
    
    For production with multiple instances, use Redis-backed rate limiting.
    """

    def __init__(self) -> None:
        self._clients: Dict[str, ClientState] = defaultdict(ClientState)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str, config: RateLimitConfig) -> tuple[bool, float]:
        """Check if a request is allowed under the rate limit.
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        async with self._lock:
            now = time.time()
            client = self._clients[key]

            # Check if client is currently blocked
            if client.blocked_until > now:
                retry_after = client.blocked_until - now
                return False, retry_after

            # Remove timestamps outside the window
            window_start = now - config.seconds
            client.timestamps = [ts for ts in client.timestamps if ts > window_start]

            # Check if under limit
            if len(client.timestamps) < config.requests:
                client.timestamps.append(now)
                return True, 0.0

            # Over limit - calculate when next request is allowed
            oldest_timestamp = min(client.timestamps)
            retry_after = oldest_timestamp + config.seconds - now
            
            # Block the client if they exceed limit repeatedly
            if retry_after > config.seconds:
                client.blocked_until = now + config.seconds
                retry_after = config.seconds

            return False, retry_after

    async def reset(self, key: str) -> None:
        """Reset rate limit for a specific client."""
        async with self._lock:
            if key in self._clients:
                del self._clients[key]


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()

# Predefined rate limit configurations
RATE_LIMITS = {
    "auth_register": RateLimitConfig(requests=5, seconds=60, key_prefix="auth_register"),  # 5 per minute
    "auth_login": RateLimitConfig(requests=10, seconds=60, key_prefix="auth_login"),  # 10 per minute
    "email_send": RateLimitConfig(requests=3, seconds=60, key_prefix="email_send"),  # 3 per minute
    "onboarding": RateLimitConfig(requests=30, seconds=60, key_prefix="onboarding"),  # 30 per minute
    "default": RateLimitConfig(requests=100, seconds=60, key_prefix="default"),  # 100 per minute
}


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _create_rate_limit_key(request: Request, limit_type: str) -> str:
    """Create a unique rate limit key for the client."""
    ip = _get_client_ip(request)
    return f"{limit_type}:{ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Starlette's BaseHTTPMiddleware."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/ready"] or request.url.path.startswith("/static"):
            return await call_next(request)

        # Determine rate limit type based on path
        path = request.url.path
        if "/register" in path or "/registration" in path:
            limit_config = RATE_LIMITS["auth_register"]
            limit_type = "auth_register"
        elif "/login" in path or "/magic-link" in path:
            limit_config = RATE_LIMITS["auth_login"]
            limit_type = "auth_login"
        elif "/email" in path or "/resend" in path:
            limit_config = RATE_LIMITS["email_send"]
            limit_type = "email_send"
        elif "/onboarding" in path:
            limit_config = RATE_LIMITS["onboarding"]
            limit_type = "onboarding"
        else:
            limit_config = RATE_LIMITS["default"]
            limit_type = "default"

        rate_limit_key = _create_rate_limit_key(request, limit_type)
        allowed, retry_after = await _rate_limiter.is_allowed(rate_limit_key, limit_config)

        if not allowed:
            logger.warning(
                "Rate limit exceeded for %s (IP: %s, Type: %s)",
                rate_limit_key,
                _get_client_ip(request),
                limit_type,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": "For mange forespørsler. Vennligst prøv igjen senere.",
                    "retry_after": int(retry_after) + 1,
                },
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit_config.requests)
        remaining_client = _rate_limiter._clients.get(rate_limit_key, ClientState())
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, limit_config.requests - len(remaining_client.timestamps))
        )
        
        return response


def setup_rate_limiting(app: FastAPI) -> None:
    """Add rate limiting middleware to the FastAPI application."""
    app.add_middleware(RateLimitMiddleware)


# Dependency for endpoint-specific rate limiting
async def check_rate_limit(
    request: Request,
    limit_type: str = "default",
) -> None:
    """Dependency to check rate limit for specific endpoints.
    
    Use this for fine-grained control on individual endpoints.
    
    Example:
        @router.post("/sensitive-action")
        async def sensitive_action(
            _: None = Depends(check_rate_limit(limit_type="auth_register")),
        ):
            ...
    """
    config = RATE_LIMITS.get(limit_type, RATE_LIMITS["default"])
    key = _create_rate_limit_key(request, limit_type)
    allowed, retry_after = await _rate_limiter.is_allowed(key, config)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="For mange forespørsler. Vennligst prøv igjen senere.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
