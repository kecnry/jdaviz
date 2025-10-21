import numpy as np
from astropy.nddata import StdDevUncertainty
from astropy import units as u
from specutils import Spectrum

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import (BaseImporterToDataCollection,
                                           SpectrumInputExtensionsMixin)
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['SpectrumImporter']


@loader_importer_registry('1D Spectrum')
class SpectrumImporter(BaseImporterToDataCollection, SpectrumInputExtensionsMixin):
    template_file = __file__, "../to_dc_with_label.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'specviz':
            self.data_label_default = '1D Spectrum'
        elif self.app.config == 'specviz2d':
            self.data_label_default = '1D Spectrum'
        else:
            self.data_label_default = '1D Spectrum'

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '1D Spectrum', 'reference': 'spectrum-1d-viewer'}]

    @property
    def user_api(self):
        expose = []
        for extension in ('extension', 'unc_extension', 'mask_extension'):
            if len(getattr(self, extension).choices):
                expose += [extension]
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz', 'specviz2d', 'cubeviz'):
            # cubeviz allowed for cubeviz.specviz.load_data support
            # NOTE: temporary during deconfig process
            return False
        try:
            sp = self.spectrum
        except Exception:
            return False
        if sp.flux.ndim != 1:
            return False
        try:
            self.output
        except Exception:
            return False
        return True
