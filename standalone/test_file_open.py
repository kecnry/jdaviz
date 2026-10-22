import importlib.util
import os
from pathlib import Path
import tempfile
import threading

import pytest


ENTRYPOINT_PATH = Path(__file__).with_name('jdaviz-cli-entrypoint.py')
SPEC = importlib.util.spec_from_file_location('jdaviz_cli_entrypoint', ENTRYPOINT_PATH)
ENTRYPOINT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRYPOINT)


def test_open_path_normalization_preserves_spaces_and_unicode(tmp_path):
    filepath = tmp_path / 'a space – spectrum.fits'
    filepath.touch()

    assert ENTRYPOINT._normalize_open_path(str(filepath)) == str(filepath)
    file_url = filepath.as_uri()
    assert ENTRYPOINT._normalize_open_path(file_url) == str(filepath)


def test_open_path_normalization_does_not_split_colons(tmp_path):
    if os.name == 'nt':
        pytest.skip('Colon is not valid in a Windows filename.')
    filepath = tmp_path / 'fits:part.fits'
    filepath.touch()

    assert ENTRYPOINT._normalize_open_path(str(filepath)) == str(filepath)


def test_prepare_cli_args_rewrites_bare_paths_without_delimiters(tmp_path):
    filepath = tmp_path / 'a;part:two.fits'
    filepath.touch()
    path = str(filepath)

    result = ENTRYPOINT._prepare_cli_args(['--port', '0', path], [path])

    assert result == ['--port', '0', '--clicked-file', path]


def test_register_open_files_skips_filepath_option_values(tmp_path):
    filepath = tmp_path / 'normal-load.fits'
    filepath.touch()
    ENTRYPOINT.OPEN_FILE_PATHS.clear()

    assert ENTRYPOINT._register_os_opened_files(['--filepath', str(filepath)]) == []


def test_register_open_files_accepts_multiple_paths(tmp_path):
    first = tmp_path / 'first.fits'
    second = tmp_path / 'second.fits'
    first.touch()
    second.touch()
    ENTRYPOINT.OPEN_FILE_PATHS.clear()

    assert ENTRYPOINT._register_os_opened_files([str(first), str(second)]) == [
        str(first), str(second)
    ]


def test_open_request_is_forwarded_to_primary_instance(tmp_path):
    from jdaviz.core.open_file_requests import OpenFileRequestServer

    received = []
    request_received = threading.Event()

    def callback(paths):
        received.extend(paths)
        request_received.set()

    ipc_dir = Path(tempfile.mkdtemp(prefix='jdvtest-'))
    primary = OpenFileRequestServer(callback, directory=ipc_dir)
    secondary = OpenFileRequestServer(callback, directory=ipc_dir)
    try:
        assert primary.is_primary
        assert not secondary.is_primary
        assert secondary.forward_or_raise(['/tmp/clicked.fits'])
        assert request_received.wait(timeout=3)
        assert received == ['/tmp/clicked.fits']
    finally:
        secondary.close()
        primary.close()
        for path in ipc_dir.iterdir():
            path.unlink()
        ipc_dir.rmdir()
