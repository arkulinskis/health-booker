from anvil import *

from ._anvil_designer import TeachClassTemplate
from ... import hb, router


class TeachClass(TeachClassTemplate):
    """One of a teacher's upcoming classes: fill, first-timers, the class list, ask for / withdraw a sub.
    item = {c, asked (open sub id or None), host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        c: dict = it["c"]
        d = self.dom_nodes
        hb.set_acc(self.card, (c.get("studio") or {}).get("accent"))
        clock, ampm = hb.time_parts(c["start"])
        hb.text(d["t_clock"], clock)
        hb.text(d["t_ampm"], ampm)
        hb.text(d["t_sub"], hb.mins(c.get("minutes")))
        d["title_link"].setAttribute("href", router.href("class", c["id"]))
        hb.text(d["title_link"], c["title"])
        hb.text(d["meta"], "%s · %s" % ((c.get("studio") or {}).get("name") or "", (c.get("room") or {}).get("name") or ""))
        tags = [("%s / %s booked" % (c.get("booked"), c.get("capacity")), "hb-tag", None)]
        if c.get("waiting"):
            tags.append(("%d waiting" % c["waiting"], "hb-tag", None))
        if c.get("first_timers"):
            tags.append((hb.plural(c["first_timers"], "first-timer"), "hb-tag good", None))
        if it.get("asked"):
            tags.append(("Sub requested", "hb-tag sub", None))
        hb.fill(d["tags"], tags)
        started = hb.ms(c["start"]) < hb.now_ms()
        self.ask_button.visible = not started and not it.get("asked")
        self.withdraw_button.visible = not started and bool(it.get("asked"))

    @handle("roster_button", "click")
    def roster_button_click(self, **event_args):
        self.item["host"].roster(self.item["c"]["id"])

    @handle("ask_button", "click")
    def ask_button_click(self, **event_args):
        self.item["host"].ask(self.item["c"]["id"])

    @handle("withdraw_button", "click")
    def withdraw_button_click(self, **event_args):
        self.item["host"].withdraw(self.item["asked"])
