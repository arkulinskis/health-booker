from anvil import *

from ._anvil_designer import ClientRowTemplate
from ... import hb, state

TAGNAME = {"new": ("New", "good"), "member": ("Member", "brand"), "intro": ("Intro", "clay"), "drifting": ("Drifting", "warn"),
           "unpaid": ("Unpaid", "bad"), "expiring": ("Pass ending", "")}


class ClientRow(ClientRowTemplate):
    """A client in the back office: tags, visits, passes, when they were last messaged. item = {c, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        c: dict = self.item["c"]
        d = self.dom_nodes
        hb.text(d["initials"], state.initials(c.get("name")))
        hb.text(d["name"], c.get("name"))
        hb.text(d["email"], c.get("email"))
        hb.fill(d["tags"], [(TAGNAME[t][0], "ui-badge " + TAGNAME[t][1], None) for t in c.get("tags") or [] if t in TAGNAME])
        hb.text(d["visits"], hb.plural(c.get("visits") or 0, "visit"))
        hb.text(d["last"], (" · last " + hb.ago(c["last"])) if c.get("last") else "")
        hb.text(d["passes"], (", ".join(c.get("passes") or []) or "No active pass") + (" · %s booked" % c["upcoming"] if c.get("upcoming") else ""))
        hb.text(d["nudged"], ("Messaged " + hb.ago(c["nudged"])) if c.get("nudged") else "")

    @handle("message_button", "click")
    def message_button_click(self, **event_args):
        self.item["host"].message([self.item["c"]])

    @handle("detail_button", "click")
    def detail_button_click(self, **event_args):
        self.item["host"].detail(self.item["c"])
