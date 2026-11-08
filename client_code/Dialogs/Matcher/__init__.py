from anvil import *

from ._anvil_designer import MatcherTemplate
from ... import hb

MATCH = {
    "feel": [("energy", "Energised", ["Vinyasa", "Hot", "Ashtanga", "Pilates"]),
             ("calm", "Calm and rested", ["Yin", "Restorative", "Sound", "Breathwork", "Meditation"]),
             ("strong", "Strong and mobile", ["Hatha", "Mobility", "Pilates", "Ashtanga"]),
             ("gentle", "Gently cared for", ["Prenatal", "Chair", "Restorative", "Kids & family"])],
    "exp": [("new", "Brand new", []), ("some", "I know the basics", []), ("lots", "Bring it on", [])],
    "when": [("morning", "Morning", []), ("midday", "Midday", []), ("evening", "Evening", []), ("any", "Whenever", [])],
    "heat": [("yes", "Love the heat", []), ("no", "No heat please", []), ("any", "Don't mind", [])],
}
TIMES = {"morning": (0, 12, "morning"), "midday": (12, 17, "midday"), "evening": (17, 24, "evening")}


class Matcher(MatcherTemplate):
    """The class matcher: four questions, then the three best classes this week (one per class name).
    Closes with the chosen class id. classes = Discover's list (with _hour), follows = {studios, teachers}."""

    def __init__(self, classes=None, follows=None, **properties):
        super().__init__(**properties)
        self.class_list = classes or []
        self.follows: dict = follows or {"studios": [], "teachers": []}
        self.ans: dict = {}
        self.results.visible = False
        self.draw()

    def draw(self):
        for key, panel in (("feel", self.feel_panel), ("exp", self.exp_panel), ("when", self.when_panel), ("heat", self.heat_panel)):
            panel.items = [{"group": key, "key": k, "label": label, "on": self.ans.get(key) == k, "host": self}
                           for k, label, _ in MATCH[key]]

    def chip_panel_for(self, group):
        return {"feel": self.feel_panel, "exp": self.exp_panel, "when": self.when_panel, "heat": self.heat_panel}[group]

    def chip(self, group, key):
        self.ans[group] = key
        self.draw()
        if len(self.ans) == 4:
            self.score()

    def score(self):
        a = self.ans
        feel = [f for f in MATCH["feel"] if f[0] == a["feel"]][0]
        now = hb.now_ms()
        scored = []
        for c in self.class_list:
            if (c.get("left") or 0) <= 0 and c.get("kind") == "class":
                continue
            s, why = 0.0, []
            if c.get("style") in feel[2]:
                s += 6 - feel[2].index(c["style"])
                why.append("%s leaves you %s" % ((c.get("style") or "").lower(), feel[1].lower()))
            beg = c.get("level") == "beginner" or "Beginner-friendly" in (c.get("tags") or [])
            if a["exp"] == "new":
                if beg:
                    s += 4
                    why.append("beginner-friendly")
                if (c.get("intensity") or 0) >= 4 or c.get("level") == "intermediate":
                    s -= 5
            if a["exp"] == "lots" and (c.get("intensity") or 0) >= 4:
                s += 2
                why.append("a real challenge")
            if a["exp"] == "some" and c.get("level") == "all":
                s += 1
            if a["when"] != "any":
                lo, hi, word = TIMES[a["when"]]
                if lo <= c["_hour"] < hi:
                    s += 3
                    why.append(word)
                else:
                    s -= 3
            if a["heat"] == "yes" and c.get("heated"):
                s += 2
                why.append("heated")
            if a["heat"] == "no" and c.get("heated"):
                s -= 8
            if (c.get("studio") or {}).get("slug") in self.follows["studios"]:
                s += 1
            s -= (hb.ms(c["start"]) - now) / 864e5 * 0.15
            scored.append((s, c, why))
        scored.sort(key=lambda x: -x[0])
        seen, top = set(), []
        for s, c, why in scored:
            if len(top) < 3 and c["title"] not in seen:
                seen.add(c["title"])
                top.append({"c": c, "why": " · ".join(why[:3]), "host": self})
        self.results_panel.items = top
        self.results.visible = True

    def pick(self, class_id):
        self.raise_event("x-close-alert", value=class_id)

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
