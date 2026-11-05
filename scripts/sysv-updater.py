#!/usr/bin/python3 -I
"""Root-owned SysV update supervisor. No caller-supplied paths or commands."""
import asyncio
import fcntl
import json
import os
import signal
import stat
import sys
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path('/etc/carbonpanel/updater.json')
RUNTIME = Path('/run/carbonpanel-updater')


def read_json(path):
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_json(path, data):
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        with temporary.open('x') as stream:
            json.dump(data, stream)
        os.chmod(temporary, 0o644)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def trusted(path):
    info = path.stat()
    if info.st_uid != 0 or info.st_mode & 0o022:
        raise RuntimeError(f'{path} must be owned by root and not writable by other users')


def configuration():
    trusted(CONFIG.parent)
    trusted(CONFIG)
    config = read_json(CONFIG)
    root = Path(config['install_root'])
    if not root.is_absolute():
        raise RuntimeError('Updater install root must be absolute')
    control = root / 'bin/carbonpanelctl'
    # The launcher may only execute the root-managed installed control script.
    for path in (*root.parents, root, root / 'bin', control):
        trusted(path)
    return config, control, root / 'shared'


def prepare_runtime():
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    trusted(RUNTIME)
    if RUNTIME.is_symlink():
        raise RuntimeError('Updater runtime directory must not be a symlink')


def lock_file(path):
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise RuntimeError('Updater lock must be a regular file')
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return descriptor
    except BlockingIOError:
        os.close(descriptor)
        return None


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def queue_operation(shared, action):
    operation_id = uuid.uuid4().hex
    data = read_json(shared / 'update-status.json')
    if action == 'check':
        data.update(check_id=operation_id, check_state='queued', check_started_at=now(),
                    check_finished_at=None, status='checking', error=None)
    else:
        data.update(operation_id=operation_id, operation_kind='update', operation_state='queued',
                    operation_started_at=now(), operation_updated_at=now(),
                    operation_finished_at=None, progress_phase='queued',
                    progress_label='Starting SysV updater', progress_percent=1,
                    restart_pending=False, restart_performed=False, status='installing', error=None)
    write_json(shared / 'update-status.json', data)
    return operation_id


def finish_operation(shared, action, operation_id, returncode, error=None):
    path = shared / 'update-status.json'
    data = read_json(path)
    prefix = 'check' if action == 'check' else 'operation'
    if data.get(prefix + '_id') != operation_id:
        return
    if data.get(prefix + '_state') in {'succeeded', 'failed'}:
        return  # The installer already recorded its own result.
    state = 'failed' if returncode else 'succeeded'
    data.update({prefix + '_state': state, prefix + '_finished_at': now()})
    if returncode:
        data.update(error=error or f'SysV {action} exited with status {returncode}',
                    status='check_failed' if action == 'check' else 'update_failed')
    if not returncode:
        data['status'] = ('installed' if action == 'update' else
                          'update_available' if data.get('update_available') else 'up_to_date')
        data['error'] = None
    if action == 'update':
        data.update(restart_pending=False, operation_updated_at=now(), progress_phase=state,
                    progress_label=error or f'Update {state}')
        if not returncode:
            data['progress_percent'] = 100
    write_json(path, data)


def running_status(shared):
    descriptor = lock_file(RUNTIME / 'launcher.lock')
    if descriptor is None:
        state = read_json(RUNTIME / 'job.json')
        return {'running': True, 'kind': state.get('kind', 'external'),
                'operation_id': state.get('operation_id')}
    try:
        # Keep both locks while repairing stale progress so a new job cannot
        # queue a fresh operation between the lock check and the status write.
        cli_lock = lock_file(shared / 'update.lock')
        if cli_lock is None:
            return {'running': True, 'kind': 'external'}
        try:
            progress = read_json(shared / 'update-status.json')
            for action, prefix in (('update', 'operation'), ('check', 'check')):
                if progress.get(prefix + '_state') in {'queued', 'running'}:
                    operation_id = progress.get(prefix + '_id')
                    if operation_id:
                        finish_operation(shared, action, operation_id, 1,
                                         'SysV updater stopped before recording a result')
            state = read_json(RUNTIME / 'job.json')
            if state.get('running'):
                state['running'] = False
                write_json(RUNTIME / 'job.json', state)
            return {'running': False, 'kind': None}
        finally:
            os.close(cli_lock)
    finally:
        os.close(descriptor)


def job_environment(config):
    # Proxy settings are read by carbonpanelctl from the panel's saved settings.
    # Do not inherit PYTHONPATH, BASH_ENV, installer flags, or proxy overrides.
    return {
        'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'HOME': '/root', 'LC_ALL': 'C',
        'CARBONPANEL_INSTALL_ROOT': config['install_root'],
        'CARBONPANEL_REPO_URL': config['repo_url'],
        'APP_PORT': str(config['app_port']),
        'CARBONPANEL_BACKEND_PORT': str(config['backend_port']),
        'CARBONPANEL_LOCK_HELD': 'true',
        'no_proxy': 'localhost,127.0.0.1,::1', 'NO_PROXY': 'localhost,127.0.0.1,::1',
    }


async def supervise(config, control, shared, action, operation_id, acknowledgement):
    proc = None
    acknowledged = False
    log_path = RUNTIME / 'updater.log'
    with log_path.open('ab', buffering=0) as log:
        os.chmod(log_path, 0o600)
        try:
            proc = await asyncio.create_subprocess_exec(
                '/bin/bash', str(control), action, env=job_environment(config),
                stdin=asyncio.subprocess.DEVNULL, stdout=log,
                stderr=asyncio.subprocess.STDOUT, start_new_session=True,
            )
            state = {'running': True, 'kind': action, 'operation_id': operation_id,
                     'pid': os.getpid()}
            write_json(RUNTIME / 'job.json', state)
            os.write(acknowledgement, json.dumps(state).encode())
            os.close(acknowledgement)
            acknowledged = True
            # Capture directly to the log, so a daemon inheriting stdout cannot
            # keep a pipe open and prevent us from observing installer exit.
            code = await proc.wait()
            finish_operation(shared, action, operation_id, code)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            message = f'SysV updater failed: {exc}'
            log.write((message + '\n').encode())
            if proc is not None and proc.returncode is None:
                os.killpg(proc.pid, signal.SIGTERM)
                await proc.wait()
            finish_operation(shared, action, operation_id, 1, message)
            if not acknowledged:
                os.write(acknowledgement, json.dumps({'error': message}).encode())
                os.close(acknowledgement)
        finally:
            write_json(RUNTIME / 'job.json', {'running': False, 'kind': action,
                                             'operation_id': operation_id})


def launch(config, control, shared, action):
    locks = []
    for path in (RUNTIME / 'launcher.lock', shared / 'update.lock'):
        descriptor = lock_file(path)
        # Status reads briefly hold the launcher lock too. Allow those to finish
        # while still rejecting a real overlapping job promptly.
        for _ in range(5):
            if descriptor is not None:
                break
            time.sleep(0.01)
            descriptor = lock_file(path)
        if descriptor is None:
            for descriptor in locks:
                os.close(descriptor)
            raise RuntimeError('Another update or version check is already running')
        locks.append(descriptor)
    try:
        operation_id = queue_operation(shared, action)
        # Publish the kind before detaching so status sees the queued operation.
        write_json(RUNTIME / 'job.json', {'running': True, 'kind': action,
                                         'operation_id': operation_id})
        reader, writer = os.pipe()
        first_child = os.fork()
        if first_child == 0:
            os.close(reader)
            os.setsid()
            if os.fork():
                os._exit(0)
            os.chdir('/')
            os.umask(0o077)
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            with open('/dev/null', 'r+b', buffering=0) as null:
                for target in (0, 1, 2):
                    os.dup2(null.fileno(), target)
            # Locks stay in this supervisor, not the installer/backend children.
            try:
                asyncio.run(supervise(config, control, shared, action, operation_id, writer))
            finally:
                os._exit(0)
        os.close(writer)
        # The detached child retains both flock descriptions until it exits.
        for descriptor in locks:
            os.close(descriptor)
        locks.clear()
        with os.fdopen(reader) as stream:
            result = json.load(stream)
        os.waitpid(first_child, 0)
        if result.get('error'):
            raise RuntimeError(result['error'])
        return result
    finally:
        for descriptor in locks:
            os.close(descriptor)


def logs():
    path = RUNTIME / 'updater.log'
    if not path.is_file():
        return ''
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size - 131072))
        return '\n'.join(deque(stream.read().decode(errors='replace').splitlines(), maxlen=150))


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {'check', 'update', 'status', 'logs'}:
        raise RuntimeError('Expected exactly one of: check, update, status, logs')
    if os.geteuid() != 0:
        raise RuntimeError('The updater helper must run as root')
    config, control, shared = configuration()
    prepare_runtime()
    action = sys.argv[1]
    if action == 'logs':
        print(logs())
    elif action == 'status':
        print(json.dumps(running_status(shared)))
    else:
        print(json.dumps(launch(config, control, shared, action)))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
