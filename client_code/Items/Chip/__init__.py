from anvil import *

from ._anvil_designer import ChipTemplate
from ... import state


class Chip(ChipTemplate):
    """A toggle chip (filters, answers, tags). item = {group, key, label, on, icon, count, host}:
    pressing it calls host.chip(group, key); the page redraws the chips with the new "on" state."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        self.btn.text = it["label"] + (("  %s" % it["count"]) if it.get("count") is not None else "")
        role = ["hb-chip"]
        if it.get("on"):
            role.append("on")
        if it.get("icon"):
            role.append("ic-" + it["icon"])
        self.btn.role = role
        state.set_control_attr(self.btn, "aria-pressed", "true" if it.get("on") else "false")
        state.set_control_attr(self.btn, "data-key", "%s:%s" % (it.get("group"), it.get("key")))

    @handle("btn", "click")
    def btn_click(self, **event_args):
        key = state.focus_key()
        host = self.item["host"]
        host.chip(self.item.get("group"), self.item["key"])
        panel = getattr(host, "chip_panel_for", None)
        if key and panel:
            state.refocus(panel(self.item.get("group")), key)
