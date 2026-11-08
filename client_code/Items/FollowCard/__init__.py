from anvil import *
from anvil.js import window

from ._anvil_designer import FollowCardTemplate
from ... import hb, router, state


class FollowCard(FollowCardTemplate):
    """A studio or teacher you follow (both link to the studio page). item = {f}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        f: dict = self.item["f"]
        d = self.dom_nodes
        state.set_attr(self.link, "href", router.href("studio", f.get("slug")))
        hb.text(d["name"], f.get("name"))
        if f.get("kind") == "studio":
            hb.set_acc(self.link, f.get("accent"))
            icon = window.document.createElement("i")
            icon.className = "ic ic-door"
            d["avatar"].appendChild(icon)
            hb.text(d["sub"], "Studio")
        else:
            hb.text(d["avatar"], state.initials(f.get("name")))
            hb.text(d["sub"], "Teaches at " + (f.get("studio") or ""))
