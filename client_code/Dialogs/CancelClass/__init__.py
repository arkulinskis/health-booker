from anvil import *

from ._anvil_designer import CancelClassTemplate
from ... import hb, state


class CancelClass(CancelClassTemplate):
    """Cancel a class: everyone booked or waiting gets their credit back and this message (cancel_class)."""

    def __init__(self, klass=None, **properties):
        super().__init__(**properties)
        self.c: dict = klass or {}
        hb.text(self.dom_nodes["title"], "Cancel %s?" % self.c.get("title"))
        hb.text(self.dom_nodes["lead"], "Everyone booked (%s) and waiting (%s) gets their credit back and this message:" % (
            self.c.get("booked", 0), self.c.get("waiting", 0)))
        state.set_control_attr(self.note_box, "aria-label", "Message to the people booked")

    @handle("yes_button", "click")
    def yes_button_click(self, **event_args):
        r = state.call("cancel_class", self.c["id"], self.note_box.text or "")
        if r:
            state.toast("Cancelled. %s told." % hb.plural(r.get("notified") or 0, "person", "people"), "ok")
            self.raise_event("x-close-alert", value=True)

    @handle("keep_button", "click")
    def keep_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)
