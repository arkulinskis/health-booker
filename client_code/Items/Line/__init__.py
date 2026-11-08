from anvil import *

from ._anvil_designer import LineTemplate
from ... import hb, state


class Line(LineTemplate):
    """A plain row: title, a line under it, optional initials, amount, badge and one action button.
    item = {title, sub, who, amount, badge, badge_cls, action, action_role, on_action(item)}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        d = self.dom_nodes
        hb.text(d["title"], it.get("title"))
        hb.text(d["sub"], it.get("sub") or "")
        d["sub"].hidden = not it.get("sub")
        self.avatar.visible = bool(it.get("who"))
        hb.text(d["initials"], state.initials(it.get("who")) if it.get("who") else "")
        self.amount.visible = bool(it.get("amount"))
        hb.text(d["amount_text"], it.get("amount") or "")
        hb.text(d["badge"], it.get("badge") or "")
        d["badge"].className = "ui-badge " + (it.get("badge_cls") or "")
        d["badge"].hidden = not it.get("badge")
        self.action_button.visible = bool(it.get("action"))
        if it.get("action"):
            self.action_button.text = it["action"]
            self.action_button.role = ["btn", "btn-sm"] + list(it.get("action_role") or [])

    @handle("action_button", "click")
    def action_button_click(self, **event_args):
        self.item["on_action"](self.item)
