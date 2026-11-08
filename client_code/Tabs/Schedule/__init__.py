from anvil import *

from ._anvil_designer import ScheduleTemplate
from ... import hb, state


class Schedule(ScheduleTemplate):
    """Back office > Schedule: a week of classes as columns; press one to edit it (or cancel it, or see its class
    list); New class repeats weekly. Server: manage_schedule, save_class, cancel_class."""

    def __init__(self, slug="", studio=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.studio: dict = studio or {}
        self.week = 0
        for b, label in ((self.prev_button, "Previous week"), (self.next_button, "Next week")):
            state.set_control_attr(b, "aria-label", label)
        self.load()

    def load(self):
        start = hb.start_of_day(self.week)
        d = state.call("manage_schedule", self.slug, start, 7)
        if d is None:
            return
        self.d: dict = d
        hb.text(self.dom_nodes["range"], "%s – %s" % (hb.day_month(start), hb.day_month(hb.start_of_day(self.week + 6))))
        self.setup_note.visible = not (d["teachers"] and d["rooms"])
        today = hb.day_key(hb.start_of_day())
        cols = []
        for i in range(7):
            iso = hb.start_of_day(self.week + i)
            k = hb.day_key(iso)
            from anvil.js import window
            cols.append({"label": str(window.HBD.fmt.weekdayDay(iso)), "today": k == today,
                         "blocks": [c for c in d["classes"] if hb.day_key(c["start"]) == k], "host": self})
        self.week_panel.items = cols

    def edit(self, c):
        from ...Dialogs.ClassForm import ClassForm
        if hb.ask(ClassForm(slug=self.slug, sched=self.d, klass=c, week_start=hb.start_of_day(self.week)), large=True):
            self.load()

    @handle("new_button", "click")
    def new_button_click(self, **event_args):
        self.edit(None)

    @handle("prev_button", "click")
    def prev_button_click(self, **event_args):
        self.week -= 7
        self.load()

    @handle("next_button", "click")
    def next_button_click(self, **event_args):
        self.week += 7
        self.load()
