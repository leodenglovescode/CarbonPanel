"""Exercise kernel-provided CPU identity/clocks without requiring ARM hardware."""
from types import SimpleNamespace

import pytest

from app.services.metrics import cpu_hardware as hardware


def write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else str(value).encode())
    return path


@pytest.fixture
def kernel(tmp_path, monkeypatch):
    monkeypatch.setattr(hardware, 'CPUINFO', tmp_path / 'cpuinfo')
    monkeypatch.setattr(hardware, 'CPU_ROOT', tmp_path / 'cpu')
    monkeypatch.setattr(hardware, 'DT_ROOTS', (tmp_path / 'dt', tmp_path / 'legacy-dt'))
    monkeypatch.setattr(hardware, 'SOC_ROOTS', (tmp_path / 'soc0',))
    monkeypatch.setattr(hardware.psutil, 'cpu_freq', lambda: None)
    monkeypatch.setattr(hardware.platform, 'machine', lambda: 'aarch64')
    hardware.cpu_name.cache_clear()
    yield tmp_path
    hardware.cpu_name.cache_clear()


@pytest.mark.parametrize('model', ['Intel(R) Core(TM) i5-8500 CPU @ 3.00GHz', 'AMD Ryzen 5 5600G'])
def test_x86_model_name_is_preserved(kernel, model):
    write(kernel, 'cpuinfo', f'model name : {model}\n')
    assert hardware.cpu_name() == model


def test_realtek_vendor_kernel_hardware_field(kernel):
    write(kernel, 'cpuinfo', 'model name : ARMv8 Processor rev 4 (v8l)\n'
          'Hardware : Realtek_RTD1296\nCPU implementer : 0x41\nCPU part : 0xd03\n')
    assert hardware.cpu_name() == 'Realtek RTD1296'


@pytest.mark.parametrize(('compatible', 'name'), [
    (b'nas-vendor,board\0realtek,rtd1296\0realtek,rtd1295\0', 'Realtek RTD1296'),
    (b'Realtek,rtd-1296\0', 'Realtek RTD1296'),
    (b'qcom,example-board\0qcom,sm8250\0', 'Qualcomm SM8250'),
    (b'rockchip,rk3588\0', 'Rockchip RK3588'),
    (b'mediatek,mt8195\0', 'MediaTek MT8195'),
])
def test_soc_compatible_is_used_instead_of_board_name(kernel, compatible, name):
    write(kernel, 'dt/compatible', compatible)
    write(kernel, 'dt/model', 'A development board\0')
    assert hardware.cpu_name() == name


def test_legacy_device_tree_path(kernel):
    write(kernel, 'legacy-dt/compatible', b'realtek,rtd1296\0')
    assert hardware.cpu_name() == 'Realtek RTD1296'


def test_soc_sysfs_model(kernel):
    write(kernel, 'soc0/family', 'Qualcomm')
    write(kernel, 'soc0/soc_id', 'SM8550')
    assert hardware.cpu_name() == 'Qualcomm SM8550'


def test_core_part_does_not_imply_soc(kernel):
    write(kernel, 'cpuinfo', 'CPU implementer : 0x41\nCPU part : 0xd03\n')
    assert hardware.cpu_name() == 'ARM Cortex-A53'


def test_mixed_arm_cores(kernel):
    write(kernel, 'cpuinfo', 'CPU implementer : 0x41\nCPU part : 0xd03\n\n'
          'CPU implementer : 0x41\nCPU part : 0xd08\n')
    assert hardware.cpu_name() == 'ARM Cortex-A53 / ARM Cortex-A72'


def test_missing_cpu_identity_reports_architecture(kernel):
    assert hardware.cpu_name() == 'aarch64 CPU (model not reported)'


def test_psutil_live_frequency(kernel, monkeypatch):
    monkeypatch.setattr(hardware.psutil, 'cpu_freq', lambda: SimpleNamespace(current=1234.5))
    result = hardware.cpu_frequency()
    assert result.mhz == 1234.5 and result.kind == 'current' and result.source == 'psutil'


@pytest.mark.parametrize('current', [0, -1, float('nan'), float('inf'), None])
def test_invalid_psutil_readings_fall_back_to_legacy_cpufreq(kernel, monkeypatch, current):
    monkeypatch.setattr(hardware.psutil, 'cpu_freq', lambda: SimpleNamespace(current=current))
    write(kernel, 'cpu/cpu0/cpufreq/scaling_cur_freq', 1400000)
    result = hardware.cpu_frequency()
    assert result.mhz == 1400 and result.kind == 'current'
    assert 'scaling_cur_freq' in result.source


def test_hardware_frequency_preferred_and_offline_cpu_ignored(kernel):
    write(kernel, 'cpu/cpu0/cpufreq/cpuinfo_cur_freq', 1200000)
    write(kernel, 'cpu/cpu0/cpufreq/scaling_cur_freq', 1400000)
    write(kernel, 'cpu/cpu1/cpufreq/scaling_cur_freq', 1600000)
    write(kernel, 'cpu/cpu2/cpufreq/scaling_cur_freq', 9000000)
    write(kernel, 'cpu/cpu2/online', 0)
    result = hardware.cpu_frequency()
    assert result.mhz == 1400 and result.kind == 'current'


def test_policy_frequency_weighted_by_cluster_size(kernel):
    write(kernel, 'cpu/cpufreq/policy0/scaling_cur_freq', 1400000)
    write(kernel, 'cpu/cpufreq/policy0/affected_cpus', '0 1 2 3')
    write(kernel, 'cpu/cpufreq/policy4/scaling_cur_freq', 1800000)
    write(kernel, 'cpu/cpufreq/policy4/affected_cpus', '4-5')
    assert hardware.cpu_frequency().mhz == pytest.approx((1400 * 4 + 1800 * 2) / 6)


def test_unreadable_hardware_frequency_uses_scaling_frequency(kernel, monkeypatch):
    write(kernel, 'cpu/cpu0/cpufreq/cpuinfo_cur_freq', 1200000)
    write(kernel, 'cpu/cpu0/cpufreq/scaling_cur_freq', 1400000)
    read_bytes = hardware.Path.read_bytes
    def protected_read(path):
        if path.name == 'cpuinfo_cur_freq':
            raise PermissionError('root only')
        return read_bytes(path)
    monkeypatch.setattr(hardware.Path, 'read_bytes', protected_read)
    assert hardware.cpu_frequency().mhz == 1400


@pytest.mark.parametrize('error', [OSError, NotImplementedError, RuntimeError])
def test_psutil_errors_do_not_abort_collection(kernel, monkeypatch, error):
    def unavailable():
        raise error('frequency unavailable')
    monkeypatch.setattr(hardware.psutil, 'cpu_freq', unavailable)
    write(kernel, 'cpu/cpu0/cpufreq/scaling_cur_freq', 1400000)
    assert hardware.cpu_frequency().mhz == 1400


def test_proc_cpu_mhz(kernel):
    write(kernel, 'cpuinfo', 'cpu MHz : 1300.0\n\ncpu MHz : 1500.0\n')
    assert hardware.cpu_frequency().mhz == 1400


def test_device_tree_clock_is_nominal_and_not_live(kernel):
    write(kernel, 'dt/cpus/cpu@0/clock-frequency', (1400000000).to_bytes(4, 'big'))
    # An unrelated memory clock must never influence the CPU display.
    write(kernel, 'dt/memory/clock-frequency', (999000000).to_bytes(4, 'big'))
    result = hardware.cpu_frequency()
    assert result.mhz == 1400 and result.kind == 'nominal'
    assert result.source == 'device-tree clock-frequency'


def test_missing_clocks_are_not_inferred_from_bogomips_or_max_frequency(kernel):
    write(kernel, 'cpuinfo', 'BogoMIPS : 2800.00\n')
    write(kernel, 'cpu/cpu0/cpufreq/cpuinfo_max_freq', 1400000)
    write(kernel, 'cpu/cpu0/cpufreq/scaling_max_freq', 1400000)
    result = hardware.cpu_frequency()
    assert result.mhz == 0 and result.kind == 'unavailable' and result.source is None


def test_metrics_snapshot_includes_arm_name_and_frequency(kernel, monkeypatch):
    import asyncio
    from app.services.metrics import cpu

    write(kernel, 'dt/compatible', b'realtek,rtd1296\0')
    write(kernel, 'cpu/cpu0/cpufreq/scaling_cur_freq', 1400000)
    monkeypatch.setattr(cpu.psutil, 'cpu_percent', lambda percpu: [10.0] * 4 if percpu else 10.0)
    monkeypatch.setattr(cpu.psutil, 'getloadavg', lambda: (0.1, 0.2, 0.3))
    monkeypatch.setattr(cpu, '_collect_temps', lambda: [])

    async def collect():
        loop = asyncio.get_running_loop()
        def run_in_executor(executor, callback):
            future = loop.create_future()
            future.set_result(callback())
            return future
        monkeypatch.setattr(loop, 'run_in_executor', run_in_executor)
        return await cpu.collect()

    result = asyncio.run(collect())
    assert result.cpu_name == 'Realtek RTD1296'
    assert len(result.per_core) == 4
    assert result.frequency_mhz == 1400
    assert result.frequency_kind == 'current'
    assert 'scaling_cur_freq' in result.frequency_source


def test_numeric_soc_id_does_not_hide_device_tree_model(kernel):
    write(kernel, 'soc0/family', 'Realtek')
    write(kernel, 'soc0/soc_id', '0x1296')
    write(kernel, 'dt/compatible', b'Realtek,rtd-1296\0')
    assert hardware.cpu_name() == 'Realtek RTD1296'


def test_vendor_tree_without_clock_does_not_fabricate_frequency(kernel):
    write(kernel, 'cpuinfo', 'CPU implementer : 0x41\nCPU part : 0xd03\n')
    write(kernel, 'dt/compatible', b'Realtek,rtd-1296\0')
    write(kernel, 'dt/model', b'Realtek_RTD1296\0')
    assert hardware.cpu_name() == 'Realtek RTD1296'
    assert hardware.cpu_frequency().kind == 'unavailable'
