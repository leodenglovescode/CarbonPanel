# Ubuntu 26.04 and sudo-rs

Older CarbonPanel installers wrote a journal rule containing
`--no-pager -n * --output=short-iso`. sudo-rs rejects that wildcard because
it is not the final argument. This can produce warnings for unrelated sudo
commands and prevent CarbonPanel's scoped permissions from working.

## Repair an existing server

Paste this single line over SSH. It edits a temporary copy, validates it with
the installed visudo, backs up the original, and then replaces the file.
It requires your normal sudo password, with no interactive editor.

```bash
sudo bash -c 'set -e; f=/etc/sudoers.d/carbonpanel-updater; t=$(mktemp "$f.XXXXXX"); trap "rm -f -- \"$t\"" EXIT; cp -p "$f" "$t"; sed -i "s/--no-pager -n \* --output=short-iso/--no-pager -n 150 --output=short-iso/g" "$t"; visudo -cf "$t"; b=$(mktemp "$f.backup.XXXXXX"); cp -p "$f" "$b"; mv -f "$t" "$f"; echo "Repaired. Original saved at $b"'
```

Backup and temporary filenames contain a dot so sudo ignores them in
`/etc/sudoers.d`. A validation failure leaves the original file in place.
The older Docker rules ending in a standalone `*` are accepted by sudo-rs
0.2.13, as documented in the [Ubuntu 26.04 sudoers manual](https://manpages.ubuntu.com/manpages/resolute/man5/sudoers-rs.5.html).

After the upstream fix is published to your tracked branch, run
`sudo carbonpanelctl update` to install the full hardening change. Until then,
the old `carbonpanelctl fix` command would recreate the rejected journal rule.

## Policy used by new installs and updates

The installer uses exactly `-n 150`, matching the backend's journal request.
Docker access goes through `/usr/local/libexec/carbonpanel-docker`, installed
as root:root with mode 755 in a root-owned directory. Sudoers grants access to
that helper without argument restrictions; the helper validates every argument.
It accepts only:

- `ps` with CarbonPanel's exact output template;
- non-streaming `stats` with the exact template and explicit container IDs/names;
- `start`, `stop`, or `restart` with exactly one container ID/name.

The helper rejects extra options and unsupported commands, inserts `--` before
container operands, and invokes the absolute Docker binary with a clean
environment. It does not grant Docker group membership. Existing privileged
containers still retain their configured privileges when started.

Install, update, and repair share one policy generator and validate the candidate
with visudo before replacing the active file. No sudoers argument wildcards are
needed. Policy snapshots follow releases during automatic and manual rollbacks
so older backends retain their matching Docker permissions; those older policies
can still contain the previously supported trailing Docker wildcards.

## Publishing

Managed web panels track their installed Git branch, normally `master`.
Merge/push this fix there to make it available to update checks. Installing the
update migrates the helper and policy before restarting the backend. Checks
notify about updates; they do not silently install them on users' servers.
Affected users whose old sudoers entry prevents updates can run the repair line
first and then update from the panel or CLI. No Android version tag is needed.
