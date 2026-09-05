"""v1 API aggregator: each feature owns its router; this file only mounts."""
from fastapi import APIRouter

from app.features.analysis.router import router as analysis_router
from app.features.ingestion.router import router as ingestion_router
from app.features.reports.router import router as reports_router
from app.features.whatsapp_bot.router import router as whatsapp_router

router = APIRouter()
router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
router.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])
router.include_router(reports_router, prefix="/reports", tags=["reports"])
router.include_router(whatsapp_router, prefix="/whatsapp", tags=["whatsapp"])
