import math

import astropy.units as u
import numpy as np
from bqplot import LinearScale
from specreduce.tracing import FlatTrace
from specreduce.utils import measure_cross_dispersion_profile
from traitlets import Bool, Float, Integer, List, Unicode, observe

from jdaviz.core.events import GlobalDisplayUnitChanged
from jdaviz.core.marks import PluginLine, PluginScatter
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (DatasetSelect, PluginTemplateMixin,
                                        PlotMixin)
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               flux_conversion_general)
from jdaviz.core.user_api import PluginUserApi

__all__ = ['CrossDispersionProfile']


@tray_registry('cross-dispersion-profile', label="Cross Dispersion Profile")
class CrossDispersionProfile(PluginTemplateMixin, PlotMixin):
    """
    The Cross Dispersion Profile plugin allows for visualizaion of the
    cross-dispersion profile of 2d spectra, at a specified wavelength / pixel
    and window.

    The following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    """

    template_file = __file__, "cross_dispersion_profile.vue"

    uses_active_status = Bool(True).tag(sync=True)

    dataset_items = List().tag(sync=True)
    dataset_selected = Unicode().tag(sync=True)

    # pixel on cross dispersion axis where profile will be centered. a FlatTrace
    # at y_pixel will be created to measure the profile.
    y_pixel = Integer().tag(sync=True)

    # pixel on spectral axis to measure profile
    pixel = Integer().tag(sync=True)
    wav = Float(4.0).tag(sync=True)  # corresponding wavelength, if available

    # set maximum values for slider limits
    max_pix = Integer().tag(sync=True)
    max_y_pix = Integer().tag(sync=True)

    # traitlets for size of window in cross-dispersion axis. If 'use_full_width'
    # is True, then the full cross dispersion axis around y_pixel will be used.
    # If False, then 'width' will be used.
    use_full_width = Bool(True).tag(sync=True)
    width = Integer().tag(sync=True)

    # app-wide flux display unit. 'profile' will always be in this unit
    flux_display_unit = Unicode("").tag(sync=True)

    # app-wide unit for spectral axis, for plot title
    sa_display_unit = Unicode("").tag(sync=True)

    plot_available = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._marks = {}

        # description displayed under plugin title in tray
        self._plugin_description = 'Visualize cross-dispersion profile.'

        self.dataset = DatasetSelect(self,
                                     'dataset_items',
                                     'dataset_selected',
                                     filters=['layer_in_spectrum_2d_viewer',
                                              'not_trace'])

        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._on_display_units_changed)

        # attribute to access computed profile, will be a quantity array
        self._profile = None

        # override default plot styling
        self.plot.figure.fig_margin = {'top': 60, 'bottom': 60, 'left': 65,
                                       'right': 15}
        self.plot.viewer.axis_y.tick_format = '0.1e'
        self.plot.viewer.axis_y.label_offset = '50px'

    @property
    def user_api(self):
        expose = ('dataset', 'pixel', 'y_pixel', 'use_full_width', 'width',
                  'profile')
        return PluginUserApi(self, expose=expose)

    @observe("dataset_selected")
    def _set_defaults(self, event={}):
        """
        When a dataset is selected, re-calculate the default values for pixel,
        y_pixel, width, and the slider limits for selecting row/column where
        the profile will be measured.
        """
        # self.dataset might not exist when app is setting itself up.
        if hasattr(self, "dataset") and self.dataset.selected_obj is not None:
            data = self.dataset.selected_obj
            # default value for 'y_pixel' is middle of cross dispersion axis
            self.y_pixel = math.floor(data.shape[0] / 2)
            # default value for 'pixel' is middle of spectral axis
            self.pixel = math.floor(data.shape[1] / 2)
            self._pixel_to_wav()  # also set corresponding wavelength
            # slider limits
            self.max_y_pix = data.shape[0]
            self.max_pix = data.shape[1]
            # default use_full_width=True
            self.use_full_width = True
            # set appropriate default 'width' if use_full_width=False
            self.width = data.shape[0]

    @observe('pixel')
    def _pixel_to_wav(self, event={}):
        """
        Calculate the corresponding wavelength for ``pixel``, if wcs is present,
        when ``pixel`` is changed.
        """
        data = self.dataset.selected_obj
        if data is not None:
            if hasattr(data, 'wcs') and self.sa_display_unit != '':
                wcs = self.dataset.selected_obj.wcs
                wav = wcs.pixel_to_world(self.pixel)
                self.wav = wav.to(u.Unit(self.sa_display_unit), u.spectral()).value

    def _on_display_units_changed(self, event={}):
        """
        On flux display unit change from Unit Conversion plugin, re-compute
        profile in new unit and update plot.

        Note: re-measure profile in native data units rather than converting
        currently computed profile so repeated conversions don't accumulate
        precision errors.
        """
        if event.axis == 'flux':
            if self.flux_display_unit != event.unit:
                self.flux_display_unit = event.unit.to_string()

        if event.axis == 'spectral':
            if self.sa_display_unit != event.unit:
                self.sa_display_unit = event.unit.to_string()

    @property
    def profile(self):
        return self._profile

    @property
    def marks(self):
        """
        Access the marks created by this plugin in the spectrum-2d-viewer.
        """
        if self._marks:
            return self._marks

        if not self._tray_instance:
            return {}

        v2d = self.spectrum_2d_viewers[0]
        v1d = self.spectrum_1d_viewers[0]

        if not v2d.state.reference_data:
            return {}

        self._marks = {'2d': {'pix': PluginLine(v2d,
                                                visible=self.is_active,
                                                line_style='solid'),
                              'y_pix': PluginScatter(v2d, marker='diamond',
                                                     stroke_width=1)},
                       '1d': {'pix': PluginLine(v1d,
                                                x=[0, 0], y=[0, 1],
                                                scales={'x': v1d.scales['x'],
                                                        'y': LinearScale(min=0,
                                                                         max=1)},
                                                visible=self.is_active,
                                                line_style='solid')}}

        v2d.figure.marks = v2d.figure.marks + list(self._marks['2d'].values())
        v1d.figure.marks = v1d.figure.marks + list(self._marks['1d'].values())

        return self._marks

    @observe('dataset_selected', 'is_active', 'pixel', 'y_pixel', 'width', 'use_full_width', 'wav')
    def _pixel_selected_mark(self, event={}):
        """
        Update drawn marks (synced vertical lines in 2d and 1d spectrum viewers,
        scatter mark to mark center of profile on y axis) for current selected
        pixel, when any relevant parameter is changed or plugin is made active.
        """

        data = self.dataset.selected_obj
        if data is not None:

            if self.use_full_width is True:
                ymax = data.shape[0]
                ymin = 0
            else:
                ymax = int(self.y_pixel + (self.width/2))
                ymin = int(self.y_pixel - (self.width/2))

            self.marks['2d']['pix'].update_xy(np.full(data.shape[1],
                                              self.pixel), range(ymin, ymax))
            self.marks['2d']['pix'].visible = self.is_active
            self.marks['2d']['y_pix'].update_xy((self.pixel, self.pixel),
                                                (self.y_pixel, self.y_pixel))
            self.marks['2d']['y_pix'].visible = self.is_active

            # plot line in 1d viewer when possible, unit conversion is handled
            # inside of Marks so we don't need to convert the limits here
            if hasattr(data, 'wcs') and self.sa_display_unit != '':
                self.marks['1d']['pix'].update_xy([self.wav, self.wav], [0, 1])
                self.marks['1d']['pix'].visible = self.is_active

    @observe('dataset_selected', 'pixel', 'y_pixel', 'is_active', 'width', 'use_full_width')
    def measure_cross_dispersion_profile(self, update_plot=True):
        """
        Measure the cross-dispersion profile.

        Calculates the cross-dispersion profile for the currently
        selected dataset at column ``pixel``. If ``use_full_width`` is True,
        the profile is computed over the entire detector width, otherwise,
        a user-defined ``width`` and center ``y_pixel`` are used. The profile
        is returned and plotted in the app-wide flux display unit, as set in
        the Unit Conversion plugin.

        Parameters
        ----------
        update_plot : bool, optional
            If True (default), update plugin plot with computed profile, if the
            plugin is active.
        """

        data = self.dataset.selected_obj
        if data is None:
            return

        if self.use_full_width:
            width = None
        else:
            width = self.width

        # create a FlatTrace at y_pixel
        trace = FlatTrace(data, self.y_pixel)

        profile = measure_cross_dispersion_profile(data,
                                                   trace=trace,
                                                   crossdisp_axis=0,
                                                   width=width,
                                                   pixel=self.pixel,
                                                   pixel_range=None,
                                                   align_along_trace=False)

        # convert profile, which was computed in data units, to display unit
        if self.sa_display_unit != '':
            eqv = all_flux_unit_conversion_equivs(data.meta.get('PIXAR_SR', 1.0),
                                                  self.wav * u.Unit(self.sa_display_unit))
            profile = flux_conversion_general(profile.value, profile.unit,
                                              self.flux_display_unit, eqv)

        self._profile = profile

        if update_plot and self.is_active:
            self.update_plot()

    def update_plot(self):
        """Update plugin plot with self.profile."""

        data = self.dataset.selected_obj
        if data is None:
            return

        x = np.arange(len(self.profile))

        if not self.use_full_width:
            # translate x-axis of plot to image y-axis coordinates so plot
            # is centered on y_pixel
            x += int(self.y_pixel - (self.width / 2))

        self.plot._update_data('profile', x=x, y=self.profile, reset_lims=True)
        self.plot.update_style('profile', line_visible=True, color='gray',
                               size=32)

        title = f'Cross dispersion profile for pixel {self.pixel}'
        # include wavelength in plot title, if available
        if hasattr(data, 'wcs'):  # also plot line in spectrum viewer
            wcs = self.dataset.selected_obj.wcs
            loc = round(wcs.pixel_to_world(self.pixel).value, 3)
            title += f' ({loc} {self.sa_display_unit})'
        self.plot.figure.title = title

        self.plot.figure.axes[1].label = f'Value ({self.flux_display_unit})'

        self.plot_available = True
