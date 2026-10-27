"""Plot Options' transaction/UI contract, independent of UnitConversion implementation."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from echo import CallbackProperty
from glue.viewers.profile.state import ProfileViewerState
from specutils import Spectrum
from traitlets import Any, Bool, Dict, HasTraits, List, Unicode

from jdaviz.configs.default.plugins.plot_options.plot_options import PlotOptions


class ViewerState(ProfileViewerState):
    spectral_y_type = CallbackProperty('Flux')
    spectral_y_type_sync = CallbackProperty(True)
    y_display_unit = CallbackProperty('Jy')
    x_display_unit = CallbackProperty('um')


class QuantityBackend(HasTraits):
    spectral_y_type_selected = Unicode('Flux')
    spectral_y_type_error = Unicode()

    def __init__(self):
        super().__init__()
        self.calls = []
        self.fail_commit = False

    def viewer_y_type(self, viewer):
        return viewer.state.spectral_y_type or self.spectral_y_type_selected

    def quantity_change_error(self, viewers, quantity):
        return '\n'.join(f'{v.label}: missing area; remove blocked layer or turn off app sync.'
                         for v in viewers if v.blocked and quantity == 'Surface Brightness')

    def set_viewer_y_type(self, viewers, quantity=None, sync=None):
        self.calls.append((list(viewers), quantity, sync))
        target = self.spectral_y_type_selected if sync else quantity
        error = self.quantity_change_error(viewers, target)
        if error or self.fail_commit:
            raise ValueError(error or 'Data changed; retry the quantity change.')
        for viewer in viewers:
            if target is not None:
                viewer.state.spectral_y_type = target
            viewer.state.spectral_y_type_sync = sync if sync is not None else False


class Controls(HasTraits):
    """Run the real control methods without constructing unrelated plot widgets."""

    spectral_y_type = Unicode()
    spectral_y_type_sync = Bool(default_value=None, allow_none=True)
    spectral_y_type_available = Bool(False)
    spectral_y_type_mixed = Bool(False)
    spectral_y_type_items = List()
    spectral_y_type_error = Unicode()
    viewer_selected = Any('spectrum')
    viewer_multiselect = Bool(False)
    display_units = Dict()
    config = 'specviz'
    uses_active_status = False
    _user_api_expose_extra = []
    _user_api_remove = []

    _spectral_y_type_viewers = PlotOptions._spectral_y_type_viewers
    _spectral_y_type_unit_conversion = PlotOptions._spectral_y_type_unit_conversion
    _watch_spectral_y_type = PlotOptions._watch_spectral_y_type
    _refresh_spectral_y_type = PlotOptions.__dict__['_refresh_spectral_y_type']
    _validate_spectral_y_type = PlotOptions.__dict__['_validate_spectral_y_type']
    _set_spectral_y_type = PlotOptions.__dict__['_set_spectral_y_type']
    vue_set_spectral_y_type = PlotOptions.vue_set_spectral_y_type
    _on_global_display_unit_changed = PlotOptions._on_global_display_unit_changed
    user_api = PlotOptions.user_api


@pytest.fixture
def controls():
    po = Controls()
    backend = QuantityBackend()
    viewers = [SimpleNamespace(default_class=Spectrum, state=ViewerState(),
                               label=label, blocked=False) for label in ('one', 'two')]
    po.viewer = SimpleNamespace(selected_obj=viewers)
    po._app = SimpleNamespace(get_tray_item_from_name=Mock(return_value=backend))
    po.send_state = Mock()
    po.viewer_multiselect = True
    po.viewer_selected = ['one', 'two']
    po._spectral_y_type_ready = True
    for viewer in viewers:
        po._watch_spectral_y_type(viewer)
    po._refresh_spectral_y_type()
    return po, backend, viewers


def test_atomic_manual_quantity_and_public_api(controls):
    po, backend, viewers = controls
    assert 'spectral_y_type' in dir(po.user_api)
    assert 'spectral_y_type_sync' in dir(po.user_api)
    po.user_api.spectral_y_type = 'Surface Brightness'
    assert backend.calls == [(viewers, 'Surface Brightness', None)]
    assert all(v.state.spectral_y_type == 'Surface Brightness' for v in viewers)
    assert all(not v.state.spectral_y_type_sync for v in viewers)
    assert po.spectral_y_type == 'Surface Brightness'
    assert po.spectral_y_type_sync is False


def test_rejected_quantity_does_not_mutate_either_viewer_or_controls(controls):
    po, backend, viewers = controls
    viewers[1].blocked = True
    po._refresh_spectral_y_type()
    assert not po.spectral_y_type_items[0]['props']['disabled']
    assert po.spectral_y_type_items[1]['props']['disabled']
    with pytest.raises(ValueError, match='two: missing area'):
        po.user_api.spectral_y_type = 'Surface Brightness'
    assert backend.calls == []
    assert po.spectral_y_type == 'Flux'
    assert po.spectral_y_type_sync is True
    assert all(v.state.spectral_y_type == 'Flux' for v in viewers)
    assert all(v.state.spectral_y_type_sync for v in viewers)
    assert 'remove blocked layer' in po.spectral_y_type_error


def test_mixed_selection_and_freeze(controls):
    po, backend, viewers = controls
    viewers[1].state.spectral_y_type = 'Surface Brightness'
    viewers[1].state.spectral_y_type_sync = False
    assert po.spectral_y_type_mixed
    assert po.spectral_y_type == ''
    assert po.spectral_y_type_sync is None
    assert backend.calls == []  # Callback refresh must never become a manual edit.
    po.user_api.spectral_y_type_sync = False
    assert backend.calls == [(viewers, None, False)]
    assert [v.state.spectral_y_type for v in viewers] == ['Flux', 'Surface Brightness']
    assert po.spectral_y_type_sync is False
    assert po.spectral_y_type_mixed


def test_sync_adopts_global_and_refresh_does_not_unpin(controls):
    po, backend, viewers = controls
    po.spectral_y_type_sync = False
    backend.spectral_y_type_selected = 'Surface Brightness'
    backend.calls.clear()
    po.user_api.spectral_y_type_sync = True
    assert backend.calls == [(viewers, None, True)]
    assert po.spectral_y_type == 'Surface Brightness'
    assert po.spectral_y_type_sync is True
    po._on_global_display_unit_changed()
    assert len(backend.calls) == 1
    assert all(v.state.spectral_y_type_sync for v in viewers)


def test_blocked_sync_can_be_disabled_without_quantity_validation(controls):
    po, backend, viewers = controls
    viewers[1].blocked = True
    backend.spectral_y_type_selected = 'Surface Brightness'
    backend.spectral_y_type_error = 'two blocks app change; turn off app sync.'
    assert 'two blocks app change' in po.spectral_y_type_error
    po.spectral_y_type_sync = False
    backend.calls.clear()
    with pytest.raises(ValueError, match='two: missing area'):
        po.spectral_y_type_sync = True
    assert backend.calls == []
    assert po.spectral_y_type_sync is False
    assert all(not v.state.spectral_y_type_sync for v in viewers)
    assert all(v.state.spectral_y_type == 'Flux' for v in viewers)


@pytest.mark.parametrize('frontend', [False, True])
def test_backend_commit_rejection_restores_controls(controls, frontend):
    po, backend, viewers = controls
    backend.fail_commit = True
    if frontend:
        po.vue_set_spectral_y_type({'name': 'spectral_y_type', 'value': 'Surface Brightness'})
    else:
        with pytest.raises(ValueError, match='Data changed'):
            po.spectral_y_type = 'Surface Brightness'
    assert po.spectral_y_type == 'Flux'
    assert po.spectral_y_type_sync is True
    assert 'Data changed' in po.spectral_y_type_error
    assert all(v.state.spectral_y_type == 'Flux' for v in viewers)


def test_frontend_precheck_rejection_resends_current_value(controls):
    po, backend, viewers = controls
    viewers[1].blocked = True
    po.vue_set_spectral_y_type({'name': 'spectral_y_type', 'value': 'Surface Brightness'})
    po.send_state.assert_called_with('spectral_y_type')
    assert po.spectral_y_type == 'Flux'
    assert backend.calls == []


@pytest.mark.parametrize('name,value', [
    ('spectral_y_type', ''),
    ('spectral_y_type', 'Counts'),
    ('spectral_y_type_sync', None),
])
def test_display_only_mixed_values_cannot_be_assigned(controls, name, value):
    po, backend, _ = controls
    with pytest.raises(ValueError):
        setattr(po, name, value)
    assert backend.calls == []


def test_selection_refresh_filters_out_ramp_scatter_and_images(controls):
    po, backend, viewers = controls
    non_spectrum = SimpleNamespace(default_class=None, state=ViewerState())
    spectrum_image = SimpleNamespace(default_class=Spectrum, state=SimpleNamespace())
    po.viewer.selected_obj = [viewers[0], non_spectrum, spectrum_image]
    po.viewer_selected = ['one', 'scatter']
    po.spectral_y_type = 'Surface Brightness'
    assert backend.calls == [([viewers[0]], 'Surface Brightness', None)]
    assert non_spectrum.state.spectral_y_type == 'Flux'
    po.viewer.selected_obj = non_spectrum
    po.viewer_selected = 'scatter'
    po.viewer_multiselect = False
    assert not po.spectral_y_type_available
    assert po.spectral_y_type_sync is None
    with pytest.raises(ValueError, match='Select a spectrum viewer'):
        po.spectral_y_type_sync = False


def test_data_removal_and_global_messages_clear_stale_reasons(controls):
    po, backend, viewers = controls
    viewers[1].blocked = True
    po._refresh_spectral_y_type(SimpleNamespace(data='blocked data'))
    assert po.spectral_y_type_error
    viewers[1].blocked = False
    po._refresh_spectral_y_type(SimpleNamespace(data='removed data'))
    assert po.spectral_y_type_error == ''
    assert not any(item['props']['disabled'] for item in po.spectral_y_type_items)
    backend.spectral_y_type_error = 'Global quantity blocked'
    assert po.spectral_y_type_error == 'Global quantity blocked'
    backend.spectral_y_type_error = ''
    po._on_global_display_unit_changed()
    assert po.spectral_y_type_error == ''
    assert po.display_units == {'spectral': 'um', 'flux': 'Jy'}
    assert backend.calls == []


def test_missing_backend_hides_controls(controls):
    po, _, _ = controls
    po._app.get_tray_item_from_name.return_value = SimpleNamespace()
    po._refresh_spectral_y_type()
    assert not po.spectral_y_type_available
    assert po.spectral_y_type_items == []
    with pytest.raises(ValueError, match='controls available'):
        po.spectral_y_type = 'Surface Brightness'


def test_real_plugin_exposes_traits_and_initializes_without_backend(specviz_helper):
    po = specviz_helper._app.get_tray_item_from_name('g-plot-options')
    assert 'spectral_y_type' in dir(po.user_api)
    assert 'spectral_y_type_sync' in dir(po.user_api)
    assert not po.spectral_y_type_available
