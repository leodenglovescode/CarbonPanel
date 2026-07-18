import asyncio
import getpass
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services import cron_service
from app.services.cron_service import CronJob

router = APIRouter(prefix="/cron", tags=["cron"])

_CRON_D_DIRS = [
    "/etc/cron.d", "/etc/cron.daily", "/etc/cron.hourly",
    "/etc/cron.weekly", "/etc/cron.monthly",
]
_SKIP_LINE = re.compile(r"^\s*(#|$|SHELL|PATH|MAILTO|HOME|LOGNAME|CRON_TZ)")
_ENTRY = re.compile(
    r"^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$"
)


class CronEntry(BaseModel):
    source: str
    user: str
    schedule: str
    command: str
    raw: str


def _parse_crontab(text: str, source: str, default_user: str) -> list[CronEntry]:
    entries: list[CronEntry] = []
    for line in text.splitlines():
        line = line.strip()
        if _SKIP_LINE.match(line):
            continue
        m = _ENTRY.match(line)
        if not m:
            continue
        min_, hour, dom, month, dow, user_or_cmd, rest = m.groups()
        schedule = f"{min_} {hour} {dom} {month} {dow}"
        # /etc/cron.d files have user field; crontab -l does not
        if source.startswith("/etc/cron"):
            user = user_or_cmd
            command = rest
        else:
            user = default_user
            command = f"{user_or_cmd} {rest}"
        entries.append(CronEntry(
            source=source, user=user, schedule=schedule,
            command=command.strip(), raw=line,
        ))
    return entries


async def _run(cmd: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode, stdout.decode(errors="replace")


@router.get("", response_model=list[CronEntry])
async def list_cron_jobs(_: User = Depends(get_current_user)):
    entries: list[CronEntry] = []

    # This process's own crontab — never actually root's (the backend runs
    # as the unprivileged carbonpanel service account), so label it with the
    # real current user instead of the previous hardcoded "root". Jobs
    # created via the panel are stripped out here since they get their own
    # dedicated, better-labeled section below.
    rc, out = await _run(["crontab", "-l"])
    if rc == 0 and out.strip():
        current_user = getpass.getuser()
        stripped = cron_service.strip_managed_blocks(out)
        entries.extend(_parse_crontab(stripped, "crontab", current_user))

    # /etc/crontab
    try:
        text = Path("/etc/crontab").read_text(errors="replace")
        entries.extend(_parse_crontab(text, "/etc/crontab", "root"))
    except OSError:
        pass

    # /etc/cron.d/* and periodic dirs
    for d in _CRON_D_DIRS:
        p = Path(d)
        if not p.is_dir():
            continue
        for f in sorted(p.iterdir()):
            if f.is_file() and not f.name.startswith("."):
                try:
                    text = f.read_text(errors="replace")
                    entries.extend(_parse_crontab(text, str(f), "root"))
                except OSError:
                    pass

    return entries


class CronJobIn(BaseModel):
    label: str = ""
    schedule: str
    command: str


@router.get("/managed", response_model=list[CronJob])
async def list_managed_jobs(_: User = Depends(get_current_user)):
    return await cron_service.list_managed_jobs()


@router.post("/managed", response_model=CronJob)
async def create_managed_job(body: CronJobIn, _: User = Depends(get_current_user)):
    try:
        return await cron_service.create_job(body.label, body.schedule, body.command)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.put("/managed/{job_id}", response_model=CronJob)
async def update_managed_job(job_id: str, body: CronJobIn, _: User = Depends(get_current_user)):
    try:
        result = await cron_service.update_job(job_id, body.label, body.schedule, body.command)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    if result is None:
        raise HTTPException(404, "Job not found")
    return result


@router.delete("/managed/{job_id}")
async def delete_managed_job(job_id: str, _: User = Depends(get_current_user)):
    try:
        removed = await cron_service.delete_job(job_id)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    if not removed:
        raise HTTPException(404, "Job not found")
    return {"ok": True}
