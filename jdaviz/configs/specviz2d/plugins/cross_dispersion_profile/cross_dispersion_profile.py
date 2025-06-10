import math

import astropy.units as u
import numpy as np
from bqplot import LinearScale
from specreduce.tracing import FlatTrace
from specreduce.utils import measure_cross_dispersion_profile
from traitlets import Bool, Integer, List, Unicode, observe

from jdaviz.core.events import GlobalDisplayUnitChanged
from jdaviz.core.marks import PluginLine, PluginScatter
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (DatasetSelect, PluginTemplateMixin,
                                        PlotMixin)
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               flux_conversion_general)

__all__ = ['CrossDispersionProfile']


@tray_registry('cross-dispersion-profile', label="Cross Dispersion Profile")
class CrossDispersionProfile(PluginTemplateMixin, PlotMixin):

    template_file = __file__, "cross_dispersion_profile.vue"

    uses_active_status = Bool(True).tag(sync=True)

    dataset_items = List().tag(sync=True)
    dataset_selected = Unicode().tag(sync=True)

    trace_items = List().tag(sync=True)
    trace_selected = Unicode().tag(sync=True)

    # pixel on cross dispersion axis where profile will be centered. a FlatTrace
    # at y_pixel will be created to measure the profile.
    y_pixel = Integer().tag(sync=True)

    # pixel on spectral axis to measure profile
    pixel = Integer().tag(sync=True)

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
        self.profile = None

        # override default plot styling
        self.plot.figure.fig_margin = {'top': 60, 'bottom': 60, 'left': 65,
                                       'right': 15}
        self.plot.viewer.axis_y.tick_format = '0.1e'
        self.plot.viewer.axis_y.label_offset = '50px'

    @observe("dataset_selected")
    def _set_defaults(self, event={}):
        """
        When a dataset is selected, re-calculate the default values for pixel
        and the slider limits for selecting row/column where the profile will
        be measured.
        """

        # self.dataset might not exist when app is setting itself up.
        if hasattr(self, "dataset") and self.dataset.selected_obj is not None:
            data = self.dataset.selected_obj
            # default value for 'y_pixel' is middle of cross dispersion axis
            self.y_pixel = math.floor(data.shape[0] / 2)
            # default value for 'pixel' is middle of spectral axis
            self.pixel = math.floor(data.shape[1] / 2)
            # slider limits
            self.max_y_pix = data.shape[0]
            self.max_pix = data.shape[1]
            # default use_full_width=True
            self.use_full_width = True
            # set appropriate default 'width' if use_full_width=False
            self.width = data.shape[0]

    def _on_display_units_changed(self, event={}):
        """
        On flux display unit change from Unit Conversion plugin, re-compute
        profile in new unit and update plot.

        Note: re-measure profile in native data units rather than converting
        currently computed profile so repeated conversions don't accumulate
        precision errors.
        """
        if event.axis == 'flux':
            if self.flux_display_unit == event.unit:
                return
            self.flux_display_unit = event.unit.to_string()

        if event.axis == 'spectral':
            if self.sa_display_unit == event.unit:
                return
            self.sa_display_unit = event.unit.to_string()

            # update marks in 1d viewer
            data = self.dataset.selected_obj
            if hasattr(data, 'wcs') and self.sa_display_unit != '':
                wcs = self.dataset.selected_obj.wcs
                wav = wcs.pixel_to_world(self.pixel)
                wav = wav.to(u.Unit(self.sa_display_unit), u.spectral()).value
                self.marks['1d']['pix'].update_xy([wav, wav], [0, 1])
                self.marks['1d']['pix'].visible = self.is_active

        # re-compute profile and update plot to new units
        self.measure_cross_dispersion_profile(update_plot=True)

    @property
    def marks(self):
        """
        Access the marks created by this plugin in the spectrum-2d-viewer.
        """
        if self._marks:
            return self._marks

        if not self._tray_instance:
            return {}

        v2d = self.app.get_viewer_by_id('specviz2d-0')
        v1d = self.app.get_viewer_by_id('specviz2d-1')

        if not v2d.state.reference_data:
            return {}

        self._marks = {'2d': {'pix': PluginLine(v2d,
                                                visible=self.is_active,
                                                line_style='dashed'),
                              'y_pix': PluginScatter(v2d, marker='diamond',
                                                     stroke_width=1)},
                       '1d': {'pix': PluginLine(v1d,
                                                x=[0, 0], y=[0, 1],
                                                scales={'x': v1d.scales['x'],
                                                        'y': LinearScale(min=0,
                                                                         max=1)},
                                                visible=self.is_active,
                                                line_style='dashed')}}

        v2d.figure.marks = v2d.figure.marks + list(self._marks['2d'].values())
        v1d.figure.marks = v1d.figure.marks + list(self._marks['1d'].values())

        return self._marks

    @observe('dataset_selected', 'is_active', 'pixel', 'y_pixel', 'width', 'use_full_width')
    def _pixel_selected_mark(self, event={}):
        """
        Update drawn marks (synced vertical lines in 2d and 1d spectrum viewers)
        for current selected pixel, when changed. If y_pixel is used to denote
        the center of the profile on the cross dispersion axis (rather than using
        a trace object exported from the spectral extraction plugin), then a
        scatter mark from this plugin will be drawn to show the row used as the
        midpoint of the profile.
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

            # plot line in 1d viewer when possible
            if hasattr(data, 'wcs') and self.sa_display_unit != '':
                wcs = self.dataset.selected_obj.wcs
                wav = wcs.pixel_to_world(self.pixel)
                wav = wav.to(u.Unit(self.sa_display_unit), u.spectral()).value
                self.marks['1d']['pix'].update_xy([wav, wav], [0, 1])
                self.marks['1d']['pix'].visible = self.is_active

    @observe('pixel', 'y_pixel', 'is_active', 'width', 'use_full_width')
    def measure_cross_dispersion_profile(self, update_plot=True):

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
        eqv = all_flux_unit_conversion_equivs(data.meta.get('PIXAR_SR', 1.0),
                                              data.spectral_axis)
        profile = flux_conversion_general(profile.value, profile.unit,
                                          self.flux_display_unit, eqv)

        self.profile = profile

        if update_plot:
            self.update_plot()

    def update_plot(self):
        """Update plot with current self.profile."""

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
        # include wavelength in plot title, if possible
        if hasattr(data, 'wcs'):  # also plot line in spectrum viewer
            wcs = self.dataset.selected_obj.wcs
            loc = round(wcs.pixel_to_world(self.pixel).value, 3)
            title += f' ({loc} {self.sa_display_unit})'
        self.plot.figure.title = title

        self.plot.figure.axes[1].label = f'Value ({self.flux_display_unit})'

        self.plot_available = True
