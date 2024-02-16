import threading
import time
import warnings

import numpy as np
import astropy.units as u
from astropy.units import UnitsWarning
from astropy.utils.decorators import deprecated
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.bqplot.profile import BqplotProfileView
from traitlets import Any, Bool, Int, Unicode, observe
from specutils.spectra.spectrum1d import Spectrum1D

from jdaviz.configs.cubeviz.plugins.viewers import CubevizImageView
from jdaviz.core.events import (AddDataMessage, SliceToolStateMessage,
                                SliceSelectSliceMessage, SliceValueUpdatedMessage,
                                NewViewerMessage, ViewerAddedMessage, ViewerRemovedMessage,
                                GlobalDisplayUnitChanged)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.core.user_api import PluginUserApi

__all__ = ['Slice']


@tray_registry('cubeviz-slice', label="Slice", viewer_requirements='spectrum')
class Slice(PluginTemplateMixin):
    """
    See the :ref:`Slice Plugin Documentation <slice>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``slice``
      Current slice number.
    * ``value``
      Value (wavelength or frequency) of the current slice.  When setting this directly, it will
      update automatically to the value corresponding to the nearest slice.
    * ``show_indicator``
      Whether to show indicator in spectral viewer when slice tool is inactive.
    * ``show_value``
      Whether to show slice value in label to right of indicator.
    """
    _cube_viewer_cls = CubevizImageView
    _cube_viewer_default_label = 'flux-viewer'
    cube_viewer_exists = Bool(True).tag(sync=True)

    template_file = __file__, "slice.vue"
    slice = Any(0).tag(sync=True)
    value = Any(-1).tag(sync=True)
    value_label = Unicode("Wavelength").tag(sync=True)
    value_unit = Any("").tag(sync=True)

    min_slice = Int(0).tag(sync=True)
    max_slice = Int(100).tag(sync=True)
    wait = Int(200).tag(sync=True)

    show_indicator = Bool(True).tag(sync=True)
    show_value = Bool(True).tag(sync=True)

    is_playing = Bool(False).tag(sync=True)
    play_interval = Int(200).tag(sync=True)  # milliseconds

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._watched_viewers = []
        self._indicator_viewers = []
        self._x_all = None
        self._player = None

        # initialize watching existing viewers WITH data (if initializing the plugin after data
        # already exists - otherwise the AddDataMessage will handle watching image viewers once
        # data is available)
        for id, viewer in self.app._viewer_store.items():
            if isinstance(viewer, BqplotProfileView) or len(viewer.data()):
                self._watch_viewer(viewer, True)

        # Subscribe to requests from the helper to change the slice across all viewers
        self.session.hub.subscribe(self, SliceSelectSliceMessage,
                                   handler=self._on_select_slice_message)

        # Listen for add data events. **Note** this should only be used in
        #  cases where there is a specific type of data expected and arbitrary
        #  viewers are not expected to be created. That is, the expected data
        #  in _all_ viewers should be uniform.
        self.session.hub.subscribe(self, AddDataMessage,
                                   handler=self._on_data_added)

        # update internal value (wavelength/frequency) when x display unit is changed
        # so that the current slice number is preserved
        self.session.hub.subscribe(self, GlobalDisplayUnitChanged,
                                   handler=self._on_global_display_unit_changed)

        self.hub.subscribe(self, ViewerAddedMessage, handler=self._check_if_cube_viewer_exists)
        self.hub.subscribe(self, ViewerRemovedMessage, handler=self._check_if_cube_viewer_exists)
        self._check_if_cube_viewer_exists()

    @property
    @deprecated(since="3.9", alternative="value")
    def wavelength(self):
        return self.user_api.value

    @property
    @deprecated(since="3.9", alternative="value_unit")
    def wavelength_unit(self):
        return self.user_api.value_unit

    @property
    @deprecated(since="3.9", alternative="show_value")
    def show_wavelength(self):
        return self.user_api.show_value

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('slice', 'wavelength', 'value',
                                           'show_indicator', 'show_wavelength', 'show_value'))

    @property
    def slice_indicator(self):
        return self.spectrum_viewer.slice_indicator

    def _check_if_cube_viewer_exists(self, *args):
        for viewer in self.app._viewer_store.values():
            if isinstance(viewer, self._cube_viewer_cls):
                self.cube_viewer_exists = True
                return
        self.cube_viewer_exists = False

    def vue_create_cube_viewer(self, *args):
        self.app._on_new_viewer(NewViewerMessage(self._cube_viewer_cls, data=None, sender=self.app),
                                vid=self._cube_viewer_default_label,
                                name=self._cube_viewer_default_label)

        dc = self.app.data_collection
        for data in dc:
            if data.ndim == 3:
                # only load the first cube-like data
                self.app.set_data_visibility(self._cube_viewer_default_label, data.label, True)
                break

    def _watch_viewer(self, viewer, watch=True):
        if isinstance(viewer, BqplotImageView):
            if watch and viewer not in self._watched_viewers:
                self._watched_viewers.append(viewer)
                viewer.state.add_callback('slices',
                                          self._viewer_slices_changed)
            elif not watch and viewer in self._watched_viewers:
                viewer.state.remove_callback('slices',
                                             self._viewer_slices_changed)
                self._watched_viewers.remove(viewer)
        elif isinstance(viewer, BqplotProfileView) and watch:
            if self._x_all is None and len(viewer.data()):
                # cache values (wavelengths/freqs) so that value <> slice conversion is efficient
                self._update_data(viewer.data()[0].spectral_axis)

            if viewer not in self._indicator_viewers:
                self._indicator_viewers.append(viewer)
                # if the units (or data) change, we need to update internally
                viewer.state.add_callback("reference_data",
                                          self._update_reference_data)

    def _on_data_added(self, msg):
        if isinstance(msg.viewer, BqplotImageView):
            if len(msg.data.shape) == 3:
                self.max_slice = msg.data.shape[-1] - 1  # Same as i_end in Export Plot plugin
                self._watch_viewer(msg.viewer, True)
                self._set_viewer_to_slice(msg.viewer, int(self.slice))

        elif isinstance(msg.viewer, BqplotProfileView):
            self._watch_viewer(msg.viewer, True)

    def _update_reference_data(self, reference_data):
        if reference_data is None:
            return  # pragma: no cover
        self._update_data(reference_data.get_object(cls=Spectrum1D).spectral_axis)

    def _update_data(self, x_all):
        self._x_all = x_all.value

        if self.value == -1:
            if len(x_all):
                # initialize at middle of cube
                self.slice = int(len(x_all)/2)
            else:
                # leave in the pre-init state and don't update the value/slice
                return

        # Also update unit when data is updated
        self.value_unit = x_all.unit.to_string()

        # force value (wavelength/frequency) to update from the current slider slice
        self._on_slider_updated({'new': self.slice})

        # update data held inside slice indicator and force reverting to original active status
        self.slice_indicator._update_data(x_all)

    def _viewer_slices_changed(self, value):
        # the slices attribute on the viewer state was changed,
        # so we'll update the slider to match which will trigger
        # the slider observer (_on_slider_updated) and sync across
        # any other applicable viewers
        if len(value) == 3:
            self.slice = float(value[-1])

    def _on_select_slice_message(self, msg):
        # NOTE: by setting the slice index, the observer (_on_slider_updated)
        # will sync across all viewers and update the value (wavelength/frequency)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UnitsWarning)
            if msg.slice is not None:
                self.slice = msg.slice
            elif msg.value is not None:
                self.value = msg.value

    @property
    def slice_axis(self):
        return 'spectral'

    def _on_global_display_unit_changed(self, msg):
        if msg.axis != self.slice_axis:
            return
        prev_unit = self.value_unit
        # original unit during init can be blank or deg (before axis is set correctly)
        if self._x_all is None or prev_unit in ('deg', ''):
            return
        self._update_data((self._x_all * u.Unit(prev_unit)).to(msg.unit, u.spectral()))

    @observe('value')
    def _on_value_updated(self, event):
        # convert to float (JS handles stripping any invalid characters)
        try:
            value = float(event.get('new'))
        except ValueError:
            # do not accept changes, we'll revert via the slider
            # since this @change event doesn't have access to
            # the old value, and self.value already updated
            # via the v-model
            self._on_slider_updated({'new': self.slice})
            return

        # NOTE: by setting the index, this should recursively update the
        # value (wavelength/frequency) to the nearest applicable value in _on_slider_updated
        self.slice = int(np.argmin(abs(value - self._x_all)))

    @observe('show_indicator', 'show_value')
    def _on_setting_changed(self, event):
        msg = SliceToolStateMessage({event['name']: event['new']}, sender=self)
        self.session.hub.broadcast(msg)

    def _set_viewer_to_slice(self, viewer, value):
        viewer.state.slices = (0, 0, value)

    @observe('slice')
    def _on_slider_updated(self, event):
        if self._x_all is None:
            return

        value = int(event.get('new', int(len(self._x_all)/2))) % (int(self.max_slice) + 1)

        self.value = self._x_all[value]

        for viewer in self._watched_viewers:
            self._set_viewer_to_slice(viewer, value)
        for viewer in self._indicator_viewers:
            if hasattr(viewer, 'slice_indicator'):
                viewer.slice_indicator.slice = value

        self.hub.broadcast(SliceValueUpdatedMessage(slice=value,
                                                    value=self.value,
                                                    value_unit=self.value_unit,
                                                    sender=self))

    def vue_goto_first(self, *args):
        if self.is_playing:
            return
        self._on_slider_updated({'new': self.min_slice})

    def vue_goto_last(self, *args):
        if self.is_playing:
            return
        self._on_slider_updated({'new': self.max_slice})

    def vue_play_next(self, *args):
        if self.is_playing:
            return
        self._on_slider_updated({'new': self.slice + 1})

    def _player_worker(self):
        ts = float(self.play_interval) * 1e-3  # ms to s
        while self.is_playing:
            self._on_slider_updated({'new': self.slice + 1})
            time.sleep(ts)

    def vue_play_start_stop(self, *args):
        if self.is_playing:  # Stop
            if self._player:
                if self._player.is_alive():
                    self._player.join(timeout=0)
                self._player = None
            self.is_playing = False
            return

        if self._x_all is None:
            return

        # Start
        self.is_playing = True
        self._player = threading.Thread(target=self._player_worker)
        self._player.start()
