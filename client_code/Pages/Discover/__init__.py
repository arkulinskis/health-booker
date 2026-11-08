import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import DiscoverTemplate
from ... import hb, router, state

TIMES = [("morning", "Morning", 0, 12), ("midday", "Midday", 12, 17), ("evening", "Evening", 17, 24)]
TOGGLES = [("beginner", "Beginner-friendly"), ("heated", "Heated"), ("unheated", "Not heated"), ("french", "En français"),
           ("open", "Mats left"), ("following", "Following"), ("workshop", "Workshops")]


class Discover(DiscoverTemplate):
    """#discover, #discover/studios: the marketplace. Every live studio's classes for the next 7 days (one server
    call: discover), filtered here by day, time, style, neighbourhood and tags; the class matcher; the studios tab.
    Open to everyone (no account needed to look). The filters are remembered in this browser (key "discover")."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.tab = "studios" if args and args[0] == "studios" else "classes"
        saved = state.store_dict("discover")
        self.st: dict = {"day": None, "q": "", "time": saved.get("time") or "", "style": saved.get("style") or "",
                         "hood": saved.get("hood") or "", "on": dict(saved.get("on") or {})}
        self._timer = None
        state.set_control_attr(self.style_box, "aria-label", "Style")
        self.load()

    # ---- data
    def load(self):
        self.d: dict = anvil.server.call("discover", hb.start_of_day(), 7)
        for c in self.d["classes"]:
            c["_hour"] = int(window.HBD.fmt.hour(c["start"]))
            c["_day"] = hb.day_key(c["start"])
        self.draw()

    def _save(self):
        state.store_set("discover", {"time": self.st["time"], "style": self.st["style"], "hood": self.st["hood"],
                                     "on": self.st["on"]})

    def matches(self, c):
        st, f = self.st, self.d["follows"]
        studio = c.get("studio") or {}
        teacher = c.get("teacher") or {}
        if st["q"]:
            words = " ".join([c["title"], studio.get("name") or "", teacher.get("name") or "",
                              studio.get("neighbourhood") or "", c.get("style") or ""]).lower()
            if st["q"].lower() not in words:
                return False
        if st["time"]:
            t = [x for x in TIMES if x[0] == st["time"]][0]
            if not (t[2] <= c["_hour"] < t[3]):
                return False
        if st["style"] and c.get("style") != st["style"]:
            return False
        if st["hood"] and studio.get("neighbourhood") != st["hood"]:
            return False
        on, tags = st["on"], c.get("tags") or []
        if on.get("beginner") and not (c.get("level") == "beginner" or "Beginner-friendly" in tags):
            return False
        if on.get("heated") and not c.get("heated"):
            return False
        if on.get("unheated") and c.get("heated"):
            return False
        if on.get("french") and not ("En français" in tags or "Bilingual" in tags):
            return False
        if on.get("open") and (c.get("left") or 0) <= 0:
            return False
        if on.get("workshop") and c.get("kind") != "workshop":
            return False
        if on.get("following") and not (studio.get("slug") in f["studios"] or teacher.get("id") in f["teachers"]):
            return False
        return True

    # ---- drawing
    def draw(self):
        me = state.me()
        d = self.d
        hb.text(self.dom_nodes["title"], "Find your class" if self.tab == "classes" else "Studios near you")
        n = len(d["studios"])
        hb.text(self.dom_nodes["lead"], ("Hello, %s. " % hb.first_name(me.get("name")) if me else "") +
                ("Every class at %s in Montréal, for the next 7 days." % hb.plural(n, "studio") if self.tab == "classes"
                 else "%s in Montréal: each one independent, all bookable with one account." % hb.plural(n, "studio")))
        self.list_link.visible = not me
        self.tab_classes.classes["on"] = self.tab == "classes"
        self.tab_studios.classes["on"] = self.tab == "studios"
        hb.text(self.dom_nodes["studio_count"], n)
        self.classes_part.visible = self.tab == "classes"
        self.studios_part.visible = self.tab == "studios"
        if self.tab == "studios":
            self.draw_studios()
            return
        styles = [s for s in d["styles"] if any(c.get("style") == s for c in d["classes"])]
        self.style_box.items = [("All styles", "")] + [(s, s) for s in styles]
        self.style_box.selected_value = self.st["style"] if self.st["style"] in styles else ""
        self.hood_box.items = [("All areas", "")] + [(h, h) for h in d["neighbourhoods"]]
        self.hood_box.selected_value = self.st["hood"] if self.st["hood"] in d["neighbourhoods"] else ""
        state.set_control_attr(self.style_box, "aria-label", "Style")
        state.set_control_attr(self.hood_box, "aria-label", "Neighbourhood")
        self.search_box.text = self.st["q"]
        state.set_control_attr(self.search_box, "aria-label", "Search classes")
        self.draw_list()

    def draw_list(self):
        d, st = self.d, self.st
        by_day: dict = {}
        for c in d["classes"]:
            by_day[c["_day"]] = by_day.get(c["_day"], 0) + (1 if self.matches(c) else 0)
        if not st["day"]:
            today = hb.day_key(hb.start_of_day())
            st["day"] = today if by_day.get(today) else (sorted(by_day.keys())[0] if by_day else today)
        days = []
        for i in range(7):
            iso = hb.start_of_day(i)
            k = hb.day_key(iso)
            days.append({"key": k, "top": "Today" if i == 0 else str(window.HBD.fmt.weekdayShort(iso)),
                         "num": int(window.HBD.fmt.dayNum(iso)), "count": by_day.get(k, 0), "on": k == st["day"], "host": self})
        self.days_panel.items = days
        me = state.me()
        chips = [{"group": "time", "key": t[0], "label": t[1], "on": st["time"] == t[0], "host": self} for t in TIMES]
        for key, label in TOGGLES:
            if key == "following" and not me:
                continue
            chips.append({"group": "tog", "key": key, "label": label, "on": bool(st["on"].get(key)), "host": self,
                          "icon": "flame" if key == "heated" else "heart" if key == "following" else None})
        self.chips_panel.items = chips
        rows = [c for c in d["classes"] if c["_day"] == st["day"] and self.matches(c)]
        self.list_panel.items = [{"c": c, "mine": d["mine"].get(c["id"]), "mode": "market", "host": self} for c in rows]
        self.empty.visible = not rows
        self.count_label.text = "%s on %s" % (hb.plural(len(rows), "class", "classes"), hb.rel_day(st["day"] + "T12:00:00"))
        n_on = len([k for k, v in st["on"].items() if v]) + sum(1 for k in ("time", "style", "hood") if st[k])
        self.clear_button.visible = bool(n_on)
        self.clear_button.text = "Clear " + hb.plural(n_on, "filter")

    def draw_studios(self):
        me = state.me()
        f = self.d["follows"]["studios"]
        self.studios_panel.items = [{"s": s, "fav": s["slug"] in f, "me": bool(me), "host": self} for s in self.d["studios"]]

    # ---- filters
    def pick_day(self, key):
        self.st["day"] = key
        k = state.focus_key()
        self.draw_list()
        state.refocus(self.days_panel, k)

    def chip(self, group, key):
        st = self.st
        if group == "time":
            st["time"] = "" if st["time"] == key else key
        else:
            st["on"][key] = not st["on"].get(key)
            if key == "heated" and st["on"][key]:
                st["on"]["unheated"] = False
            if key == "unheated" and st["on"][key]:
                st["on"]["heated"] = False
        self._save()
        self.draw_list()

    def chip_panel_for(self, group):
        return self.chips_panel

    @handle("style_box", "change")
    def style_box_change(self, **event_args):
        self.st["style"] = self.style_box.selected_value or ""
        self._save()
        self.draw_list()

    @handle("hood_box", "change")
    def hood_box_change(self, **event_args):
        self.st["hood"] = self.hood_box.selected_value or ""
        self._save()
        self.draw_list()

    @handle("search_box", "change")
    def search_box_change(self, **event_args):
        self.st["q"] = self.search_box.text or ""
        if self._timer:
            window.clearTimeout(self._timer)
        self._timer = window.setTimeout(self._search_now, 220)

    def _search_now(self):
        self._timer = None
        self.draw_list()

    @handle("clear_button", "click")
    def clear_button_click(self, **event_args):
        self.st.update(time="", style="", hood="", on={})
        self.style_box.selected_value = ""
        self.hood_box.selected_value = ""
        self._save()
        self.draw_list()

    def matcher_click(self, event):
        from ...Dialogs.Matcher import Matcher
        cid = hb.ask(Matcher(classes=self.d["classes"], follows=self.d["follows"]), large=True)
        if cid:
            router.go("class", cid)

    # ---- actions from rows and cards
    def book_row(self, c, button):
        button.enabled = False
        try:
            b = hb.book(c)
        finally:
            button.enabled = True
        if b:
            self.load()

    def follow_studio(self, slug):
        r = state.call("toggle_follow", "studio", slug)
        if r is None:
            return
        f = self.d["follows"]["studios"]
        if r.get("following") and slug not in f:
            f.append(slug)
        elif not r.get("following") and slug in f:
            f.remove(slug)
        state.toast('Following. Their classes show under "Following".' if r.get("following") else "Unfollowed.")
        self.draw_studios()
