"""Viewer-context lookup and analysis notification regressions."""
from types import SimpleNamespace
from unittest.mock import Mock

import astropy.units as u
from astropy.nddata import StdDevUncertainty
import numpy as np
import pytest
from specutils import Spectrum

from jdaviz.app import PrivateApplication
from jdaviz.core.events import GlobalDisplayUnitChanged
from jdaviz.configs.default.plugins.model_fitting.model_fitting import ModelFitting
from jdaviz.configs.specviz.plugins.line_analysis.line_analysis import LineAnalysis
from jdaviz.configs.cubeviz.plugins.spectral_extraction.spectral_extraction import (
    SpectralExtraction3D)
from jdaviz.configs.cubeviz.plugins.moment_maps.moment_maps import MomentMap


@pytest.mark.parametrize('as_id', [False, True])
@pytest.mark.parametrize('actual_unit', ['mJy', '', None])
def test_contextual_spectral_y_lookup(as_id, actual_unit):
    viewer = SimpleNamespace(state=SimpleNamespace(y_display_unit=actual_unit))
    uc = SimpleNamespace(spectral_y_unit='Jy', viewer_y_unit=Mock(return_value='Jy / sr'))
    app = SimpleNamespace(_jdaviz_helper=object(),
                          get_viewer=Mock(return_value=viewer),
                          get_tray_item_from_name=Mock(return_value=uc))
    assert PrivateApplication._get_display_unit(app, 'spectral_y') == 'Jy'
    assert PrivateApplication._get_display_unit(
        app, 'spectral_y', viewer='local' if as_id else viewer) == (actual_unit or 'Jy / sr')
    if actual_unit:
        uc.viewer_y_unit.assert_not_called()
    else:
        uc.viewer_y_unit.assert_called_once_with(viewer)


def test_fitting_uses_dataset_viewer_not_results_destination():
    other = SimpleNamespace(layers=[SimpleNamespace(layer=SimpleNamespace(label='other'))])
    selected = SimpleNamespace(layers=[SimpleNamespace(layer=SimpleNamespace(label='selected'))])
    plugin = SimpleNamespace(dataset_selected='selected', spectrum_1d_viewers=[other, selected])
    assert ModelFitting._dataset_spectrum_viewer.fget(plugin) is selected
    plugin._dataset_spectrum_viewer = selected
    plugin.cube_fit = False
    plugin._app = SimpleNamespace(get_viewer=Mock(return_value=other))
    # An unrelated targeted event must not change fitted parameter units.
    ModelFitting._on_global_display_unit_changed(
        plugin, GlobalDisplayUnitChanged('spectral_y', 'Jy', viewer='other', sender=plugin))


@pytest.mark.parametrize('contains_selected', [False, True])
def test_line_analysis_targeted_dataset_events(contains_selected):
    viewer = SimpleNamespace(layers=[SimpleNamespace(layer=SimpleNamespace(
        label='selected' if contains_selected else 'other'))])
    plugin = SimpleNamespace(dataset_selected='selected', _calculate_statistics=Mock())
    message = GlobalDisplayUnitChanged('spectral_y', 'Jy', viewer=viewer, sender=plugin)
    LineAnalysis._on_global_display_unit_changed(plugin, message)
    assert plugin._calculate_statistics.called == contains_selected


def test_extraction_preview_unit_context():
    preview = SimpleNamespace()
    other = SimpleNamespace()
    app = SimpleNamespace(_get_display_unit=Mock(return_value='mJy / sr'))
    plugin = SimpleNamespace(slice_indicator_viewers=[preview], _app=app,
                             spectrum_y_units='Jy')
    SpectralExtraction3D._on_global_display_unit_changed(
        plugin, GlobalDisplayUnitChanged('spectral_y', 'mJy', viewer=other, sender=plugin))
    assert plugin.spectrum_y_units == 'Jy'
    SpectralExtraction3D._on_global_display_unit_changed(
        plugin, GlobalDisplayUnitChanged('spectral_y', 'mJy', viewer=preview, sender=plugin))
    assert plugin.spectrum_y_units == 'mJy / sr'
    app._get_display_unit.assert_called_once_with('spectral_y', viewer=preview)


def test_moment_map_ignores_spectral_y_quantity():
    plugin = SimpleNamespace()
    MomentMap._set_data_units(
        plugin, GlobalDisplayUnitChanged('spectral_y', u.Jy, viewer=object(), sender=plugin))


def test_fitting_local_quantity(specviz_helper):
    spectrum = Spectrum(spectral_axis=np.arange(1, 11) * u.um,
                        flux=np.ones(10) * u.Jy / u.sr,
                        uncertainty=StdDevUncertainty(np.full(10, 0.1), unit=u.Jy / u.sr),
                        meta={'PIXAR_SR': 2, '_pixel_scale_factor': 2})
    specviz_helper.load_data(spectrum, data_label='surface brightness')
    app = specviz_helper._app
    viewer = app.get_viewer('spectrum-viewer')
    uc = app.get_tray_item_from_name('g-unit-conversion')
    plugin = specviz_helper.plugins['Model Fitting']._obj
    uc.set_viewer_y_type([viewer], quantity='Flux')
    assert u.Unit(app._get_display_unit('spectral_y')) == u.Jy / u.sr
    assert u.Unit(app._get_display_unit('spectral_y', viewer=viewer)) == u.Jy
    converted = plugin._get_selected_spectrum()
    assert converted.flux.unit == u.Jy
    np.testing.assert_allclose(converted.flux.value, 2)
    np.testing.assert_allclose(converted.uncertainty.array, 0.2)
    plugin.create_model_component('Const1D')
    assert u.Unit(plugin._units['y']) == u.Jy
    assert u.Unit(plugin.component_models[0]['parameters'][0]['unit']) == u.Jy
