from anvil import *

from ._anvil_designer import PassCardTemplate
from ... import hb, router, state


class PassCard(PassCardTemplate):
    """A pass in the wallet: studio, credits left, dates, pay at the desk, pause a membership. item = {p, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p: dict = self.item["p"]
        s: dict = p.get("studio") or {}
        d = self.dom_nodes
        live = p.get("state") in ("active", "paused")
        hb.set_acc(self.card, s.get("accent"))
        self.card.classes["dim"] = not live
        hb.text(d["studio"], s.get("name"))
        st = p.get("state") or ""
        hb.text(d["state_badge"], st[:1].upper() + st[1:])
        d["state_badge"].className = "ui-badge " + {"active": "good", "paused": "warn"}.get(st, "")
        hb.text(d["name"], p["name"])
        if p.get("unlimited"):
            hb.text(d["big"], "Unlimited")
            hb.text(d["of"], "")
        else:
            hb.text(d["big"], p.get("credits_left"))
            hb.text(d["of"], " of %s left" % p.get("credits_total"))
        hb.text(d["dates"], ("Paused until %s · " % hb.full_date(p.get("paused_until")) if st == "paused" else "") +
                ("Valid until " if live else "Ended ") + hb.full_date(p.get("expires")))
        self.pay.visible = not p.get("paid") and live
        hb.text(d["pay_text"], "Pay at the desk: " + hb.money(p.get("price")))
        self.pause_button.visible = bool(p.get("can_pause"))
        state.set_attr(self.book_link, "href", router.href("studio", s.get("slug")))

    @handle("pause_button", "click")
    def pause_button_click(self, **event_args):
        self.item["host"].pause(self.item["p"])
