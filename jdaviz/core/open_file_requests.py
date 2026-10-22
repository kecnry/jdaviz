"""Single-instance local IPC for desktop file-open requests."""

import atexit
import base64
import hashlib
import json
import multiprocessing.connection
import os
from pathlib import Path
import tempfile
import threading
import time
import uuid


class OpenFileRequestServer:
    """Own a per-user instance lock and receive authenticated path-list requests."""

    def __init__(self, callback, directory=None):
        self.callback = callback
        self.directory = (Path.home() / '.cache' / 'jdaviz'
                          if directory is None else Path(directory))
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.directory, 0o700)
        except OSError:
            pass
        self.metadata_path = self.directory / 'open-file-instance.json'
        self.lock_path = self.directory / 'open-file-instance.lock'
        self._lock_file = self.lock_path.open('a+b')
        try:
            os.chmod(self.lock_path, 0o600)
        except OSError:
            pass
        self._listener = None
        self._thread = None
        self._metadata = None
        self.is_primary = self._acquire_lock()
        if self.is_primary:
            self._start_listener()
            atexit.register(self.close)

    def _acquire_lock(self):
        self._lock_file.seek(0)
        if self._lock_file.read(1) == b'':
            self._lock_file.write(b'0')
            self._lock_file.flush()
        self._lock_file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lock_file.close()
            return False
        return True

    def _start_listener(self):
        secret = os.urandom(32)
        instance_id = uuid.uuid4().hex
        user_id = hashlib.sha256(str(Path.home()).encode()).hexdigest()[:12]
        if os.name == 'nt':
            address = rf'\\.\pipe\jdaviz-{user_id}-{instance_id}'
            family = 'AF_PIPE'
        else:
            address = str(Path(tempfile.gettempdir()) / f'jdv-{instance_id[:12]}.sock')
            family = 'AF_UNIX'
        self._listener = multiprocessing.connection.Listener(
            address, family=family, authkey=secret)
        self._metadata = {
            'address': address,
            'family': family,
            'authkey': base64.b64encode(secret).decode('ascii')
        }
        temporary_path = self.metadata_path.with_suffix('.tmp')
        temporary_path.write_text(json.dumps(self._metadata), encoding='utf-8')
        try:
            os.chmod(temporary_path, 0o600)
        except OSError:
            pass
        temporary_path.replace(self.metadata_path)
        self._thread = threading.Thread(target=self._serve, daemon=True,
                                        name='jdaviz-open-file-requests')
        self._thread.start()

    def _serve(self):
        while self._listener is not None:
            try:
                connection = self._listener.accept()
            except (OSError, EOFError):
                return
            try:
                paths = connection.recv()
                if isinstance(paths, list) and all(isinstance(path, str) for path in paths):
                    self.callback(paths)
                    connection.send(True)
                else:
                    connection.send(False)
            except (EOFError, OSError):
                pass
            finally:
                connection.close()

    def forward_or_raise(self, paths, timeout=3):
        """Forward paths to the primary instance; return False if this is primary."""
        if self.is_primary:
            return False
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                metadata = json.loads(self.metadata_path.read_text(encoding='utf-8'))
                authkey = base64.b64decode(metadata['authkey'])
                connection = multiprocessing.connection.Client(
                    metadata['address'], family=metadata['family'], authkey=authkey)
                try:
                    connection.send(list(paths))
                    return bool(connection.recv())
                finally:
                    connection.close()
            except (OSError, EOFError, KeyError, ValueError, json.JSONDecodeError):
                time.sleep(0.1)
        raise RuntimeError(
            'A jdaviz instance is running but could not receive the file-open request.')

    def close(self):
        if self._listener is not None:
            listener, self._listener = self._listener, None
            try:
                listener.close()
            except OSError:
                pass
            if self._metadata is not None and self._metadata['family'] == 'AF_UNIX':
                try:
                    Path(self._metadata['address']).unlink()
                except OSError:
                    pass
        if self._metadata is not None:
            try:
                if json.loads(self.metadata_path.read_text(encoding='utf-8')) == self._metadata:
                    self.metadata_path.unlink()
            except (OSError, json.JSONDecodeError):
                pass
        if not self._lock_file.closed:
            try:
                if os.name == 'nt':
                    import msvcrt
                    self._lock_file.seek(0)
                    msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self._lock_file.close()
