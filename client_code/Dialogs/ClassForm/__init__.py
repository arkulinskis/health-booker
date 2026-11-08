import anvil.server
from anvil import *

from ._anvil_designer import ClassFormTemplate
from ... import hb, state


class ClassForm(ClassFormTemplate):
    """New class (repeat weekly) or edit one (this one, or this and the following ones), plus cancel class and the
    class list. sched = manage_schedule's reply (teachers, rooms, styles, levels, tags). Closes with True when the
    schedule changed. Server: save_class, cancel_class."""

    def __init__(self, slug="", sched=None, klass=None, week_start=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.s: dict = sched or {}
        self.is_new = klass is None
        c: dict = klass or {"title": "", "style": "Vinyasa", "level": "all", "intensity": 2, "heated": False, "tags": [],
                            "about": "", "minutes": 60, "kind": "class", "price": 0}
        self.c = c
        self.changed = False
        s = self.s
        hb.text(self.dom_nodes["title"], "New class" if self.is_new else "Edit class")
        start = c.get("start") or hb.add_days(week_start or hb.start_of_day(), 1)
        from anvil.js import window
        if not c.get("start"):
            start = str(window.HBD.fmt.toIso(hb.day_key(start), "18:00"))
        self.title_box.text = c.get("title") or ""
        self.style_box.items = [(x, x) for x in s.get("styles") or []]
        self.style_box.selected_value = c.get("style") if c.get("style") in (s.get("styles") or []) else None
        self.level_box.items = [(hb.LEVEL.get(x, x), x) for x in s.get("levels") or []]
        self.level_box.selected_value = c.get("level") or "all"
        self.teacher_box.items = [(t["name"], t["id"]) for t in s.get("teachers") or []]
        tid = (c.get("teacher") or {}).get("id")
        if tid in [t["id"] for t in s.get("teachers") or []]:
            self.teacher_box.selected_value = tid
        rooms = s.get("rooms") or []
        self.room_box.items = [("%s (%s mats)" % (r["name"], r["capacity"]), r["id"]) for r in rooms]
        rid = (c.get("room") or {}).get("id") or (rooms[0]["id"] if rooms else None)
        if rid:
            self.room_box.selected_value = rid
        self.date_box.text = hb.day_key(start)
        state.control(self.time_box).setAttribute("type", "time")  # the App Server's TextBox has no type="time"
        self.time_box.text = str(window.HBD.fmt.hhmm(start))
        self.minutes_box.text = str(c.get("minutes") or 60)
        self.capacity_box.text = str(c.get("capacity") or (rooms[0]["capacity"] if rooms else 12))
        self.kind_box.items = [("Class (uses passes)", "class"), ("Workshop (own price)", "workshop")]
        self.kind_box.selected_value = c.get("kind") or "class"
        self.price_box.text = str(c.get("price") or 0)
        self.intensity_box.items = [("%d of 5 · %s" % (i, hb.INTENSITY[i]), i) for i in range(1, 6)]
        self.intensity_box.selected_value = int(c.get("intensity") or 2)
        self.heated_box.checked = bool(c.get("heated"))
        self.tags = set(c.get("tags") or [])
        self.about_box.text = c.get("about") or ""
        self.repeat_field.visible = self.is_new
        self.repeat_box.items = [("Just once" if n == 1 else "%d weeks" % n, n) for n in (1, 2, 4, 6, 8, 12)]
        self.repeat_box.selected_value = 8
        self.scope_field.visible = not self.is_new and bool(c.get("series"))
        self.scope_box.items = [("This class only", "one"), ("This and the following ones", "future")]
        self.cancel_class_button.visible = not self.is_new and c.get("status") != "cancelled"
        self.roster_button.visible = not self.is_new
        self.save_button.text = "Add to schedule" if self.is_new else "Save"
        self.draw_tags()

    def draw_tags(self):
        self.tags_panel.items = [{"group": "tag", "key": t, "label": t, "on": t in self.tags, "host": self} for t in self.s.get("tags") or []]

    def chip_panel_for(self, group):
        return self.tags_panel

    def chip(self, group, key):
        if key in self.tags:
            self.tags.discard(key)
        else:
            self.tags.add(key)
        self.draw_tags()

    @handle("room_box", "change")
    def room_box_change(self, **event_args):
        r = [x for x in self.s.get("rooms") or [] if x["id"] == self.room_box.selected_value]
        if r:
            self.capacity_box.text = str(r[0]["capacity"])

    def _int(self, box, default):
        try:
            return float(box.text)
        except (TypeError, ValueError):
            return default

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        from anvil.js import window
        if not self.date_box.text or not self.time_box.text:
            self.message.text, self.message.visible = "Choose a date and time.", True
            return
        payload = {"id": self.c.get("id"), "title": self.title_box.text or "", "style": self.style_box.selected_value,
                   "level": self.level_box.selected_value, "teacher_id": self.teacher_box.selected_value,
                   "room_id": self.room_box.selected_value,
                   "start": str(window.HBD.fmt.toIso(str(self.date_box.text)[:10], self.time_box.text)),
                   "minutes": self._int(self.minutes_box, 60), "capacity": self._int(self.capacity_box, 12),
                   "kind": self.kind_box.selected_value, "price": self._int(self.price_box, 0),
                   "intensity": self.intensity_box.selected_value, "heated": bool(self.heated_box.checked),
                   "about": self.about_box.text or "", "repeat_weeks": self.repeat_box.selected_value or 1,
                   "scope": self.scope_box.selected_value or "one", "tags": [t for t in self.s.get("tags") or [] if t in self.tags]}
        self.save_button.enabled = False
        try:
            r = anvil.server.call("save_class", self.slug, payload)
        finally:
            self.save_button.enabled = True
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        n = r.get("count") or 1
        state.toast((hb.plural(n, "class", "classes") + (" added." if self.is_new else " updated.")) if n > 1
                    else ("Class added." if self.is_new else "Saved."), "ok")
        self.raise_event("x-close-alert", value=True)

    @handle("cancel_class_button", "click")
    def cancel_class_button_click(self, **event_args):
        from ..CancelClass import CancelClass
        if hb.ask(CancelClass(klass=self.c)):
            self.raise_event("x-close-alert", value=True)

    @handle("roster_button", "click")
    def roster_button_click(self, **event_args):
        if hb.roster(self.c["id"]):
            self.changed = True

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=self.changed)
