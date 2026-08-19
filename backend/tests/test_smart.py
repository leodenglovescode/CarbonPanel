import pytest

from app.services.smart import _parse_json, _smartctl_args


def _attr(attr_id: int, raw: int | str, value: int = 100) -> dict:
    return {"id": attr_id, "value": value, "raw": {"value": raw}}


def test_hdd_smart_exposes_bad_sector_and_lifetime_details():
    result = _parse_json(
        {
            "device": {"protocol": "ATA"},
            "model_name": "Example HDD",
            "serial_number": "HDD123",
            "firmware_version": "1.0",
            "rotation_rate": 7200,
            "user_capacity": {"bytes": 2_000_000_000_000},
            "smart_status": {"passed": True},
            "temperature": {"current": 39},
            "ata_smart_attributes": {
                "table": [
                    _attr(4, 500),
                    _attr(5, "1 sector"),
                    _attr(9, 25_000),
                    _attr(12, 80),
                    _attr(187, 0),
                    _attr(188, 2),
                    _attr(193, 70_000),
                    _attr(197, 2),
                    _attr(198, 0),
                    _attr(199, 4),
                ]
            },
        },
        "/dev/sda",
    )

    assert result.drive_type == "hdd"
    assert result.capacity_bytes == 2_000_000_000_000
    assert result.reallocated_sectors == 1
    assert result.pending_sectors == 2
    assert result.uncorrectable_errors == 0
    assert result.power_on_hours == 25_000
    assert result.power_cycle_count == 80
    assert result.start_stop_count == 500
    assert result.load_cycle_count == 70_000
    assert result.command_timeouts == 2
    assert result.crc_errors == 4
    assert result.health_percentage == 82.2
    assert result.health_assessment == "Attention"
    assert any("pending reallocation" in note for note in result.health_notes or [])



def test_hdd_with_sixteen_reallocated_sectors_is_attention_not_near_failure():
    result = _parse_json(
        {
            "device": {"protocol": "ATA"},
            "model_name": "Example HDD",
            "rotation_rate": 7200,
            "smart_status": {"passed": True},
            "temperature": {"current": 40},
            "ata_smart_attributes": {
                "table": [
                    _attr(5, 16),
                    _attr(197, 0),
                    _attr(198, 0),
                ]
            },
        },
        "/dev/sda",
    )

    assert result.health_percentage == 88.8
    assert result.health_assessment == "Attention"


def test_hdd_sector_counters_use_strongest_signal_plus_corroboration():
    result = _parse_json(
        {
            "device": {"protocol": "ATA"},
            "model_name": "Example HDD",
            "rotation_rate": 7200,
            "smart_status": {"passed": True},
            "temperature": {"current": 40},
            "ata_smart_attributes": {
                "table": [
                    _attr(5, 16),
                    _attr(187, 16),
                    _attr(197, 16),
                    _attr(198, 16),
                ]
            },
        },
        "/dev/sda",
    )

    assert result.health_percentage == 67.7
    assert result.health_assessment == "Attention"


def _hdd_with_uncorrectable(count: int, *, temperature: int = 40) -> dict:
    return {
        "device": {"protocol": "ATA"},
        "model_name": "Example HDD",
        "rotation_rate": 7200,
        "smart_status": {"passed": True},
        "temperature": {"current": temperature},
        "ata_smart_attributes": {
            "table": [
                _attr(5, 0),
                _attr(197, 0),
                _attr(198, count),
            ]
        },
    }


def test_hdd_sixty_nine_uncorrectable_sectors_is_attention_not_critical():
    result = _parse_json(_hdd_with_uncorrectable(69), "/dev/sda")

    assert result.health_percentage == 71.6
    assert result.health_assessment == "Attention"
    assert "not the percentage of readable sectors" in result.health_basis


def test_hdd_three_hundred_static_uncorrectable_sectors_stays_operational_attention():
    previous = _parse_json(_hdd_with_uncorrectable(300), "/dev/sda")
    result = _parse_json(
        _hdd_with_uncorrectable(300),
        "/dev/sda",
        previous=previous,
    )

    assert result.health_percentage == 65.3
    assert result.health_assessment == "Attention"
    assert not any("Trend deduction" in note for note in result.health_notes or [])


def test_hdd_growing_uncorrectable_count_adds_bounded_trend_warning():
    previous = _parse_json(_hdd_with_uncorrectable(69), "/dev/sda")
    result = _parse_json(
        _hdd_with_uncorrectable(300),
        "/dev/sda",
        previous=previous,
    )

    assert result.health_percentage == 40.3
    assert result.health_assessment == "Warning"
    assert any("Trend deduction: 25 points" in note for note in result.health_notes or [])


def test_kingston_nvme_health_uses_tbw_when_reported_wear_rounds_to_zero():
    result = _parse_json(
        {
            "device": {"protocol": "NVMe"},
            "model_name": "KINGSTON SNV2S4000G",
            "smart_status": {"passed": True},
            "temperature": {"current": 50},
            "smartctl": {
                "messages": [
                    {
                        "severity": "error",
                        "string": "Read Self-test Log failed: Invalid Field in Command",
                    }
                ]
            },
            "nvme_smart_health_information_log": {
                "critical_warning": 0,
                "temperature": 50,
                "temperature_sensors": [50, 69],
                "percentage_used": 0,
                "available_spare": 100,
                "available_spare_threshold": 10,
                "data_units_read": 1_000_000,
                "data_units_written": 57_988_281,
                "unsafe_shutdowns": 20,
                "media_errors": 0,
                "num_err_log_entries": 987_654,
            },
        },
        "/dev/nvme0n1",
    )

    assert result.rated_endurance_tbw == 1280
    assert result.lifetime_written_tb == pytest.approx(29.69, abs=0.001)
    assert result.tbw_used_percent == pytest.approx(2.3195, abs=0.0001)
    assert result.effective_wear_percent == pytest.approx(2.3195, abs=0.0001)
    assert result.health_percentage == 97.7
    assert result.health_assessment == "Excellent"
    assert result.critical_warning == 0
    assert result.temperature_c == 50
    assert result.temperature_sensors_c == [50, 69]
    assert result.highest_temperature_c == 69
    assert result.reallocated_sectors is None
    assert result.pending_sectors is None
    assert result.uncorrectable_errors is None
    assert "command/protocol error" in (result.error_log_context or "")
    assert "not treated as media failures" in " ".join(result.health_notes or [])


def test_nvme_health_uses_maximum_of_tbw_and_reported_wear():
    result = _parse_json(
        {
            "device": {"protocol": "NVMe"},
            "model_name": "KINGSTON SNV2S4000G",
            "smart_status": {"passed": True},
            "nvme_smart_health_information_log": {
                "critical_warning": 0,
                "percentage_used": 8,
                "data_units_written": 57_988_281,
                "media_errors": 0,
            },
        },
        "/dev/nvme0n1",
    )

    assert result.tbw_used_percent == pytest.approx(2.3195, abs=0.0001)
    assert result.effective_wear_percent == 8
    assert result.health_percentage == 92.0
    assert result.health_assessment == "Good"


def test_nvme_scan_avoids_optional_self_test_log_command():
    args = _smartctl_args("/dev/nvme0n1")

    assert args == ("smartctl", "-H", "-A", "-i", "-j", "/dev/nvme0n1")
    assert "-a" not in args
    assert "selftest" not in args


def test_nvme_health_uses_endurance_and_extended_counters():
    result = _parse_json(
        {
            "device": {"protocol": "NVMe"},
            "model_name": "Example NVMe",
            "smart_status": {"passed": True},
            "temperature": {"current": 42},
            "nvme_smart_health_information_log": {
                "critical_warning": 0,
                "percentage_used": 12,
                "available_spare": 98,
                "available_spare_threshold": 10,
                "data_units_read": 10,
                "data_units_written": "20",
                "power_cycles": 40,
                "power_on_hours": 8_000,
                "unsafe_shutdowns": 3,
                "media_errors": 0,
                "num_err_log_entries": 1,
            },
        },
        "/dev/nvme0n1",
    )

    assert result.drive_type == "nvme"
    assert result.wear_percentage_used == 12
    assert result.health_percentage == 88
    assert result.health_assessment == "Good"
    assert result.available_spare_percent == 98
    assert result.data_read_bytes == 5_120_000
    assert result.data_written_bytes == 10_240_000
    assert result.media_errors == 0
    assert result.unsafe_shutdowns == 3


def test_failed_smart_always_scores_zero():
    result = _parse_json(
        {
            "rotation_rate": 7200,
            "smart_status": {"passed": False},
            "ata_smart_attributes": {"table": []},
        },
        "/dev/sdb",
    )

    assert result.health == "FAILED"
    assert result.health_percentage == 0
    assert result.health_assessment == "Critical"
