from anvil import *

from ._anvil_designer import AskKindnessTemplate
from ... import hb, state

REASONS = [("Sick", "Sick"), ("Emergency", "Emergency"), ("Work", "Work ran late"), ("Transport", "Transport"), ("Other", "Something else")]


class AskKindness(AskKindnessTemplate):
    """Ask a studio to forgive a late cancel or no-show (ask_kindness): a reason chip + an optional note.
    Closes with True when the request was sent."""

    def __init__(self, booking=None, **properties):
        super().__init__(**properties)
        self.b: dict = booking or {}
        c: dict = self.b.get("class") or {}
        studio = (c.get("studio") or {}).get("name") or "the studio"
        kind = "no-show" if self.b.get("status") == "no_show" else "late cancel"
        hb.text(self.dom_nodes["intro"], "%s on %s was a %s, so it used a credit. Life happens: tell %s what came up." % (
            c.get("title") or "This class", hb.date(c["start"]) if c.get("start") else "", kind, studio))
        self.reason = ""
        state.set_control_attr(self.note_box, "aria-label", "A few words for the studio")
        self.draw()

    def draw(self):
        self.reasons_panel.items = [{"group": "reason", "key": k, "label": label, "on": k == self.reason, "host": self} for k, label in REASONS]

    def chip(self, group, key):
        self.reason = "" if self.reason == key else key
        self.draw()

    def chip_panel_for(self, group):
        return self.reasons_panel

    @handle("send_button", "click")
    def send_button_click(self, **event_args):
        if not self.reason:
            state.toast("Pick what happened first.", "error")
            return
        self.send_button.enabled = False
        try:
            r = state.call("ask_kindness", self.b["id"], self.reason, self.note_box.text or "")
        finally:
            self.send_button.enabled = True
        if r:
            state.toast("Sent. The studio will answer in your inbox.", "ok")
            self.raise_event("x-close-alert", value=True)

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)
