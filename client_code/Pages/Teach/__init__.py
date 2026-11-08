from anvil import *
from anvil.js import window

from ._anvil_designer import TeachTemplate
from ... import hb, state

TABS = ["classes", "subs", "pay", "reviews"]


class Teach(TeachTemplate):
    """#teach[/subs|pay|reviews]: for teachers (any active staff row). Upcoming classes across their studios with the
    class list, sub requests (ask, cover in one tap, withdraw), the monthly pay statement (base + per head above a
    threshold) and their reviews. Server: teach_home, request_sub, withdraw_sub, cover_sub (+ the roster dialog)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.tab = args[0] if args and args[0] in TABS else "classes"
        self.month = 0
        state.set_control_attr(self.prev_button, "aria-label", "Previous month")
        state.set_control_attr(self.next_button, "aria-label", "Next month")
        self.load()

    def _range(self):
        return str(window.HBD.fmt.monthStart(self.month)), str(window.HBD.fmt.monthStart(self.month + 1))

    def load(self):
        a, b = self._range()
        d = state.call("teach_home", a, b)
        if d is None:
            return
        self.d: dict = d
        self.draw()

    def draw(self):
        d, dn = self.d, self.dom_nodes
        self.no_team.visible = not d.get("teaching")
        self.main.visible = bool(d.get("teaching"))
        if not d.get("teaching"):
            return
        hb.text(dn["studios"], "Your classes at " + " · ".join(s["name"] for s in d["studios"]))
        n_open = len(d["open_subs"])
        hb.text(dn["k_up"], len(d["upcoming"]))
        hb.text(dn["k_pay"], hb.money0(d["pay"]["total"]))
        hb.text(dn["k_pay_note"], "%s, %s" % (hb.plural(len(d["pay"]["lines"]), "class", "classes"), hb.plural(d["pay"]["heads"], "student")))
        hb.text(dn["k_subs"], n_open)
        hb.text(dn["k_subs_word"], ("colleague needs" if n_open == 1 else "colleagues need") + " a sub")
        hb.text(dn["k_rating"], ("%.1f" % d["rating"]) if d.get("rating_n") else "–")
        hb.text(dn["k_rating_note"], hb.plural(d.get("rating_n") or 0, "review"))
        hb.text(dn["n_subs"], n_open or "")
        dn["n_subs"].hidden = not n_open
        for name in TABS:
            getattr(self, "tab_" + name).classes["on"] = name == self.tab
            getattr(self, name + "_part").visible = name == self.tab
        getattr(self, "_draw_" + self.tab)()

    def _draw_classes(self):
        asked = {x["class"]["id"]: x["id"] for x in self.d["my_subs"] if x.get("status") == "open" and x.get("class")}
        rows = [{"c": c, "asked": asked.get(c["id"]), "host": self} for c in self.d["upcoming"]]
        groups = hb.by_day(rows)
        for g in groups:
            g["tpl"] = "teach"
        self.days_panel.items = groups
        self.no_classes.visible = not rows

    def _draw_subs(self):
        d = self.d
        self.open_panel.items = [{"x": x, "mine": False, "host": self} for x in d["open_subs"]]
        self.no_open.visible = not d["open_subs"]
        self.mine_panel.items = [{"x": x, "mine": True, "host": self} for x in d["my_subs"]]
        self.no_mine.visible = not d["my_subs"]

    def _draw_pay(self):
        d, p = self.d, self.d["pay"]
        label = str(window.HBD.fmt.monthYear(self._range()[0]))
        hb.text(self.dom_nodes["month"], label)
        self.next_button.enabled = self.month < 0
        rules = []
        for s in d["studios"]:
            text = "%s: %s per class" % (s["name"], hb.money0(s["pay_base"]))
            if s.get("pay_per_head"):
                text += " + %s for each student after the %s" % (hb.money(s["pay_per_head"]), hb.ordinal(int(s.get("pay_after") or 0)))
            rules.append({"cells": [(text + ". Classes with nobody still pay the base.", "c")], "cls": "tc-rule"})
        self.rules_panel.items = rules
        self.pay_table.visible = bool(p["lines"])
        head = {"cells": [("Date", "th"), ("Class", "th"), ("Studio", "th studio"), ("Students", "th n"), ("Pay", "th n")], "cls": "tc-row tc-head"}
        rows = [{"cells": [(hb.date(l["start"]), "c"), (l["title"], "c"), (l["studio"], "c studio muted"), (str(l["heads"]), "c n"),
                           (hb.money0(l["pay"]), "c n")], "cls": "tc-row"} for l in p["lines"]]
        foot = {"cells": [("Total", "c"), ("", "c"), ("", "c studio"), (str(p["heads"]), "c n"), (hb.money0(p["total"]), "c n")], "cls": "tc-row tc-foot"}
        self.lines_panel.items = [head] + rows + [foot]
        self.no_pay.visible = not p["lines"]
        hb.text(self.dom_nodes["no_pay_text"], "No classes taught in %s yet." % label)

    def _draw_reviews(self):
        self.reviews_panel.items = [{"r": r, "mode": "teach"} for r in self.d["reviews"]]
        self.no_reviews.visible = not self.d["reviews"]

    # ---- actions
    def roster(self, class_id):
        if hb.roster(class_id):
            self.load()

    def ask(self, class_id):
        from ...Dialogs.AskSub import AskSub
        if hb.ask(AskSub(class_id=class_id)):
            self.load()

    def withdraw(self, sub_id):
        if state.call("withdraw_sub", sub_id):
            state.toast("Request withdrawn.")
            self.load()

    def cover(self, sub_id):
        if confirm("It moves to you right away and everyone is told.", title="Cover this class?",
                   buttons=[("Cancel", False), ("Yes, I'll teach it", True)], role="app-dialog"):
            if state.call("cover_sub", sub_id):
                state.toast("Thank you! It's in your classes now.", "ok")
                self.load()

    @handle("prev_button", "click")
    def prev_button_click(self, **event_args):
        self.month -= 1
        self.load()

    @handle("next_button", "click")
    def next_button_click(self, **event_args):
        if self.month < 0:
            self.month += 1
            self.load()

    @handle("csv_button", "click")
    def csv_button_click(self, **event_args):
        rows = [["date", "class", "studio", "students", "pay"]] + [[l["start"], l["title"], l["studio"], l["heads"], l["pay"]]
                                                                  for l in self.d["pay"]["lines"]]
        hb.download("pay-%s.csv" % self._range()[0][:7], hb.csv_text(rows), "text/csv")
