# NAS monitoring and SysV installation

The **Disks → RAID, LVM & Fans** section reports existing storage and sensors,
including unmounted arrays and volumes. It refreshes every 30 seconds, has its own
refresh button, and is searchable with Cmd/Ctrl+K. All NAS monitoring is read-only.

- **Linux MD RAID:** array level, state, capacity, configured member count,
  degraded count, member device/state/slot, sync action and rebuild progress.
  Data comes from `/sys/class/block/*/md`; mdadm is not required. Hardware RAID,
  ZFS and proprietary storage controllers are outside this collector.
- **LVM2:** physical volumes, volume groups, logical volumes, capacity/free space,
  attributes, backing devices and thin-pool data/metadata allocation when reported.
  Mount usage remains in the existing disk cards; pool allocation is not filesystem usage.
  The installer installs `lvm2` and a root-owned reporting helper. Its sudo rules
  allow only fixed `pvs`, `vgs` and `lvs` reports. No storage-changing operations are exposed.
  Missing tools, permission failures and report errors appear in the section.
  Existing installations can provision the helper with `sudo carbonpanelctl fix`
  after updating to this installer.
- **Fans/PWM:** hwmon driver names, fan RPM, sensor faults, raw PWM duty values
  (0–255) and numeric enable modes where exposed. PWM channels are listed
  independently of fan channels; their numbering does not establish a physical
  association. Modes depend on the driver. Older hwmon `device/` layouts are supported.
  No fan settings are written and no sensor-detection probes are run. Missing
  channels mean the running kernel/driver does not expose them, not a stopped fan.

## SysV

The installer checks for a running systemd instance, rather than just an installed
`systemctl`. Without systemd it writes `/etc/init.d/carbonpanel-backend`, registers
it through `update-rc.d`, and uses `start-stop-daemon` to run the backend as the
CarbonPanel service user. The service loads the shared backend environment,
records a PID under `/run`, and logs to `/opt/carbonpanel/shared/backend.log`
(or the configured install root). Unlike the systemd unit, this script does not
automatically restart a crashed backend.

```sh
sudo service carbonpanel-backend status
sudo service carbonpanel-backend restart
sudo carbonpanelctl check
sudo carbonpanelctl update
sudo carbonpanelctl rollback
```

Install, update, rollback, repair and uninstall select the running init system.
Browser-triggered updates and scheduled systemd update checks require systemd;
Settings shows manual update instructions on SysV. Service management pages and
systemd journal views still require systemd. No broad service-control sudo rule is
added for SysV. Storage and hardware monitoring do not require systemd.

## Debian 13 with a vendor Linux 4.9 kernel

This combination needs verification on the actual NAS; it is not certified by these
changes. The collectors use long-established MD and hwmon sysfs interfaces and
LVM2 JSON reports, and do not require a modern systemd version. Vendor drivers can
expose fewer attributes or hide storage/sensors from a chroot/container.

The backend still requires Python 3.11+. Installation currently builds the web
frontend on the host and requires working Node.js 18+ and npm. Upstream Node binary
kernel requirements can exceed Linux 4.9; having Debian 13 userspace alone does not
guarantee a binary will run. The installer checks that Python and Node execute
before building. Use a distribution/vendor-compatible runtime where available;
these changes do not install or replace your kernel or vendor fan driver.

Before installation, these read-only commands help establish compatibility:

```sh
uname -m
uname -r
ps -p 1 -o comm=
python3 --version
node --version
cat /proc/mdstat
ls /sys/class/hwmon
sudo pvs
sudo vgs
sudo lvs -a -o +devices
```

Interface references: [Linux MD](https://docs.kernel.org/admin-guide/md.html),
[hwmon sysfs](https://www.kernel.org/doc/html/v5.12/hwmon/sysfs-interface.html),
[LVM reports](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/single/logical_volume_manager_administration/),
and [Node platform requirements](https://github.com/nodejs/node/blob/main/BUILDING.md).
