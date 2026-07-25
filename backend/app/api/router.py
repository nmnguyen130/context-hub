from fastapi import APIRouter, Depends

from app.infrastructure.rate_limiter import PlanPolicyProvider, RateLimiter
from app.modules.auth.router import auth_router
from app.modules.chat.router import chat_router
from app.modules.documents.router import documents_router, workspaces_router
from app.modules.tenant.router import tenant_router, tenants_router

rate_limiter = RateLimiter(policy_provider=PlanPolicyProvider())

api_router = APIRouter(dependencies=[Depends(rate_limiter)])
api_router.include_router(tenant_router)
api_router.include_router(tenants_router)
api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(workspaces_router)
api_router.include_router(chat_router)
