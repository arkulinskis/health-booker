from anvil import *

from ._anvil_designer import MarkPaidTemplate
from ... import state


class MarkPaid(MarkPaidTemplate):
    """The desk marks a pass paid (mark_paid) with how it was paid. Closes with True when done."""

    def __init__(self, pass_id=None, **properties):
        super().__init__(**properties)
        self.pass_id = pass_id

    def _paid(self, method):
        if state.call("mark_paid", self.pass_id, method):
            state.toast("Marked paid.", "ok")
            self.raise_event("x-close-alert", value=True)

    @handle("card_button", "click")
    def card_button_click(self, **event_args):
        self._paid("card")

    @handle("cash_button", "click")
    def cash_button_click(self, **event_args):
        self._paid("cash")

    @handle("etransfer_button", "click")
    def etransfer_button_click(self, **event_args):
        self._paid("e-transfer")

    @handle("comp_button", "click")
    def comp_button_click(self, **event_args):
        self._paid("comp")

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)
