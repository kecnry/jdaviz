from traitlets import Unicode, observe, validate

from jdaviz.configs.specviz.plugins.viewers import Spectrum1DViewer
from jdaviz.core.events import GlobalDisplayUnitChanged
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry
from jdaviz.core.user_api import ViewerCreatorUserApi


__all__ = ['Spectrum1DViewerCreator']


@viewer_creator_registry('1D Spectrum', overwrite=True)
class Spectrum1DViewerCreator(BaseViewerCreator):
    template_file = __file__, "spectrum1d.vue"
    spectral_y_type_selected = Unicode('').tag(sync=True)

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_spectrum', self._compatible_quantity]
        self.viewer_label_default = '1D Spectrum'
        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._refresh_quantity_filter)

    @property
    def user_api(self):
        return ViewerCreatorUserApi(self, expose=['spectral_y_type'])

    @property
    def spectral_y_type(self):
        """New viewer quantity: '', 'Flux', or 'Surface Brightness'.

        The empty string follows the app default; explicit choices disable sync.
        """
        return self.spectral_y_type_selected

    @spectral_y_type.setter
    def spectral_y_type(self, value):
        self.spectral_y_type_selected = value

    @validate('spectral_y_type_selected')
    def _validate_quantity(self, proposal):
        if proposal['value'] not in ('', 'Flux', 'Surface Brightness'):
            raise ValueError("spectral_y_type must be '', 'Flux', or 'Surface Brightness'")
        return proposal['value']

    def _unit_conversion(self):
        try:
            return self._app.get_tray_item_from_name('g-unit-conversion')
        except KeyError:
            return None

    def _compatible_quantity(self, data):
        uc = self._unit_conversion()
        return uc is None or not uc.data_y_error(
            data, quantity=self.spectral_y_type_selected or uc.spectral_y_type_selected)

    @observe('spectral_y_type_selected')
    def _refresh_quantity_filter(self, *args):
        if hasattr(self, 'dataset'):
            self.dataset._update_items()

    def _configure_new_viewer(self, viewer):
        uc = self._unit_conversion()
        if uc is not None:
            uc.set_viewer_y_type([viewer], quantity=self.spectral_y_type_selected or None,
                                 sync=not bool(self.spectral_y_type_selected))

    @property
    def viewer_class(self):
        return Spectrum1DViewer
