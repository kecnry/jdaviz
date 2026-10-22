import multiprocessing
import sys

# Dispatch frozen multiprocessing helpers before importing the application stack.
if __name__ == "__main__":
    multiprocessing.freeze_support()

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import jdaviz.cli
from jdaviz.core.open_file_requests import OpenFileRequestServer


OPEN_FILE_PATHS = []
OPEN_FILE_CALLBACK = None
MACOS_OPEN_FILES_DELEGATE = None
MACOS_OPEN_FILES_HANDLER = None


def _debug_open_event(stage, **details):
    """Write opt-in file-open diagnostics without logging paths by default."""
    log_path = os.environ.get('JDAVIZ_OPEN_DEBUG_LOG')
    if not log_path:
        return
    try:
        with open(log_path, 'a', encoding='utf-8') as log:
            log.write(f"{stage}: {details!r}\n")
    except OSError:
        pass


def _normalize_open_path(arg):
    """Normalize an OS-delivered path or file URL without splitting path characters."""
    if not arg:
        return None
    candidate = str(arg).strip()
    if candidate.startswith("file:"):
        parsed = urlparse(candidate)
        candidate = unquote(parsed.path)
        if parsed.netloc and parsed.netloc not in ('', 'localhost'):
            candidate = f"//{parsed.netloc}{candidate}"
        # file:///C:/... is the common Windows file-URL representation.
        if os.name == 'nt' and len(candidate) > 2 and candidate[0] == '/' and candidate[2] == ':':
            candidate = candidate[1:]
    elif candidate.startswith("~/"):
        candidate = str(Path.home() / candidate[2:])
    elif candidate.startswith("-"):
        return None

    path = Path(candidate).expanduser()
    if path.is_file():
        return str(path.absolute())
    return None


def _save_open_files(filepaths):
    """Collect each path once, preserving the path list as structured data."""
    for filepath in filepaths:
        normalized = _normalize_open_path(filepath)
        if normalized is not None and normalized not in OPEN_FILE_PATHS:
            OPEN_FILE_PATHS.append(normalized)
    return list(OPEN_FILE_PATHS)


def _install_macos_open_files_handler():
    """Capture Finder document-open events without mutating parsed CLI arguments."""
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return

    try:
        import AppKit
        from Foundation import NSObject
    except Exception:
        return

    global MACOS_OPEN_FILES_DELEGATE, MACOS_OPEN_FILES_HANDLER
    nsapp = AppKit.NSApplication.sharedApplication()
    _debug_open_event('installing macOS open-file handlers',
                      delegate_before=repr(nsapp.delegate()))

    def _handle_paths(filenames):
        _debug_open_event('macOS open-files callback', filenames=list(filenames))
        before = set(OPEN_FILE_PATHS)
        paths = _save_open_files(filenames)
        new_paths = [path for path in paths if path not in before]
        _debug_open_event('macOS callback normalized paths', paths=new_paths)
        if new_paths and OPEN_FILE_CALLBACK is not None:
            OPEN_FILE_CALLBACK(new_paths)
        return bool(paths)

    try:
        nsapp.setOpenFilesHandler_(_handle_paths)
        MACOS_OPEN_FILES_HANDLER = _handle_paths
        _debug_open_event('installed NSApplication open-files handler')
    except Exception as e:
        _debug_open_event('failed to install NSApplication open-files handler',
                          error=repr(e))

    class _FinderOpenFilesDelegate(NSObject):
        def application_openFiles_(self, _application, filenames):
            _handle_paths(filenames)

        def application_openURLs_(self, _application, urls):
            _handle_paths([str(url) for url in urls])
            return True

    try:
        delegate = _FinderOpenFilesDelegate.alloc().init()
        nsapp.setDelegate_(delegate)
        # PyObjC delegate wrappers must remain strongly referenced.
        MACOS_OPEN_FILES_DELEGATE = delegate
        _debug_open_event('installed macOS delegate', delegate=repr(delegate))
    except Exception as e:
        _debug_open_event('failed to install macOS delegate', error=repr(e))


def _filter_python_runtime_args(argv):
    """Drop runtime-only flags used by frozen Python and multiprocessing helpers."""
    filtered = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {'-B', '-S', '-I'} or arg.startswith('-psn_'):
            i += 1
            continue
        if arg == '-c' and i + 1 < len(argv):
            cmd = argv[i + 1]
            if ('multiprocessing.resource_tracker' in cmd or
                    'from multiprocessing.resource_tracker import main' in cmd):
                i += 2
                continue
        filtered.append(arg)
        i += 1
    return filtered


def _register_os_opened_files(argv):
    """Collect file-association arguments on all platforms and Finder events on macOS."""
    _debug_open_event('startup sys.argv', argv=list(argv), platform=sys.platform,
                      frozen=getattr(sys, 'frozen', False))
    if sys.platform == "darwin" and getattr(sys, "frozen", False):
        _install_macos_open_files_handler()
        candidates = _filter_python_runtime_args(list(argv))
        try:
            from Foundation import NSProcessInfo
        except Exception:
            NSProcessInfo = None
        if NSProcessInfo is not None:
            process_args = [
                str(arg) for arg in NSProcessInfo.processInfo().arguments()[1:]
            ]
            _debug_open_event('macOS NSProcessInfo arguments', argv=process_args)
            candidates.extend(_filter_python_runtime_args(process_args))
    else:
        candidates = list(argv)

    # Do not reinterpret values supplied to ordinary CLI options as OS-open events.
    positional = []
    skip_next = False
    options_with_values = {
        '-fp', '--filepath', '-ff', '--file_format', '--layout', '--instrument',
        '--browser', '--theme', '--verbosity', '--history-verbosity', '--host', '--port'
    }
    for arg in candidates:
        if skip_next:
            skip_next = False
            continue
        if arg in options_with_values:
            skip_next = True
            continue
        if arg.startswith('-'):
            continue
        normalized = _normalize_open_path(arg)
        if normalized is not None:
            positional.append(normalized)

    paths = _save_open_files(positional)
    _debug_open_event('normalized startup file paths', paths=paths)
    return paths


def _prepare_cli_args(argv, clicked_files):
    """Convert bare OS file arguments into the hidden clicked-file CLI option."""
    original = _filter_python_runtime_args(list(argv))
    options_with_values = {
        '-fp', '--filepath', '-ff', '--file_format', '--layout', '--instrument',
        '--browser', '--theme', '--verbosity', '--history-verbosity', '--host', '--port'
    }
    clicked_set = set(clicked_files)
    args = []
    skip_next = False
    for arg in original:
        if skip_next:
            args.append(arg)
            skip_next = False
        elif arg in options_with_values:
            args.append(arg)
            skip_next = True
        elif _normalize_open_path(arg) not in clicked_set:
            args.append(arg)

    existing = set()
    for index, arg in enumerate(args[:-1]):
        if arg == '--clicked-file':
            existing.add(args[index + 1])
    for filepath in clicked_files:
        if filepath not in existing:
            args.extend(['--clicked-file', filepath])
    _debug_open_event('prepared CLI arguments', argv=args)
    return args


def _run():
    def dispatch_file_open(paths):
        from jdaviz.solara import receive_clicked_file_paths
        receive_clicked_file_paths(paths)

    global OPEN_FILE_CALLBACK
    OPEN_FILE_CALLBACK = dispatch_file_open
    clicked_files = _register_os_opened_files(sys.argv[1:])
    _debug_open_event('clicked files passed to app', paths=clicked_files)

    instance_server = OpenFileRequestServer(dispatch_file_open)
    if not instance_server.is_primary:
        instance_server.forward_or_raise(clicked_files)
        return

    import matplotlib_inline
    import matplotlib_inline.backend_inline  # noqa: F401
    import matplotlib

    # Help PyInstaller include and register the inline backend.
    matplotlib.use("module://matplotlib_inline.backend_inline")
    matplotlib.use("inline")
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        user_home = Path.home()
        jdaviz_cache = user_home / ".cache" / "jdaviz"
        jdaviz_cache.mkdir(parents=True, exist_ok=True)
        os.environ['JDAVIZ_CACHE_DIR'] = str(jdaviz_cache)
        astropy_cache = user_home / ".cache" / "astropy"
        astropy_cache.mkdir(parents=True, exist_ok=True)
        os.environ['ASTROPY_CACHE_DIR'] = str(astropy_cache)
        os.chdir(user_home)

    orig_args = _filter_python_runtime_args(sys.argv[1:])
    args = _prepare_cli_args(orig_args, clicked_files)
    has_layout = any(a == '--layout' or a.startswith('--layout=') for a in orig_args)
    if not has_layout:
        args.extend(['--layout', 'flexible'])

    if not any(a == '--browser' or a.startswith('--browser=') for a in args):
        args.extend(['--browser', 'qt'])

    sys.argv = [sys.argv[0], *args]
    jdaviz.cli._main()


if __name__ == "__main__":
    _run()
