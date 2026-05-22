import signal

import psutil
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/processes", tags=["processes"])


class KillRequest(BaseModel):
    force: bool = False


class KillResponse(BaseModel):
    success: bool
    message: str = ""


@router.post("/{pid}/kill", response_model=KillResponse)
async def kill_process(
    pid: int,
    body: KillRequest,
    _: User = Depends(get_current_user),
):
    if pid <= 1:
        raise HTTPException(400, "Cannot kill system process")
    try:
        proc = psutil.Process(pid)
        sig = signal.SIGKILL if body.force else signal.SIGTERM
        proc.send_signal(sig)
        return KillResponse(success=True, message=f"Signal sent to PID {pid}")
    except psutil.NoSuchProcess:
        raise HTTPException(404, "Process not found")
    except psutil.AccessDenied:
        raise HTTPException(403, "Permission denied")
