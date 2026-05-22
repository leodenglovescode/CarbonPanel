from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.metrics import HistoryPoint
from app.services.metrics.collector import metrics_collector

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/history", response_model=list[HistoryPoint])
async def get_history(_: User = Depends(get_current_user)):
    return list(metrics_collector.history)
