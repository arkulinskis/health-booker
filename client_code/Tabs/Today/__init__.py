from anvil import *

from ._anvil_designer import TodayTemplate
from ... import hb, state


class Today(TodayTemplate):
    """Back office > Today: one day's classes (fill, check-ins, the class list), sales, first-timers, open subs and
    passes to collect at the desk. Server: manage_day, restore_class (+ roster and mark-paid dialogs)."""

    def __init__(self, slug="", studio=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.offset = 0
        for b, label in ((self.prev_button, "Previous day"), (self.next_button, "Next day")):
            state.set_control_attr(b, "aria-label", label)
        self.load()

    def load(self):
        a, b = hb.start_of_day(self.offset), hb.start_of_day(self.offset + 1)
        d = state.call("manage_day", self.slug, a, b)
        if d is None:
            return
        dn = self.dom_nodes
        is_today = self.offset == 0
        hb.text(dn["day"], "Today" if is_today else hb.date(a))
        self.today_button.visible = not is_today
        fill = int(round(d["visits"] * 100.0 / d["capacity"])) if d["capacity"] else 0
        hb.text(dn["k_visits"], d["visits"])
        hb.text(dn["k_cap"], " / %s" % d["capacity"])
        hb.text(dn["k_fill"], "mats booked (%d%% full)" % fill)
        hb.text(dn["k_first"], d["first_timers"])
        hb.text(dn["k_sold"], hb.money0(d["sold"]["total"]))
        hb.text(dn["k_sold_n"], hb.plural(d["sold"]["count"], "pass", "passes") + " sold")
        hb.text(dn["k_unpaid"], len(d["unpaid"]))
        subs = d["open_subs"]
        self.subs_hint.visible = bool(subs)
        hb.text(dn["subs_title"], hb.plural(len(subs), "class needs", "classes need") + " a sub.")
        hb.text(dn["subs_text"], " · ".join("%s (%s, %s)" % (x["class"]["title"], hb.date(x["class"]["start"]), x["from"]) for x in subs if x.get("class")) +
                ". Your teachers see it in Teach; or change the teacher in Schedule.")
        self.classes_panel.items = [{"c": c, "host": self} for c in d["classes"]]
        self.no_classes.visible = not d["classes"]
        self.unpaid_panel.items = [{"title": p["who"], "who": p["who"], "sub": "%s · got it %s" % (p["name"], hb.ago(p.get("created"))),
                                    "amount": hb.money(p.get("price")), "action": "Mark paid", "action_role": ["btn-clay"],
                                    "id": p["id"], "on_action": self._paid} for p in d["unpaid"]]
        self.all_paid.visible = not d["unpaid"]

    def _paid(self, item):
        if hb.mark_paid(item["id"]):
            self.load()

    def roster(self, class_id):
        if hb.roster(class_id):
            self.load()

    def restore(self, class_id):
        if state.call("restore_class", class_id):
            state.toast("Back on the schedule.", "ok")
            self.load()

    @handle("prev_button", "click")
    def prev_button_click(self, **event_args):
        self.offset -= 1
        self.load()

    @handle("next_button", "click")
    def next_button_click(self, **event_args):
        self.offset += 1
        self.load()

    @handle("today_button", "click")
    def today_button_click(self, **event_args):
        self.offset = 0
        self.load()
