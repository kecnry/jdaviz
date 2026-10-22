import os
from pathlib import Path
import threading

import solara
import solara.lab
import ipyvue

import jdaviz
from jdaviz.app import custom_components

config = None
data_list = []
format_list = []
clicked_file_paths = []
load_data_kwargs = {}
jdaviz_verbosity = 'error'
jdaviz_history_verbosity = 'info'
_active_helper = None
_pending_clicked_file_paths = []
_clicked_file_paths_lock = threading.Lock()


def receive_clicked_file_paths(filepaths):
    """Add OS-opened paths to the live helper, or queue until it is created."""
    paths = list(dict.fromkeys(str(path) for path in filepaths))
    with _clicked_file_paths_lock:
        helper = _active_helper
        if helper is None:
            _pending_clicked_file_paths.extend(paths)
            return
    helper._app._add_clicked_file_loaders(paths)


def _set_active_helper(helper):
    global _active_helper
    with _clicked_file_paths_lock:
        _active_helper = helper
        pending_paths = list(dict.fromkeys(_pending_clicked_file_paths))
        _pending_clicked_file_paths.clear()
    if pending_paths:
        helper._app._add_clicked_file_loaders(pending_paths)


@solara.lab.on_kernel_start
def on_kernel_start():
    print("Starting kernel", solara.get_kernel_id())
    # at import time, solara runs with a dummy kernel
    # we simply ignore that
    if "dummy" in solara.get_kernel_id():
        return

    def on_kernel_close():
        def exit_process():
            # sys.exit(0) does not work, it just throws an exception
            # this really makes the process exit
            os._exit(0)
        # give the kernel some time to close
        threading.Thread(target=exit_process).start()
    return on_kernel_close


def create_shared_widgets():
    for name, path in custom_components.items():
        ipyvue.register_component_from_file(None, name,
                                            os.path.join(os.path.dirname(jdaviz.__file__), path))

    ipyvue.register_component_from_file('g-viewer-tab', "container.vue", jdaviz.__file__)


def get_app_or_launcher():
    '''
    Return either the app instance or the launcher page as appropriate
    '''
    if config is None or not hasattr(jdaviz.configs, config):
        if config == 'Flexible':
            viz = jdaviz.gca()
            _set_active_helper(viz)
            if clicked_file_paths:
                receive_clicked_file_paths(clicked_file_paths)
            if not len(data_list) and not clicked_file_paths:
                jdaviz.loaders['file'].open_in_tray()
            elif data_list:
                with jdaviz.batch_load():
                    for filename, format in zip(data_list, format_list):
                        jdaviz.load(filename, format=format)
        else:
            from jdaviz.core.launcher import Launcher
            launcher = Launcher(height='100vh',
                                filepath=(data_list[0] if len(data_list) == 1 else ''))
            return launcher.main_with_launcher

    else:
        viz = getattr(jdaviz.configs, config)(verbosity=jdaviz_verbosity,
                                              history_verbosity=jdaviz_history_verbosity)
        with jdaviz.batch_load():
            for filename, format in zip(data_list, format_list):
                if config == 'Mosviz':
                    viz.load(directory=filename, format=format, **load_data_kwargs)
                else:
                    viz.load(filename, format=format, **load_data_kwargs)

    return viz._app


@solara.component
def Jdaviz():
    # Create the shared widgets, using use_memo to ensure we only do it once
    solara.use_memo(create_shared_widgets, [])

    app_or_launcher, set_app_or_launcher = solara.use_state(None)

    def load_app():
        set_app_or_launcher(get_app_or_launcher())

    # We need to use use_effect so that the initial Solara render happens before the app
    # instantiates internal Solara components (file_drop, file_browser), which would otherwise
    # be detected and rendered at the top level outside the app.
    solara.use_effect(load_app, [config, data_list, format_list, clicked_file_paths])

    return solara.Column(children=[app_or_launcher] if app_or_launcher is not None else [])


@solara.component
def Page():
    if config is None:
        solara.Text("No config defined")
        return

    solara.Style(Path(__file__).parent / "solara.css")

    solara.Title("Jdaviz")
    Jdaviz()
