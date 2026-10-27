import pytest
from astropy import units as u
from specutils import Spectrum

from jdaviz.core.events import GlobalDisplayUnitChanged
from jdaviz.core.loaders.importers.spectrum1d.spectrum1d import SpectrumImporter
from jdaviz.core.viewer_creators.spectrum1d.spectrum1d import Spectrum1DViewerCreator


@pytest.fixture
def quantity_setup(deconfigged_helper):
    helper = deconfigged_helper
    flux = Spectrum(flux=[1, 2, 3] * u.Jy, spectral_axis=[1, 2, 3] * u.um)
    sb = Spectrum(flux=[1, 2, 3] * u.Jy / u.sr, spectral_axis=[1, 2, 3] * u.um)
    # Initialize physical solid-angle preferences natively (no pix2/sr change).
    helper.load(sb, format='1D Spectrum', data_label='sb')
    uc = helper.plugins['Unit Conversion']._obj
    uc.set_viewer_y_type([helper.viewers['1D Spectrum']._obj.glue_viewer], sync=False)
    uc.spectral_y_type_selected = 'Flux'
    importer = SpectrumImporter(app=helper._app, resolver=helper.loaders['object']._obj,
                                parser=None, input=flux)
    importer.add_to_data_collection(flux, data_label='flux', viewer_select=False)
    return helper, uc, flux, sb


@pytest.mark.parametrize('quantity', ['', 'Flux', 'Surface Brightness'])
def test_creator_quantity_before_data(quantity_setup, quantity, monkeypatch):
    helper, uc, flux, sb = quantity_setup
    creator = helper.new_viewers['1D Spectrum']
    creator.spectral_y_type = quantity
    label = 'sb' if quantity == 'Surface Brightness' else 'flux'
    assert creator.dataset.choices == [label]
    creator.dataset = [label]

    original_setter = uc.set_viewer_y_type
    configured = []

    def configure(viewers, **kwargs):
        assert all(not viewer.state.layers_data for viewer in viewers)
        configured.extend(viewers)
        return original_setter(viewers, **kwargs)

    monkeypatch.setattr(uc, 'set_viewer_y_type', configure)
    result = creator()
    viewer = result._obj.glue_viewer
    assert configured == [viewer]
    assert viewer.data_menu.data_labels_loaded == [label]
    assert uc.viewer_y_type(viewer) == (quantity or 'Flux')
    assert viewer.state.spectral_y_type_sync == (quantity == '')
    assert uc.spectral_y_type_selected == 'Flux'
    assert helper._app.data_collection['sb'].get_component('flux').units == 'Jy / sr'


def test_creator_filters_refresh_on_global_change(quantity_setup):
    helper, uc, flux, sb = quantity_setup
    creator = helper.new_viewers['1D Spectrum']._obj
    assert creator.dataset.choices == ['flux']
    viewer = helper.viewers['1D Spectrum']._obj.glue_viewer
    uc.set_viewer_y_type([viewer], sync=False)
    uc.spectral_y_type_selected = 'Surface Brightness'
    assert creator.dataset.choices == ['sb']
    creator.spectral_y_type = 'Flux'
    assert creator.dataset.choices == ['flux']
    helper._app.hub.broadcast(GlobalDisplayUnitChanged('spectral_y', 'Jy / sr', sender=uc))
    assert creator.dataset.choices == ['flux']


@pytest.mark.parametrize('quantity', ['', 'Flux', 'Surface Brightness'])
def test_importer_creation_quantity(quantity_setup, quantity, monkeypatch):
    helper, uc, flux, sb = quantity_setup
    spec = sb if quantity == 'Surface Brightness' else flux
    importer = SpectrumImporter(app=helper._app, resolver=helper.loaders['object']._obj,
                                parser=None, input=spec)
    api = importer.user_api
    assert api.spectral_y_type == ''
    api.spectral_y_type = quantity
    api.viewer.create_new = '1D Spectrum'
    api.viewer.new_label = 'Created Spectrum'
    api.data_label = 'imported'
    if quantity:
        original_setter = uc.set_viewer_y_type

        def configure(viewers, **kwargs):
            assert all(not viewer.state.layers_data for viewer in viewers)
            return original_setter(viewers, **kwargs)

        monkeypatch.setattr(uc, 'set_viewer_y_type', configure)
    api()
    viewer = helper.viewers['Created Spectrum']._obj.glue_viewer
    assert viewer.data_menu.data_labels_loaded == ['imported']
    assert uc.viewer_y_type(viewer) == (quantity or 'Flux')
    assert viewer.state.spectral_y_type_sync == (quantity == '')
    assert uc.spectral_y_type_selected == 'Flux'
    assert api.viewer.selected == ['Created Spectrum']
    api.data_label = 'imported again'
    api()
    assert len(helper.viewers) == 2
    assert set(viewer.data_menu.data_labels_loaded) == {'imported', 'imported again'}


def test_importer_override_does_not_change_existing_viewer(quantity_setup):
    helper, uc, flux, sb = quantity_setup
    viewer = helper.viewers['1D Spectrum']._obj.glue_viewer
    importer = SpectrumImporter(app=helper._app, resolver=helper.loaders['object']._obj,
                                parser=None, input=sb)
    api = importer.user_api
    api.spectral_y_type = 'Flux'
    assert importer.viewer.choices == [viewer.reference_id]
    api.viewer = [viewer.reference_id]
    api.data_label = 'another sb'
    api()
    assert uc.viewer_y_type(viewer) == 'Surface Brightness'
    assert not viewer.state.spectral_y_type_sync
    assert set(viewer.data_menu.data_labels_loaded) == {'sb', 'another sb'}
    assert len(helper.viewers) == 1


def test_invalid_creation_quantities(quantity_setup):
    helper, uc, flux, sb = quantity_setup
    creator = helper.new_viewers['1D Spectrum']
    importer = SpectrumImporter(app=helper._app, resolver=helper.loaders['object']._obj,
                                parser=None, input=flux)
    for api in (creator, importer.user_api):
        with pytest.raises(ValueError, match='spectral_y_type must be'):
            api.spectral_y_type = 'Invalid'
        assert api.spectral_y_type == ''
    with pytest.raises(ValueError, match='spectral_y_type must be'):
        creator._obj.spectral_y_type_selected = 'Invalid'


def test_first_import_initializes_global_default(deconfigged_helper):
    spec = Spectrum(flux=[1, 2, 3] * u.Jy / u.sr, spectral_axis=[1, 2, 3] * u.um)
    deconfigged_helper.load(spec, format='1D Spectrum')
    uc = deconfigged_helper.plugins['Unit Conversion']._obj
    viewer = deconfigged_helper.viewers['1D Spectrum']._obj.glue_viewer
    assert uc.spectral_y_type_selected == 'Surface Brightness'
    assert uc.viewer_y_type(viewer) == 'Surface Brightness'
    assert viewer.state.spectral_y_type_sync


def test_creator_without_unit_conversion(deconfigged_helper, spectrum1d, monkeypatch):
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label='spectrum')
    original_get = deconfigged_helper._app.get_tray_item_from_name

    def get_plugin(name, *args, **kwargs):
        if name == 'g-unit-conversion':
            raise KeyError(name)
        return original_get(name, *args, **kwargs)

    monkeypatch.setattr(deconfigged_helper._app, 'get_tray_item_from_name', get_plugin)
    creator = Spectrum1DViewerCreator(app=deconfigged_helper._app)
    assert creator.dataset.choices == ['spectrum']
