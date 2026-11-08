from anvil import *

from ._anvil_designer import ClientDetailTemplate
from ... import hb, state


class ClientDetail(ClientDetailTemplate):
    """One client: waiver (health notes only if they shared them), passes (mark paid), visits. Server: client_detail."""

    def __init__(self, slug="", user_id=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.user_id = user_id
        self.load()

    def load(self):
        d = state.call("client_detail", self.slug, self.user_id)
        if d is None:
            return
        dn = self.dom_nodes
        hb.text(dn["name"], d["name"])
        hb.text(dn["email"], d["email"])
        w = d.get("waiver")
        if w:
            text = "Waiver signed " + hb.full_date(w.get("signed"))
            if w.get("health"):
                text += "\nHealth notes: " + w["health"]
            elif not w.get("shared"):
                text += "\nHealth notes not shared."
            if w.get("emergency"):
                text += "\nEmergency: " + w["emergency"]
        else:
            text = "No waiver yet."
        hb.text(dn["waiver"], text)
        self.passes_panel.items = [{"title": p["name"], "sub": "%s · %s · until %s" % (p.get("state"), "unlimited" if p.get("unlimited") else "%s left" % p.get("credits_left"), hb.full_date(p.get("expires"))),
                                    "badge": "Paid" if p.get("paid") else "", "badge_cls": "good",
                                    "action": None if p.get("paid") else "Mark paid · " + hb.money(p.get("price")), "action_role": ["btn-clay"],
                                    "id": p["id"], "on_action": self._paid} for p in d["passes"]]
        self.visits_panel.items = [{"cells": [("%s · %s" % (hb.date(b["start"]), b.get("title")), "c"), ((b.get("status") or "").replace("_", " "), "c ui-badge")],
                                    "cls": "mg-visit"} for b in d["bookings"][:25]]

    def _paid(self, item):
        if hb.mark_paid(item["id"]):
            self.load()

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
