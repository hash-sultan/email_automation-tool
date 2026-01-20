"""
XenFlow Mailer - API Routes
"""

from fastapi import APIRouter

from app.api.leads import router as leads_router
from app.api.campaigns import router as campaigns_router
from app.api.templates import router as templates_router
from app.api.senders import router as senders_router
from app.api.analytics import router as analytics_router

api_router = APIRouter()

api_router.include_router(leads_router, prefix="/leads", tags=["Leads"])
api_router.include_router(campaigns_router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(templates_router, prefix="/templates", tags=["Templates"])
api_router.include_router(senders_router, prefix="/senders", tags=["Senders"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])

