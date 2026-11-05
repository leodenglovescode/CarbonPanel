"""Read CPU identity and clocks without assuming an x86 /proc/cpuinfo layout."""
import math
import platform
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import psutil

CPUINFO = Path('/proc/cpuinfo')
CPU_ROOT = Path('/sys/devices/system/cpu')
DT_ROOTS = (Path('/sys/firmware/devicetree/base'), Path('/proc/device-tree'))
SOC_ROOTS = (Path('/sys/devices/soc0'), Path('/sys/devices/system/soc/soc0'))

# CPU part IDs identify cores, not the SoC containing them.
_ARM_CORES = {
    0xD03: 'Cortex-A53', 0xD05: 'Cortex-A55', 0xD07: 'Cortex-A57',
    0xD08: 'Cortex-A72', 0xD09: 'Cortex-A73', 0xD0A: 'Cortex-A75',
    0xD0B: 'Cortex-A76', 0xD0C: 'Neoverse-N1', 0xD0D: 'Cortex-A77',
    0xD41: 'Cortex-A78',
}
_SOC_COMPATIBLES = {
    'realtek': ('Realtek', r'rtd\d+[a-z0-9]*'),
    'qcom': ('Qualcomm', r'(?:sm|sc|msm|apq|qcs|sdm|ipq|sa|x1e|x1p)\d+[a-z0-9]*'),
    'rockchip': ('Rockchip', r'rk\d+[a-z0-9]*'),
    'amlogic': ('Amlogic', r'(?:meson-[a-z0-9-]+|a\d+|s\d+[a-z0-9]*)'),
    'allwinner': ('Allwinner', r'sun\d+[a-z0-9-]*'),
    'mediatek': ('MediaTek', r'mt\d+[a-z0-9]*'),
    'brcm': ('Broadcom', r'bcm\d+[a-z0-9]*'),
    'nvidia': ('NVIDIA', r'tegra\d+[a-z0-9]*'),
    'samsung': ('Samsung', r'exynos\d+[a-z0-9]*'),
    'apple': ('Apple', r't\d+'),
}


def _text(path: Path) -> str:
    try:
        return path.read_bytes().decode(errors='replace').strip('\0 \t\r\n')
    except OSError:
        return ''


def _cpuinfo() -> list[dict[str, str]]:
    blocks = []
    for block in re.split(r'\n\s*\n', _text(CPUINFO)):
        fields = {}
        for line in block.splitlines():
            key, sep, value = line.partition(':')
            if sep:
                fields[key.strip().lower()] = value.strip()
        if fields:
            blocks.append(fields)
    return blocks


def _usable_name(value: str) -> bool:
    return bool(value) and value.lower() not in {
        'unknown', 'unknown cpu', 'generic', 'generic dt based system',
    }


@lru_cache(maxsize=1)
def cpu_name() -> str:
    blocks = _cpuinfo()
    models = list(dict.fromkeys(
        b['model name'] for b in blocks if _usable_name(b.get('model name', ''))
    ))
    # Keep the existing x86 path; ARM core descriptions can be improved by a SoC ID.
    if models and not re.search(r'arm|aarch64|cortex|neoverse', models[0], re.I):
        return ' / '.join(models)

    soc_fallback = ''
    for root in SOC_ROOTS:
        family, soc_id = _text(root / 'family'), _text(root / 'soc_id')
        if (_usable_name(soc_id) and re.search(r'[a-z]', soc_id, re.I)
                and not re.fullmatch(r'0x[0-9a-f]+', soc_id, re.I)):
            if family and family.lower() not in soc_id.lower():
                return f'{family} {soc_id}'
            return soc_id
        if family:
            soc_fallback = f'{family} (SoC ID {soc_id})' if soc_id else family

    hardware = next((b['hardware'] for b in blocks if _usable_name(b.get('hardware', ''))), '')
    # Vendor kernels often expose the Realtek model only in Hardware.
    realtek = re.search(r'(?<![a-z0-9])rtd[ _-]?(\d+[a-z0-9]*)\b', hardware, re.I)
    if realtek:
        return f'Realtek RTD{realtek[1].upper()}'

    board_model = ''
    for root in DT_ROOTS:
        for compatible in _text(root / 'compatible').split('\0'):
            vendor, sep, chip = compatible.partition(',')
            vendor, chip = vendor.lower(), chip.lower()
            # Older Realtek trees use "Realtek,rtd-1296" rather than the
            # upstream spelling "realtek,rtd1296".
            if vendor == 'realtek':
                chip = re.sub(r'^rtd-', 'rtd', chip)
            if sep and vendor in _SOC_COMPATIBLES:
                brand, pattern = _SOC_COMPATIBLES[vendor]
                if re.fullmatch(pattern, chip, re.I):
                    return f'{brand} {chip.upper()}'
        board_model = board_model or _text(root / 'model')
    if hardware:
        return hardware
    if soc_fallback:
        return soc_fallback

    cores = []
    for block in blocks:
        try:
            implementer = int(block.get('cpu implementer', ''), 0)
            part = int(block.get('cpu part', ''), 0)
        except ValueError:
            continue
        if implementer == 0x41:
            name = 'ARM ' + _ARM_CORES.get(part, f'CPU (part 0x{part:x})')
        else:
            vendor = 'Qualcomm' if implementer == 0x51 else f'implementer 0x{implementer:x}'
            name = f'ARM CPU ({vendor}, part 0x{part:x})'
        if name not in cores:
            cores.append(name)
    if cores:
        return ' / '.join(cores)
    if models:
        return ' / '.join(models)
    if board_model:
        return board_model
    return f'{platform.machine() or "Unknown architecture"} CPU (model not reported)'


@dataclass(frozen=True)
class CpuFrequency:
    # Retain the numeric wire format used by existing clients; zero means unavailable.
    mhz: float = 0.0
    source: str | None = None
    kind: Literal['current', 'nominal', 'unavailable'] = 'unavailable'


def _positive(value) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def _policy_weight(root: Path) -> int:
    # A policy can cover one core or a whole cluster. Weight the cluster average
    # by affected CPUs rather than treating a two-core and four-core cluster alike.
    cpus = _text(root / 'affected_cpus') or _text(root / 'related_cpus')
    count = 0
    for token in re.split(r'[,\s]+', cpus):
        if token.isdigit():
            count += 1
        elif re.fullmatch(r'\d+-\d+', token):
            first, last = map(int, token.split('-'))
            count += max(0, last - first + 1)
    return count or 1


def _sysfs_frequency(roots: list[Path], *, policies: bool = False) -> CpuFrequency | None:
    readings = []
    sources = set()
    total_weight = 0
    for root in roots:
        for attribute in ('cpuinfo_cur_freq', 'scaling_cur_freq'):
            khz = _positive(_text(root / attribute))
            if khz is not None:
                weight = _policy_weight(root) if policies else 1
                readings.append(khz / 1000 * weight)
                total_weight += weight
                sources.add(attribute)
                break
    if readings:
        return CpuFrequency(sum(readings) / total_weight, 'cpufreq: ' + ', '.join(sorted(sources)),
                            'current')
    return None


def cpu_frequency() -> CpuFrequency:
    try:
        freq = psutil.cpu_freq()
        mhz = _positive(freq.current) if freq else None
        if mhz is not None:
            return CpuFrequency(mhz, 'psutil', 'current')
    except (AttributeError, OSError, NotImplementedError, RuntimeError, ValueError):
        pass

    # Legacy kernels use per-CPU paths; modern kernels also expose policy paths.
    per_cpu = [p / 'cpufreq' for p in sorted(CPU_ROOT.glob('cpu[0-9]*'))
               if _text(p / 'online') != '0']
    reading = _sysfs_frequency(per_cpu)
    if reading:
        return reading
    reading = _sysfs_frequency(sorted((CPU_ROOT / 'cpufreq').glob('policy[0-9]*')),
                              policies=True)
    if reading:
        return reading

    reported = []
    for block in _cpuinfo():
        mhz = _positive(block.get('cpu mhz'))
        if mhz is None:
            clock = re.fullmatch(r'([\d.]+)\s*([MG])Hz', block.get('clock', ''), re.I)
            if clock:
                mhz = _positive(clock[1])
                if mhz is not None and clock[2].lower() == 'g':
                    mhz *= 1000
        if mhz is not None:
            reported.append(mhz)
    if reported:
        return CpuFrequency(sum(reported) / len(reported), '/proc/cpuinfo', 'current')

    # clock-frequency is a configured/boot clock, never evidence of a live speed.
    # Limit this fallback to CPU nodes so bus and memory clocks cannot be used.
    for root in DT_ROOTS:
        clocks = []
        for path in sorted((root / 'cpus').glob('cpu@*/clock-frequency')):
            if _text(path.parent / 'status') == 'disabled':
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if len(raw) in (4, 8):
                hz = int.from_bytes(raw, 'big')
                if hz > 0:
                    clocks.append(hz / 1_000_000)
        if clocks:
            return CpuFrequency(sum(clocks) / len(clocks), 'device-tree clock-frequency', 'nominal')
    return CpuFrequency()
