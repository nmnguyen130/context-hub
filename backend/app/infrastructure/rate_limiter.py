import hashlib
import logging
import uuid
from dataclasses import dataclass
from typing import Callable, Protocol

from fastapi import HTTPException, Request, Response, status
from redis.exceptions import RedisError

from app.core.context import try_current_context

logger = logging.getLogger(__name__)


# Lua script to perform sliding window rate limit atomically.
# Utilizes Redis-side clock (via redis.call('time')) to prevent clock drift.
# Keys:
#   KEYS[1]: Rate limit key
# Arguments:
#   ARGV[1]: Window size (seconds)
#   ARGV[2]: Max requests allowed (int)
#   ARGV[3]: Unique member ID (UUID string)
# Returns:
#   {allowed (1/0), remaining_count (int), retry_after_seconds (int)}
LUA_SLIDING_WINDOW = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local member = ARGV[3]

local time = redis.call('TIME')
local now = tonumber(time[1]) + tonumber(time[2]) / 1000000

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local current = redis.call('ZCARD', key)

if current < limit then
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, window)
    return {1, limit - current - 1, 0}
end

local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')[2]
local retry = oldest and math.ceil(tonumber(oldest) + window - now) or window
return {0, 0, retry > 0 and retry or 1}
"""


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """Defines requests limit and window duration for rate limiting."""

    key_prefix: str
    requests: int
    window_seconds: int


class LimitPolicyProvider(Protocol):
    """Protocol for dynamic rate limiting policy resolution."""

    def get_policy(self, request: Request) -> RateLimitPolicy: ...


class PlanPolicyProvider(LimitPolicyProvider):
    """Resolves rate limit policies based on tenant subscription plan."""

    def __init__(
        self,
        default_requests: int = 60,
        default_window: int = 60,
    ):
        self.default_requests = default_requests
        self.default_window = default_window

    def get_policy(self, request: Request) -> RateLimitPolicy:
        """Resolves policy by evaluating subscription tier."""
        ctx = try_current_context()
        plan = ctx.plan if ctx else "free"
        requests = {"enterprise": 2000, "pro": 500}.get(plan.lower(), self.default_requests)

        return RateLimitPolicy(
            key_prefix="api",
            requests=requests,
            window_seconds=self.default_window,
        )


class RateLimiter:
    """FastAPI dependency enforcing sliding window rate limits using Redis."""

    def __init__(
        self,
        policy_provider: LimitPolicyProvider,
        key_func: Callable[[Request, RateLimitPolicy], str] | None = None,
        fail_open: bool = True,
    ):
        self.policy_provider = policy_provider
        self.key_func = key_func or self._default_key
        self.fail_open = fail_open

    def _default_key(self, request: Request, policy: RateLimitPolicy) -> str:
        """Generates a structured rate limit key based on identity priority.

        Priority order:
          1. API Key: `rate_limit:apikey:{key_hash}:{policy_prefix}:{route_path}`
          2. User & Tenant: `rate_limit:tenant:{tenant_id}:user:{user_id}:{policy_prefix}:{route_path}`
          3. Tenant only: `rate_limit:tenant:{tenant_id}:{policy_prefix}:{route_path}`
          4. IP (Anonymous): `rate_limit:ip:{client_ip}:{policy_prefix}:{route_path}`
        """
        api_key = request.headers.get("x-api-key")
        if api_key:
            target = f"apikey:{hashlib.sha256(api_key.encode()).hexdigest()}"
        else:
            ctx = try_current_context()
            if ctx and ctx.user_id:
                target = f"tenant:{ctx.tenant_id}:user:{ctx.user_id}"
            elif ctx and ctx.tenant_id:
                target = f"tenant:{ctx.tenant_id}"
            else:
                client_ip = request.client.host if request.client else "unknown"
                target = f"ip:{client_ip}"

        route = request.scope.get("route")
        route_path = route.path if route else request.url.path
        return f"rate_limit:{target}:{policy.key_prefix}:{route_path}"

    async def __call__(self, request: Request, response: Response) -> None:
        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            logger.warning("Redis unavailable. Rate limit skipped.")
            return

        # Retrieve the pre-registered Lua script from FastAPI app state
        script = getattr(request.app.state, "limiter_script", None)
        if script is None:
            raise RuntimeError("Rate limiter script is not initialized.")

        # Resolve policy and generate key
        policy = self.policy_provider.get_policy(request)
        key = self.key_func(request, policy)
        unique_member = uuid.uuid4().hex

        try:
            # Execute sliding window evaluation atomically in Redis
            allowed, remaining, retry_after = await script(
                keys=[key],
                args=[
                    str(policy.window_seconds),
                    str(policy.requests),
                    unique_member,
                ],
                client=redis,
            )
        except RedisError as e:
            logger.exception(
                "Redis rate limit check failed for key '%s': %s. Skipping rate limiting.",
                key,
                e,
            )

            if self.fail_open:
                return

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiter unavailable. Please try again later.",
            )

        limit_headers = {
            "X-RateLimit-Limit": str(policy.requests),
            "X-RateLimit-Remaining": str(max(0, remaining)),
        }

        # Set headers in response flow
        for k, v in limit_headers.items():
            response.headers[k] = v

        if not allowed:
            limit_headers["Retry-After"] = str(retry_after)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers=limit_headers,
            )
