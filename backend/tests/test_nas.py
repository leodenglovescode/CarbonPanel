import asyncio
import json
from types import SimpleNamespace

from app.services import nas
from app.services.metrics import disk


def write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(value))


def test_md_degraded_rebuild_and_members(tmp_path, monkeypatch):
    monkeypatch.setattr(nas, 'BLOCK_ROOT', tmp_path)
    for name, value in {
        'md0/size': 2000, 'md0/md/level': 'raid1',
        'md0/md/array_state': 'active', 'md0/md/raid_disks': 2,
        'md0/md/degraded': 1, 'md0/md/sync_action': 'recover',
        'md0/md/sync_completed': '250 / 1000',
        'md0/md/dev-sda1/state': 'in_sync', 'md0/md/dev-sda1/slot': 0,
    }.items():
        write(tmp_path, name, value)
    array, = nas.raid_inventory()['arrays']
    assert array['size_bytes'] == 1024000
    assert array['degraded'] == 1
    assert array['sync_percent'] == 25
    assert array['members'] == [{'device': '/dev/sda1', 'state': 'in_sync', 'slot': '0'}]
    write(tmp_path, 'md0/md/sync_completed', 'none')
    assert nas.raid_inventory()['arrays'][0]['sync_percent'] is None


def test_hwmon_independent_pwm_and_legacy_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(nas, 'HWMON_ROOT', tmp_path)
    for name, value in {
        'hwmon0/name': 'nas-fan', 'hwmon0/fan1_input': 0,
        'hwmon0/fan1_fault': 1, 'hwmon0/fan1_label': 'Chassis',
        'hwmon0/device/pwm2': 128, 'hwmon0/device/pwm2_enable': 2,
    }.items():
        write(tmp_path, name, value)
    chip, = nas.fan_inventory()['chips']
    fan, pwm = chip['channels']
    assert fan['value'] == 0 and fan['fault'] == 1 and fan['label'] == 'Chassis'
    assert pwm['value'] == 128 and pwm['enable'] == 2
    assert chip['name'] == 'nas-fan'


def test_lvm_report_and_diagnostics(monkeypatch):
    monkeypatch.setattr(nas.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(nas.shutil, 'which', lambda name: '/sbin/' + name)
    captured = []

    async def spawn(*args, **kwargs):
        captured.append(args)
        async def communicate():
            return json.dumps({'report': [{'lv': [{'lv_name': ' data ', 'lv_size': '1024'}]}]}).encode(), b'warning'
        return SimpleNamespace(returncode=0, communicate=communicate)

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    rows, errors = asyncio.run(nas._lvm_report('lvs'))
    assert rows == [{'lv_name': 'data', 'lv_size': '1024'}]
    assert errors == ['warning']
    assert '--reportformat' in captured[0]


def test_lvm_timeout_reaps_child(monkeypatch):
    monkeypatch.setattr(nas.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(nas.shutil, 'which', lambda name: name)
    killed = []
    async def communicate():
        return b'', b''
    async def spawn(*args, **kwargs):
        return SimpleNamespace(communicate=communicate, kill=lambda: killed.append(True))
    async def timeout(coro, **kwargs):
        coro.close()
        raise asyncio.TimeoutError
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    monkeypatch.setattr(asyncio, 'wait_for', timeout)
    rows, errors = asyncio.run(nas._lvm_report('pvs'))
    assert not rows and 'timed out' in errors[0]
    assert killed == [True]


def test_mapper_io_and_duplicate_mount_rates(monkeypatch):
    monkeypatch.setattr(disk, '_prev_counters', {'dm-1': SimpleNamespace(read_bytes=0, write_bytes=0)})
    monkeypatch.setattr(disk, '_prev_time', 10)
    monkeypatch.setattr(disk, 'time', SimpleNamespace(monotonic=lambda: 12))
    monkeypatch.setattr(disk, 'os', SimpleNamespace(path=SimpleNamespace(
        realpath=lambda _: '/dev/dm-1', basename=lambda _: 'dm-1',
    )))
    monkeypatch.setattr(disk.psutil, 'disk_partitions', lambda **_: [
        SimpleNamespace(device='/dev/mapper/vg-data', mountpoint=mp) for mp in ['/data', '/bind']
    ])
    monkeypatch.setattr(disk.psutil, 'disk_usage', lambda _: SimpleNamespace(total=100, used=20, percent=20))
    monkeypatch.setattr(disk.psutil, 'disk_io_counters', lambda **_: {
        'dm-10': SimpleNamespace(read_bytes=90000000, write_bytes=0),
        'dm-1': SimpleNamespace(read_bytes=4 * 1024**2, write_bytes=0),
    })
    async def collect_without_threads():
        loop = asyncio.get_running_loop()
        def run_in_executor(executor, callback):
            future = loop.create_future()
            future.set_result(callback())
            return future
        monkeypatch.setattr(loop, 'run_in_executor', run_in_executor)
        return await disk.collect()
    readings = asyncio.run(collect_without_threads())
    assert [reading.read_mb_s for reading in readings] == [2, 2]
