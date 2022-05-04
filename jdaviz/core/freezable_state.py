from glue.viewers.profile.state import ProfileViewerState
from glue_jupyter.bqplot.image.state import BqplotImageViewerState

from echo import delay_callback
import numpy as np


class FreezableState():
    _frozen_state = []

    def __setattr__(self, k, v):
        if k[0] == '_' or k not in self._frozen_state:
            super().__setattr__(k, v)
        elif getattr(self, k) is None:
            # still allow Nones to be updated to initial values
            super().__setattr__(k, v)


class FreezableProfileViewerState(ProfileViewerState, FreezableState):
    x_min_default = -np.inf
    x_max_default = np.inf
    y_min_default = -np.inf
    y_max_default = np.inf

    def _reset_x_limits(self, *event, reset=False):

        # NOTE: we don't use AttributeLimitsHelper because we need to avoid
        # trying to get the minimum of *all* the world coordinates in the
        # dataset. Instead, we use the same approach as in the layer state below
        # and in the case of world coordinates we use online the spine of the
        # data.

        if self.reference_data is None or self.x_att_pixel is None:
            return

        if reset:
            return super()._reset_x_limits(*event)

        with delay_callback(self, 'x_min', 'x_max'):
            self.x_min = self.x_min_default
            self.x_max = self.x_max_default

    def _reset_y_limits(self, *event, reset=False):
        if reset:
            return super()._reset_y_limits(*event)
        if self.normalize:
            return super()._reset_y_limits(*event)
        else:
            y_min, y_max = self.y_min_default, self.y_max_default
            with delay_callback(self, 'y_min', 'y_max'):
                if y_max > y_min:
                    self.y_min = y_min
                    self.y_max = y_max
                else:
                    self.y_min = 0
                    self.y_max = 1


class FreezableBqplotImageViewerState(BqplotImageViewerState, FreezableState):
    pass
