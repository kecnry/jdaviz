"""Integration tests for quantity inheritance, overrides and atomic rejection."""
import numpy as np
import pytest
from astropy import units as u
from specutils import Spectrum

from jdaviz.core.unit_conversion_utils import spectral_y_conversion_error


def spectrum(unit=u.Jy, area=None):
    meta = {} if area is None else {'_pixel_scale_factor': area}
    return Spectrum(flux=np.ones(5) * unit, spectral_axis=np.arange(1, 6) * u.um,
                    meta=meta)


@pytest.mark.parametrize('area', [None, 0, -1, np.nan, np.inf])
def test_missing_or_invalid_area(area):
    assert spectral_y_conversion_error(spectrum(u.Jy / u.sr, area), 'Jy')


def test_conversion_uses_actual_target():
    assert not spectral_y_conversion_error(spectrum(u.Jy / u.sr, 2), 'Jy')
    assert not spectral_y_conversion_error(spectrum(u.Jy / u.sr), 'MJy / sr')
    assert spectral_y_conversion_error(spectrum(u.Jy / u.sr), 'MJy / pix2')


def test_local_override_and_global_sync(deconfigged_helper):
    helper = deconfigged_helper
    helper.load(spectrum(u.Jy / u.sr), format='1D Spectrum', data_label='sb')
    uc = helper.plugins['Unit Conversion']._obj
    sb_viewer = helper._app.get_viewer('1D Spectrum')
    # An explicit new-viewer quantity is independent of the app default.
    helper.load(spectrum(), format='1D Spectrum', data_label='flux',
                spectral_y_type='Flux')
    flux_viewer = helper._app.get_viewer('1D Spectrum (1)')
    assert sb_viewer.state.spectral_y_type_sync
    assert not flux_viewer.state.spectral_y_type_sync
    assert uc.viewer_y_type(sb_viewer) == 'Surface Brightness'
    assert u.Unit(sb_viewer.state.y_display_unit).is_equivalent(u.Jy / u.sr)
    # The synced SB-only viewer blocks adopting flux without an area.
    with pytest.raises(ValueError, match='sb'):
        uc.spectral_y_type.selected = 'Flux'
    assert uc.spectral_y_type.selected == 'Surface Brightness'
    assert sb_viewer.state.spectral_y_type_sync
    assert len(helper._app.data_collection) == 2
    # Unsyncing the blocker allows the default to change without converting it.
    uc.set_viewer_y_type([sb_viewer], sync=False)
    uc.spectral_y_type.selected = 'Flux'
    assert uc.viewer_y_type(flux_viewer) == 'Flux'
    assert u.Unit(flux_viewer.state.y_display_unit) == u.Jy
    with pytest.raises(ValueError, match='sb'):
        uc.set_viewer_y_type([sb_viewer], sync=True)
    assert not sb_viewer.state.spectral_y_type_sync


def test_plot_options_real_backend(deconfigged_helper):
    helper = deconfigged_helper
    helper.load(spectrum(), format='1D Spectrum')
    viewer = helper._app.get_viewer('1D Spectrum')
    plot = helper.plugins['Plot Options']
    plot.viewer = '1D Spectrum'
    plot.spectral_y_type = 'Surface Brightness'
    assert not viewer.state.spectral_y_type_sync
    assert u.Unit(viewer.state.y_display_unit) == u.Jy / u.pix**2
    plot.spectral_y_type_sync = True
    assert viewer.state.spectral_y_type_sync
    assert u.Unit(viewer.state.y_display_unit) == u.Jy