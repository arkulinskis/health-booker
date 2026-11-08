import json

from anvil import *
from anvil.js import window

from ._anvil_designer import PracticeTemplate
from ... import hb, state

TABS = ["upcoming", "journal", "wallet", "following"]


class Practice(PracticeTemplate):
    """#practice[/journal|wallet|following]: the student's home. Upcoming bookings (cancel, calendar), the journal
    (12-week heatmap, styles, mood after class, reflections), the wallet (passes at every studio, pause a membership,
    friend passes) and who they follow. One server call: my_practice; stats are worked out in local time (HBD.stats)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.tab = args[0] if args and args[0] in TABS else "upcoming"
        self.load()

    def load(self):
        d = state.call("my_practice")
        if d is None:
            return
        self.d: dict = d
        self.draw()

    def draw(self):
        d, dn = self.d, self.dom_nodes
        me = state.me() or {}
        hist = [{"start": b["class"]["start"], "minutes": b["class"].get("minutes") or 0, "mood": b.get("mood")} for b in d["history"]]
        s = json.loads(window.HBD.stats(json.dumps(hist)))
        hb.text(dn["hello"], "Namaste, %s. Your classes, your journal and your passes at every studio." % hb.first_name(me.get("name")))
        hb.text(dn["k_month"], s["month"])
        hb.text(dn["k_streak"], s["streak"])
        hb.text(dn["k_streak_word"], ("week" if s["streak"] == 1 else "weeks") + " in a row")
        hb.text(dn["k_hours"], s["hours"])
        hb.text(dn["k_mood"], hb.MOODS[int(round(s["mood"])) - 1] if s["mood"] else "–")
        hb.text(dn["k_mood_note"], "Average of your reflections" if s["mood"] else "Add a reflection after class")
        live = [p for p in d["passes"] if p.get("state") in ("active", "paused")]
        hb.text(dn["n_upcoming"], len(d["upcoming"]) or "")
        dn["n_upcoming"].hidden = not d["upcoming"]
        hb.text(dn["n_wallet"], len(live) or "")
        dn["n_wallet"].hidden = not live
        for name in TABS:
            getattr(self, "tab_" + name).classes["on"] = name == self.tab
            getattr(self, name + "_part").visible = name == self.tab
        getattr(self, "_draw_" + self.tab)()

    def _draw_upcoming(self):
        rows = [{"c": b["class"], "b": b, "mine": b["status"], "mode": "upcoming", "host": self} for b in self.d["upcoming"]]
        self.up_panel.items = hb.by_day(rows)
        self.no_upcoming.visible = not rows

    def _draw_journal(self):
        h = self.d["history"]
        self.no_journal.visible = not h
        self.journal_body.visible = bool(h)
        if not h:
            return
        counts: dict = {}
        styles: dict = {}
        for b in h:
            k = hb.day_key(b["class"]["start"])
            counts[k] = counts.get(k, 0) + 1
            st = b["class"].get("style") or ""
            styles[st] = styles.get(st, 0) + 1
        self.heat_chart.draw("heat", {"counts": counts})
        top = sorted(styles.keys(), key=lambda k: -styles[k])[:6]
        self.styles_chart.draw("hbars", {"rows": [{"label": k, "value": styles[k]} for k in top]})
        moods = [b for b in h if b.get("mood")][:15]
        moods.reverse()
        self.mood_card.visible = len(moods) >= 2
        if len(moods) >= 2:
            hb.text(self.dom_nodes["mood_note"], "Your last %d reflections. Hover a dot for the class." % len(moods))
            self.mood_chart.draw("mood", {"points": [{"mood": b["mood"], "label": "%s, %s" % (b["class"]["title"], hb.date(b["class"]["start"]))}
                                                     for b in moods]})
        self.entries_panel.items = [{"b": b, "host": self} for b in h]

    def _draw_wallet(self):
        d = self.d
        self.passes_panel.items = [{"p": p, "host": self} for p in d["passes"]]
        self.no_passes.visible = not d["passes"]
        self.late_part.visible = bool(d["late"])
        self.late_panel.items = [{"title": b["class"]["title"], "sub": "%s · %s" % ((b["class"].get("studio") or {}).get("name"), hb.date(b["class"]["start"])),
                                  "badge": "Late cancel" if b["status"] == "late" else "No-show",
                                  "badge_cls": "warn" if b["status"] == "late" else "bad"} for b in d["late"]]
        self.friends_panel.items = [{"title": f["studio"], "sub": "Created " + hb.ago(f.get("created")),
                                     "badge": "Claimed" if f.get("claimed") else "", "badge_cls": "good",
                                     "action": None if f.get("claimed") else "Copy link", "action_role": ["ic-copy"],
                                     "code": f["code"], "on_action": self._copy_gift} for f in d["friend_passes"]]

    def _draw_following(self):
        self.follow_panel.items = [{"f": f} for f in self.d["follows"]]
        self.no_follows.visible = not self.d["follows"]

    # ---- actions
    def _copy_gift(self, item):
        hb.copy(hb.link("#gift/" + item["code"]), "Friend pass link copied.")

    def cancel_row(self, b):
        if hb.cancel(b):
            self.load()

    def book_row(self, c, button):
        pass

    def reflect(self, b):
        if hb.reflect(b):
            self.load()

    def pause(self, p):
        from ...Dialogs.Pause import Pause
        if hb.ask(Pause(pass_id=p["id"])):
            self.load()
