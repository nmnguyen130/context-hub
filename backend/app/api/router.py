from fastapi import APIRouter

from app.modules.auth.router import auth_router, user_router
from app.modules.chat.router import router as chat_router
from app.modules.documents.router import router as documents_router
from app.modules.tenant.router import tenant_router, tenants_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(tenant_router)
api_router.include_router(tenants_router)
api_router.include_router(chat_router)
api_router.include_router(documents_router)
