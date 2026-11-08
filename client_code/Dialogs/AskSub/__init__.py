from anvil import *

from ._anvil_designer import AskSubTemplate
from ... import state


class AskSub(AskSubTemplate):
    """A teacher asks colleagues to cover a class (request_sub). Closes with True when sent."""

    def __init__(self, class_id=None, **properties):
        super().__init__(**properties)
        self.class_id = class_id

    @handle("send_button", "click")
    def send_button_click(self, **event_args):
        if state.call("request_sub", self.class_id, self.reason_box.text or ""):
            state.toast("Sent to your colleagues.", "ok")
            self.raise_event("x-close-alert", value=True)

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)
