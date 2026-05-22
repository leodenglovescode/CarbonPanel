import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionInfo(BaseModel):
    user: str
    tty: str
    from_host: str
    login_time: str
    idle: str
    cpu_time: str
    command: str


async def _run(cmd: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode, stdout.decode(errors="replace")


@router.get("", response_model=list[SessionInfo])
async def list_sessions(_: User = Depends(get_current_user)):
    # `w -h` prints sessions without header: USER TTY FROM LOGIN@ IDLE JCPU PCPU WHAT
    rc, out = await _run(["w", "-h"])
    sessions: list[SessionInfo] = []
    if rc != 0:
        return sessions
    for line in out.splitlines():
        parts = line.split(None, 7)
        if len(parts) < 7:
            continue
        sessions.append(SessionInfo(
            user=parts[0],
            tty=parts[1],
            from_host=parts[2],
            login_time=parts[3],
            idle=parts[4],
            cpu_time=parts[5],
            command=parts[7] if len(parts) > 7 else parts[6],
        ))
    return sessions
