from __future__ import annotations

import asyncio
import re
import uuid
from urllib.parse import quote, unquote

from pydantic import BaseModel

# Jobs created through the panel are written into the CarbonPanel service
# account's own crontab (no root/sudo needed — every user can manage their
# own crontab) and tagged with a comment line carrying an id + label, so
# they can be listed/edited/deleted without a separate DB table. The
# crontab itself stays the single source of truth — nothing to drift out
# of sync with a manually-edited crontab the way a DB mirror could.
_JOB_TAG = re.compile(r"^#\s*carbonpanel-job\s+id=(\S+)\s+label=(.*)$")
_JOB_TAG_PREFIX = re.compile(r"^#\s*carbonpanel-job\s+id=")
_SCHEDULE_ENTRY = re.compile(r"^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$")

_FIELD_BOUNDS = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
_FIELD_TOKEN = re.compile(r"^(\*|\d+)(?:-(\d+))?(?:/(\d+))?$")


class CronJob(BaseModel):
    id: str
    label: str
    schedule: str
    command: str


def validate_schedule(schedule: str) -> None:
    parts = schedule.strip().split()
    if len(parts) != 5:
        raise ValueError(
            "Schedule must have exactly 5 fields (minute hour day-of-month month day-of-week)."
        )
    for part, (lo, hi) in zip(parts, _FIELD_BOUNDS):
        for token in part.split(","):
            if not _validate_field_token(token, lo, hi):
                raise ValueError(f"Invalid schedule field: {token!r}")


def _validate_field_token(token: str, lo: int, hi: int) -> bool:
    m = _FIELD_TOKEN.match(token)
    if not m:
        return False
    base, range_end, step = m.groups()
    if base != "*" and not (lo <= int(base) <= hi):
        return False
    if range_end is not None and not (lo <= int(range_end) <= hi):
        return False
    if step is not None and int(step) <= 0:
        return False
    return True


def _clean_single_line(value: str, max_len: int) -> str:
    # Reject rather than silently collapse newlines in the *command* — an
    # embedded newline there would break out of the entry's own line and
    # inject an extra, unreviewed cron line when written back. Labels are
    # cosmetic only, so those are just flattened instead of rejected.
    return " ".join(value.split())[:max_len]


async def _read_raw_crontab() -> str:
    proc = await asyncio.create_subprocess_exec(
        "crontab", "-l",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        return ""  # no crontab for this user yet — not an error
    return stdout.decode(errors="replace")


async def _write_raw_crontab(text: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "crontab", "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate(input=text.encode())
    if proc.returncode != 0:
        raise RuntimeError(
            f"Failed to update crontab: {stderr.decode(errors='replace').strip()}"
        )


def strip_managed_blocks(text: str) -> str:
    """Remove carbonpanel-tagged blocks — used so the general read-only cron
    listing doesn't show panel-managed jobs a second time, mislabeled."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if _JOB_TAG_PREFIX.match(lines[i].strip()):
            i += 2  # skip the tag comment and its entry line
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _parse_managed_jobs(text: str) -> list[CronJob]:
    lines = text.splitlines()
    jobs: list[CronJob] = []
    i = 0
    while i < len(lines):
        m = _JOB_TAG.match(lines[i].strip())
        if m and i + 1 < len(lines):
            job_id, label_enc = m.groups()
            entry_m = _SCHEDULE_ENTRY.match(lines[i + 1].strip())
            if entry_m:
                min_, hour, dom, month, dow, command = entry_m.groups()
                jobs.append(CronJob(
                    id=job_id,
                    label=unquote(label_enc),
                    schedule=f"{min_} {hour} {dom} {month} {dow}",
                    command=command.strip(),
                ))
            i += 2
            continue
        i += 1
    return jobs


async def list_managed_jobs() -> list[CronJob]:
    return _parse_managed_jobs(await _read_raw_crontab())


def _prepare(label: str, schedule: str, command: str) -> tuple[str, str, str]:
    validate_schedule(schedule)
    command = command.strip()
    if not command:
        raise ValueError("Command cannot be empty.")
    if "\n" in command or "\r" in command:
        raise ValueError("Command cannot contain newlines.")
    label = _clean_single_line(label or command, 200)
    return label, schedule.strip(), command


async def create_job(label: str, schedule: str, command: str) -> CronJob:
    label, schedule, command = _prepare(label, schedule, command)
    job_id = uuid.uuid4().hex[:12]

    text = await _read_raw_crontab()
    block = f"# carbonpanel-job id={job_id} label={quote(label)}\n{schedule} {command}\n"
    updated = text.rstrip("\n")
    updated = (updated + "\n\n" + block) if updated else block
    await _write_raw_crontab(updated)
    return CronJob(id=job_id, label=label, schedule=schedule, command=command)


async def update_job(job_id: str, label: str, schedule: str, command: str) -> CronJob | None:
    label, schedule, command = _prepare(label, schedule, command)

    lines = (await _read_raw_crontab()).splitlines()
    out: list[str] = []
    i = 0
    found = False
    while i < len(lines):
        m = _JOB_TAG.match(lines[i].strip())
        if m and m.group(1) == job_id:
            found = True
            out.append(f"# carbonpanel-job id={job_id} label={quote(label)}")
            out.append(f"{schedule} {command}")
            i += 2
            continue
        out.append(lines[i])
        i += 1

    if not found:
        return None
    await _write_raw_crontab("\n".join(out) + "\n")
    return CronJob(id=job_id, label=label, schedule=schedule, command=command)


async def delete_job(job_id: str) -> bool:
    lines = (await _read_raw_crontab()).splitlines()
    out: list[str] = []
    i = 0
    removed = False
    while i < len(lines):
        m = _JOB_TAG.match(lines[i].strip())
        if m and m.group(1) == job_id:
            removed = True
            i += 2
            continue
        out.append(lines[i])
        i += 1

    if removed:
        await _write_raw_crontab(("\n".join(out) + "\n") if out else "")
    return removed
