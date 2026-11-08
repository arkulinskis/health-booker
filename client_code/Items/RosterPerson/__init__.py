from anvil import *

from ._anvil_designer import RosterPersonTemplate
from ... import hb, state


class RosterPerson(RosterPersonTemplate):
    """Someone on a class list. item = {p, mgr, started, host}: check in / undo, no-show once class started;
    owners and the desk can forgive and mark paid."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        p: dict = it["p"]
        d = self.dom_nodes
        st = p["status"]
        self.row.classes["in"] = st == "checked_in"
        hb.text(d["initials"], state.initials(p["name"]))
        hb.text(d["name"], p["name"])
        badges = []
        if p.get("first_visit"):
            badges.append(("First visit", "ui-badge good", "leaf"))
        if p.get("milestone"):
            badges.append(("%sth class!" % p.get("visits"), "ui-badge clay", None))
        if st == "late":
            badges.append(("Late cancel", "ui-badge warn", None))
        if st == "no_show":
            badges.append(("No-show", "ui-badge bad", None))
        if p.get("unpaid"):
            badges.append(("Unpaid", "ui-badge warn", None))
        if not p.get("waiver"):
            badges.append(("No waiver", "ui-badge bad", None))
        hb.fill(d["badges"], badges)
        hb.text(d["sub"], ("Mat %s · " % p["spot"] if p.get("spot") else "") + (p.get("pass") or "Walk-in") + " · " +
                hb.plural(p.get("visits") or 0, "visit"))
        self.health.visible = bool(p.get("health"))
        hb.text(d["health_text"], p.get("health"))
        can_att = st in ("booked", "checked_in", "no_show")
        self.in_button.visible = can_att
        self.in_button.text = "Here" if st == "checked_in" else "Check in"
        self.in_button.role = ["btn", "btn-sm", "ic-check"] + (["btn-primary"] if st == "checked_in" else [])
        state.set_control_attr(self.in_button, "aria-pressed", "true" if st == "checked_in" else "false")
        self.noshow_button.visible = bool(it.get("started")) and st == "booked"
        self.forgive_button.visible = bool(it.get("mgr")) and st in ("late", "no_show")
        self.paid_button.visible = bool(it.get("mgr")) and bool(p.get("unpaid")) and bool(p.get("pass_id"))

    @handle("in_button", "click")
    def in_button_click(self, **event_args):
        p = self.item["p"]
        self.item["host"].attend(p["id"], "booked" if p["status"] == "checked_in" else "checked_in")

    @handle("noshow_button", "click")
    def noshow_button_click(self, **event_args):
        self.item["host"].attend(self.item["p"]["id"], "no_show")

    @handle("forgive_button", "click")
    def forgive_button_click(self, **event_args):
        self.item["host"].forgive(self.item["p"]["id"])

    @handle("paid_button", "click")
    def paid_button_click(self, **event_args):
        self.item["host"].paid(self.item["p"]["pass_id"])
