from anvil import *

from ._anvil_designer import PauseTemplate
from ... import state


class Pause(PauseTemplate):
    """Pause a membership for 1-4 weeks (pause_pass). Closes with True when paused."""

    def __init__(self, pass_id=None, **properties):
        super().__init__(**properties)
        self.pass_id = pass_id

    def _pause(self, weeks):
        if state.call("pause_pass", self.pass_id, weeks):
            state.toast("Paused. Enjoy the break.", "ok")
            self.raise_event("x-close-alert", value=True)

    @handle("w1", "click")
    def w1_click(self, **event_args):
        self._pause(1)

    @handle("w2", "click")
    def w2_click(self, **event_args):
        self._pause(2)

    @handle("w3", "click")
    def w3_click(self, **event_args):
        self._pause(3)

    @handle("w4", "click")
    def w4_click(self, **event_args):
        self._pause(4)

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)
