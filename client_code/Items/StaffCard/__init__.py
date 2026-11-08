from anvil import *

from ._anvil_designer import StaffCardTemplate
from ... import hb, state


class StaffCard(StaffCardTemplate):
    """Someone on the team: role, this month's numbers, their pay rule. item = {t, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        t: dict = self.item["t"]
        d = self.dom_nodes
        hb.text(d["initials"], state.initials(t.get("name")))
        hb.text(d["name"], t.get("name"))
        hb.text(d["email"], t.get("email"))
        role = t.get("role") or ""
        hb.text(d["role"], "Front desk" if role == "desk" else role[:1].upper() + role[1:])
        d["role"].className = "ui-badge" + (" brand" if role == "owner" else "")
        self.invited.visible = bool(t.get("invited"))
        self.nums.visible = bool(t.get("teaches"))
        if t.get("teaches"):
            hb.text(d["n_classes"], t.get("classes", 0))
            hb.text(d["n_avg"], t.get("avg", 0))
            hb.text(d["n_pay"], hb.money0(t.get("pay")))
            hb.text(d["n_rating"], ("%.1f" % t["rating"]) if t.get("rating_n") else "–")
            rule = "Pay: %s per class" % hb.money0(t.get("pay_base"))
            if t.get("pay_per_head"):
                rule += " + %s per student after %s" % (hb.money0(t["pay_per_head"]), t.get("pay_after"))
            if t.get("subs_covered"):
                rule += " · covered " + hb.plural(t["subs_covered"], "sub")
            hb.text(d["rule"], rule)
        else:
            hb.text(d["rule"], "Doesn't teach.")
        self.remove_button.visible = role != "owner"

    @handle("edit_button", "click")
    def edit_button_click(self, **event_args):
        self.item["host"].edit(self.item["t"])

    @handle("remove_button", "click")
    def remove_button_click(self, **event_args):
        self.item["host"].remove(self.item["t"])
