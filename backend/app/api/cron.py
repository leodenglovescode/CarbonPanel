import asyncio
import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/cron", tags=["cron"])

_CRON_D_DIRS = ["/etc/cron.d", "/etc/cron.daily", "/etc/cron.hourly", "/etc/cron.weekly", "/etc/cron.monthly"]
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
        entries.append(CronEntry(source=source, user=user, schedule=schedule, command=command.strip(), raw=line))
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

    # System-wide crontab
    rc, out = await _run(["crontab", "-l"])
    if rc == 0 and out.strip():
        entries.extend(_parse_crontab(out, "crontab", "root"))

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
