from anvil import *

from ._anvil_designer import TeacherCardTemplate
from ... import hb, state


class TeacherCard(TeacherCardTemplate):
    """A teacher on a studio's Teachers tab. item = {t, following, me, host}; host.follow_teacher(id)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        t: dict = it["t"]
        d = self.dom_nodes
        hb.text(d["initials"], state.initials(t["name"]))
        hb.text(d["name"], t["name"])
        hb.fill(d["styles"], [(x, "hb-tag", None) for x in (t.get("styles") or [])])
        hb.text(d["bio"], t.get("bio"))
        self.follow_button.visible = bool(it.get("me"))
        f = bool(it.get("following"))
        self.follow_button.text = "Following" if f else "Follow"
        self.follow_button.role = ["btn", "btn-sm", "ic-heartfill" if f else "ic-heart"]
        state.set_control_attr(self.follow_button, "aria-pressed", "true" if f else "false")

    @handle("follow_button", "click")
    def follow_button_click(self, **event_args):
        self.item["host"].follow_teacher(self.item["t"]["id"])
