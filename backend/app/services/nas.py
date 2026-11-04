"""Read-only Linux MD, LVM and hwmon inventory, including unmounted storage."""
import asyncio
import json
import os
import re
import shutil
from pathlib import Path

BLOCK_ROOT = Path('/sys/class/block')
HWMON_ROOT = Path('/sys/class/hwmon')
LVM_HELPER = '/usr/local/libexec/carbonpanel-lvm'
LVM_FIELDS = {
    'pvs': ('pv', 'pv_name,vg_name,pv_size,pv_free,pv_attr'),
    'vgs': ('vg', 'vg_name,vg_size,vg_free,pv_count,lv_count,vg_attr'),
    'lvs': ('lv', 'lv_name,vg_name,lv_size,lv_attr,lv_path,pool_lv,'
                  'data_percent,metadata_percent,devices'),
}


def _read(path: Path, errors: list[str]) -> str | None:
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        errors.append(f'{path}: {exc.strerror}')
        return None


def _number(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def raid_inventory() -> dict:
    errors: list[str] = []
    arrays = []
    for md in sorted(BLOCK_ROOT.glob('*/md')):
        def read(name):
            return _read(md / name, errors)

        completed = read('sync_completed')
        progress = None
        if completed and re.fullmatch(r'\d+\s*/\s*\d+', completed):
            done, total = map(int, completed.split('/'))
            progress = round(min(100, done / total * 100), 2) if total else None
        members = []
        for member in sorted(md.glob('dev-*')):
            block = member / 'block'
            members.append({
                'device': '/dev/' + (block.resolve().name if block.exists() else member.name[4:]),
                'state': _read(member / 'state', errors),
                'slot': _read(member / 'slot', errors),
            })
        sectors = _number(_read(md.parent / 'size', errors))
        arrays.append({
            'device': '/dev/' + md.parent.name,
            'level': read('level'), 'state': read('array_state'),
            'raid_disks': _number(read('raid_disks')),
            'degraded': _number(read('degraded')),
            'size_bytes': sectors * 512 if sectors is not None else None,
            'sync_action': read('sync_action'), 'sync_percent': progress,
            'members': members,
        })
    return {'available': BLOCK_ROOT.is_dir(), 'arrays': arrays, 'errors': errors}


def fan_inventory() -> dict:
    errors: list[str] = []
    chips = []
    for chip in sorted(HWMON_ROOT.glob('hwmon*')):
        # Older drivers expose attributes in the device subdirectory.
        roots = [chip, chip / 'device']
        channels = []
        seen = set()
        for root in roots:
            for path in sorted(root.glob('*')):
                match = re.fullmatch(r'(fan(\d+)_input|pwm(\d+))', path.name)
                if not match or path.name in seen:
                    continue
                seen.add(path.name)
                value = _number(_read(path, errors))
                kind = 'fan' if match[2] else 'pwm'
                index = match[2] or match[3]
                channels.append({
                    'name': path.name, 'kind': kind,
                    'label': _read(root / f'{kind}{index}_label', errors) or f'{kind}{index}',
                    'value': value,
                    'enable': _number(_read(root / f'{kind}{index}_enable', errors)),
                    'fault': _number(_read(root / f'{kind}{index}_fault', errors)),
                })
        if channels:
            chips.append({'id': chip.name, 'name': _read(chip / 'name', errors) or chip.name,
                          'channels': channels})
    return {'available': HWMON_ROOT.is_dir(), 'chips': chips, 'errors': errors}


async def _lvm_report(command: str) -> tuple[list[dict], list[str]]:
    key, fields = LVM_FIELDS[command]
    if os.geteuid() != 0 and Path(LVM_HELPER).is_file():
        args = ['/usr/bin/sudo', '-n', LVM_HELPER, command]
    else:
        executable = shutil.which(command)
        if not executable:
            return [], [f'{command} is unavailable; install lvm2 for LVM monitoring.']
        args = [executable, '--reportformat', 'json', '--units', 'b', '--nosuffix', '-o', fields]
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env={**os.environ, 'LC_ALL': 'C'},
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            proc.kill()
            await proc.communicate()
            raise
        diagnostic = stderr.decode(errors='replace').strip()
        if proc.returncode:
            return [], [diagnostic or f'{command} exited with status {proc.returncode}']
        report = json.loads(stdout)
        rows = [row for section in report['report'] for row in section.get(key, [])]
        if not all(isinstance(row, dict) for row in rows):
            raise ValueError('invalid report rows')
        return [{k: str(v).strip() for k, v in row.items()} for row in rows], (
            [diagnostic] if diagnostic else []
        )
    except asyncio.TimeoutError:
        return [], [f'{command} timed out after 15 seconds']
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [], [f'{command}: {exc}']


async def inventory() -> dict:
    raid, fans, *reports = await asyncio.gather(
        asyncio.to_thread(raid_inventory), asyncio.to_thread(fan_inventory),
        *(_lvm_report(command) for command in LVM_FIELDS),
    )
    return {'raid': raid, 'fans': fans, 'lvm': {
        'physical_volumes': reports[0][0], 'volume_groups': reports[1][0],
        'logical_volumes': reports[2][0],
        'errors': [error for _, errors in reports for error in errors],
    }}
