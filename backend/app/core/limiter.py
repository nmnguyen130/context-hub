import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from redis.exceptions import RedisError

logger = logging.getLogger("app.limiter")

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

-- Get current time from Redis server
local time_res = redis.call('time')
local now = tonumber(time_res[1]) + tonumber(time_res[2]) / 1000000

-- Remove out-of-date elements
redis.call('zremrangebyscore', key, '-inf', now - window)

-- Count current elements
local current_requests = redis.call('zcard', key)

local allowed = 1
local remaining = limit - current_requests
local retry_after = 0

if current_requests < limit then
    redis.call('zadd', key, now, member)
    redis.call('expire', key, window)
    remaining = remaining - 1 -- Deduct the current successful request
else
    allowed = 0
    remaining = 0
    local oldest = redis.call('zrange', key, 0, 0, 'WITHSCORES')
    if oldest[2] then
        retry_after = math.ceil(tonumber(oldest[2]) + window - now)
    else
        retry_after = window
    end
    if retry_after <= 0 then
        retry_after = 1
    end
end

return {allowed, remaining, retry_after}
"""


@dataclass
class RateLimitPolicy:
    """Defines limits and identification prefix for rate limiting."""

    key_prefix: str
    requests: int
    window_seconds: int


class LimitPolicyProvider(ABC):
    """Abstract provider to dynamically determine rate limiting policy."""

    @abstractmethod
    def get_policy(self, request: Request) -> RateLimitPolicy:
        """Returns the rate limiting policy based on request context."""
        ...


class StaticPolicyProvider(LimitPolicyProvider):
    """Static limit configuration fallback."""

    def __init__(self, key_prefix: str, requests: int, window_seconds: int):
        self.key_prefix = key_prefix
        self.requests = requests
        self.window_seconds = window_seconds

    def get_policy(self, request: Request) -> RateLimitPolicy:
        return RateLimitPolicy(
            key_prefix=self.key_prefix,
            requests=self.requests,
            window_seconds=self.window_seconds,
        )


class SaaSPlanPolicyProvider(LimitPolicyProvider):
    """SaaS Policy Provider supporting dynamic limits per tier/plan."""

    def __init__(
        self,
        key_prefix: str = "default",
        default_requests: int = 60,
        default_window: int = 60,
    ):
        self.key_prefix = key_prefix
        self.default_requests = default_requests
        self.default_window = default_window

    def get_policy(self, request: Request) -> RateLimitPolicy:
        identity = getattr(request.state, "identity", None)

        # NOTE: Dynamic limits can be populated based on the resolved user's tier.
        requests = self.default_requests
        window = self.default_window

        if identity:
            tenant_tier = getattr(identity, "plan", "free").lower()
            if tenant_tier == "enterprise":
                requests = 2000
            elif tenant_tier == "pro":
                requests = 500

        return RateLimitPolicy(
            key_prefix=self.key_prefix,
            requests=requests,
            window_seconds=window,
        )


class RateLimiter:
    """Redis-based Sliding Window Rate Limiter dependency for FastAPI."""

    def __init__(
        self,
        requests: int | None = None,
        window_seconds: int | None = None,
        policy_provider: LimitPolicyProvider | None = None,
        key_func: Callable[[Request, RateLimitPolicy], str] | None = None,
    ):
        if policy_provider:
            self.policy_provider = policy_provider
        elif requests is not None and window_seconds is not None:
            self.policy_provider = StaticPolicyProvider(
                key_prefix="static",
                requests=requests,
                window_seconds=window_seconds,
            )
        else:
            raise ValueError(
                "Either policy_provider or both requests and window_seconds must be provided."
            )

        self.key_func = key_func or self._default_key_generator

    def _default_key_generator(self, request: Request, policy: RateLimitPolicy) -> str:
        """Generates a structured rate limit key based on identity priority.

        Priority order:
          1. API Key: `rate_limit:apikey:{key_hash}:{policy_prefix}:{route_path}`
          2. User & Tenant: `rate_limit:tenant:{tenant_id}:user:{user_id}:{policy_prefix}:{route_path}`
          3. Tenant only: `rate_limit:tenant:{tenant_id}:{policy_prefix}:{route_path}`
          4. IP (Anonymous): `rate_limit:ip:{client_ip}:{policy_prefix}:{route_path}`
        """
        identity = getattr(request.state, "identity", None)

        if api_key := request.headers.get("x-api-key"):
            target = f"apikey:{hash(api_key)}"
        elif identity and getattr(identity, "user_id", None):
            target = f"tenant:{identity.tenant_id}:user:{identity.user_id}"
        elif identity and getattr(identity, "tenant_id", None):
            target = f"tenant:{identity.tenant_id}"
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"
            target = f"ip:{client_ip}"

        route = request.scope.get("route")
        route_path = route.path if route else request.scope.get("path", "")
        return f"rate_limit:{target}:{policy.key_prefix}:{route_path}"

    async def __call__(self, request: Request, response: Response) -> None:
        redis = getattr(request.app.state, "redis", None)
        if not redis:
            logger.warning(
                "Redis client not initialized in app.state. Skipping rate limiting."
            )
            return

        # Retrieve the pre-registered Lua script from FastAPI app state
        script = getattr(request.app.state, "limiter_script", None)
        if not script:
            raise RuntimeError(
                "Redis Rate Limiter script has not been preloaded at startup."
            )

        # Resolve policy and generate key
        policy = self.policy_provider.get_policy(request)
        key = self.key_func(request, policy)
        unique_member = str(uuid.uuid4())

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
            logger.error(
                f"Redis rate limit check failed for key '{key}': {e}. Skipping rate limiting.",
                exc_info=True,
            )
            return

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
