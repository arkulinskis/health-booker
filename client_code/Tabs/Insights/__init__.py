from anvil import *

from ._anvil_designer import InsightsTemplate
from ... import hb, state

_days: dict = {"n": 28}


class Insights(InsightsTemplate):
    """Back office > Insights in plain words: visits, fill, sales (per day and by kind), when classes fill up, intro
    offers that stick, favourite classes, teachers. Server: insights. The charts are drawn by hb-draw.js."""

    def __init__(self, slug="", studio=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.load()

    def load(self):
        d = state.call("insights", self.slug, _days["n"])
        if d is None:
            return
        dn = self.dom_nodes
        for n, el in ((7, self.r7), (28, self.r28), (90, self.r90)):
            el.classes["on"] = n == _days["n"]
        hb.text(dn["k_visits"], d["visits"])
        hb.text(dn["k_classes"], hb.plural(d["classes"], "class", "classes"))
        hb.text(dn["k_fill"], "%s%%" % d["fill"])
        hb.text(dn["k_rev"], hb.money0(d["revenue_total"]))
        hb.text(dn["k_noshow"], "%s%%" % d["no_show_rate"])
        hb.text(dn["k_late"], "%s late cancels" % d["late"])
        hb.text(dn["k_new"], d["clients"]["new"])
        hb.text(dn["k_clients"], "%s members · %s drifting" % (d["clients"]["members"], d["clients"]["drifting"]))
        hb.text(dn["k_mood"], hb.MOODS[int(round(d["mood"])) - 1] if d.get("mood") else "–")
        hb.text(dn["k_mood_n"], ("From " + hb.plural(d["mood_n"], "reflection")) if d.get("mood_n") else "No reflections yet")
        hb.text(dn["rev_note"], "Total %s. Hover a bar for the day." % hb.money0(d["revenue_total"]))
        days = []
        for i in range(d["days"] - 1, -1, -1):
            iso = hb.start_of_day(-i)
            v = d["daily"].get(hb.day_key(iso), 0)
            days.append({"iso": iso, "value": v, "label": hb.money0(v)})
        self.cols_chart.draw("cols", {"days": days, "total": hb.money0(d["revenue_total"])})
        rk = sorted(d["revenue"].keys(), key=lambda k: -d["revenue"][k])
        self.kind_chart.draw("hbars", {"rows": [{"label": hb.KIND.get(k, k), "value": d["revenue"][k], "text": hb.money0(d["revenue"][k])} for k in rk]})
        self.no_sales.visible = not rk
        self.fill_chart.draw("fillgrid", {"heat": d["heat"]})
        f = d["funnel"]
        hb.text(dn["funnel_note"], "Students who started with an intro or friend pass (last %d days)." % max(d["days"], 60))
        started = f["started"] or 0
        rows = []
        for label, v in (("Started", f["started"]), ("Came back", f["second"]), ("Bought a pack or membership", f["converted"])):
            rows.append({"label": label, "value": v, "pct": (v * 100.0 / (started or 1)),
                         "extra": ("%d%%" % round(v * 100.0 / started)) if label != "Started" and started else None})
        self.funnel_chart.draw("hbars", {"rows": rows})
        hb.text(dn["friend"], "Friend passes: %s shared, %s claimed." % (d["friend"]["sent"], d["friend"]["claimed"]))
        head = {"cells": [("Class", "th"), ("Avg", "th n"), ("Fill", "th n")], "cls": "mg-t3 mg-thead"}
        self.top_panel.items = [head] + [{"cells": [("%s ×%s" % (t["title"], t["classes"]), "c"), (str(t["avg"]), "c n"), ("%s%%" % t["fill"], "c n")],
                                          "cls": "mg-t3"} for t in d["top"]]
        head2 = {"cells": [("Teacher", "th"), ("Classes", "th n"), ("Avg", "th n"), ("Rating", "th n")], "cls": "mg-t4 mg-thead"}
        self.teachers_panel.items = [head2] + [{"cells": [(t["name"], "c"), (str(t["classes"]), "c n"), (str(t["avg"]), "c n"),
                                                          (("%.1f" % t["rating"]) if t.get("rating") else "–", "c n")], "cls": "mg-t4"} for t in d["teachers"]]

    def range_click(self, event):
        _days["n"] = int(event.currentTarget.getAttribute("data-days"))
        self.load()
