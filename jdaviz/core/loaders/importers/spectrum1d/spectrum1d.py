import numpy as np
from astropy.nddata import StdDevUncertainty
from astropy import units as u
from asdf import AsdfFile
from specutils import Spectrum
from traitlets import Bool, List, Unicode

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import (BaseImporterToDataCollection,
                                           _spectrum_assign_component_type)
from jdaviz.core.template_mixin import SelectFileExtensionComponent


__all__ = ['SpectrumImporter']


def asdf_is_roman_ext(item):
    return all(k in item for k in ["unit_wl", "unit_flux"])

@loader_importer_registry('1D Spectrum')
class SpectrumImporter(BaseImporterToDataCollection):
    template_file = __file__, "../to_dc_with_label.vue"

    # HDUList-specific options
    input_hasexts = Bool(False).tag(sync=True)
    extension_items = List().tag(sync=True)
    extension_selected = Unicode().tag(sync=True)

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

        self.input_hasexts = isinstance(self.input, AsdfFile)
        if self.input_hasexts:
            ext_options = [{'label': f"{ind}: {k}",
                            'name': k,
                            'name_ver': k,
                            'index': ind,
                            'obj': ext}
                           for ind, (k, ext) in enumerate(self.input['roman']['data'].items())]
            # TODO: support or disable multiselect
            self.extension = SelectFileExtensionComponent(self,
                                                          items='extension_items',
                                                          selected='extension_selected',
                                                          manual_options=ext_options,
                                                          filters=[asdf_is_roman_ext])

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '1D Spectrum', 'reference': 'spectrum-1d-viewer'}]

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz', 'specviz2d', 'cubeviz'):
            # cubeviz allowed for cubeviz.specviz.load_data support
            # NOTE: temporary during deconfig process
            return False
        if isinstance(self.input, Spectrum) and self.input.flux.ndim == 1:
            return True
        if isinstance(self.input, AsdfFile):
            # Roman: valid as long as there is at least one valid extension
            if ('roman' in self.input.tree and
                    len([item for item in self.input['roman']['data']
                         if asdf_is_roman_ext(item)])):
                return True
        return False

    @property
    def output(self):
        # if the entire uncert. array is Nan and the data is not, model fitting won't
        # work (more generally, if uncert[i] is nan/inf and flux[i] is not, fitting will
        # fail, but just deal with the all nan case here since it is straightforward).
        # set uncerts. to None if they are all nan/inf, and display a warning message.
        data = self.input

        if self.input_hasexts:
            # for now assume Roman ASDF
            def _to_unit(x):
                """Coerce str/bytes/Unit to astropy.units.Unit."""
                if isinstance(x, bytes):
                    x = x.decode()
                return u.Unit(x)

            roman = self.input["roman"]
            meta = roman["meta"]
            data = roman["data"]
            spectrum = self.extension.selected_obj
            wavelength = np.asarray(spectrum["wl"])
            flux = np.asarray(spectrum["flux"])
            wl_unit = _to_unit(meta["unit_wl"])
            flux_unit = _to_unit(meta["unit_flux"])

            flux_error = spectrum.get("flux_error", None)
            variance = spectrum.get("var", None)
            uncertainty = None
            if flux_error is not None:
                uncertainty = StdDevUncertainty(np.asarray(flux_error) * flux_unit)
            elif variance is not None:
                var = np.asarray(variance) * (flux_unit ** 2)
                var = np.where(np.asarray(var.value) < 0, np.nan, var.value) * var.unit
                uncertainty = StdDevUncertainty(np.sqrt(var))
            else:
                uncertainty = None

            spectrum1d = Spectrum(
                flux=flux * flux_unit,
                spectral_axis=wavelength * wl_unit,
                uncertainty=uncertainty
            )
            return spectrum1d

        if data.uncertainty is not None:
            uncerts_finite = np.isfinite(data.uncertainty.array)
            if not np.any(uncerts_finite):
                data.uncertainty = None
                set_nans_to_none = True

                if set_nans_to_none:
                    # alert user that we have changed their all-nan uncertainty array to None
                    msg = 'All uncertainties are nonfinite, replacing with uncertainty=None.'
                    self.app.hub.broadcast(SnackbarMessage(msg, color="warning", sender=self.app))
        return data

    def assign_component_type(self, comp_id, comp, units, physical_type):
        return _spectrum_assign_component_type(comp_id, comp, units, physical_type)
