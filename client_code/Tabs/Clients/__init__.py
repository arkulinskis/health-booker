from anvil import *
from anvil.js import window

from ._anvil_designer import ClientsTemplate
from ... import hb, state

TAGNAME = {"new": ("New", "good"), "member": ("Member", "brand"), "intro": ("Intro", "clay"), "drifting": ("Drifting", "warn"),
           "unpaid": ("Unpaid", "bad"), "expiring": ("Pass ending", "")}


class Clients(ClientsTemplate):
    """Back office > Clients: everyone who booked or bought a pass, tagged (new, member, intro, drifting, unpaid,
    pass ending), searchable; a personal message to one or a whole group; details; CSV export.
    Server: clients, client_detail, nudge, export_csv."""

    def __init__(self, slug="", studio=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.studio: dict = studio or {}
        self.tag = "all"
        self.q = ""
        self.all = False
        self._timer = None
        state.set_control_attr(self.search_box, "aria-label", "Search clients")
        self.load()

    def load(self):
        d = state.call("clients", self.slug)
        if d is None:
            return
        self.d: dict = d
        self.draw()

    def rows(self):
        q = self.q.lower()
        return [c for c in self.d["clients"] if (self.tag == "all" or self.tag in c["tags"]) and
                (not q or q in ((c.get("name") or "") + " " + (c.get("email") or "")).lower())]

    def draw(self):
        d = self.d
        n_drift = d["counts"].get("drifting", 0)
        self.drift_hint.visible = bool(n_drift)
        hb.text(self.dom_nodes["drift_title"], "%s a pass but hasn't come in 2 weeks." % hb.plural(n_drift, "student has", "students have"))
        tags = [("all", "All")] + [(k, v[0]) for k, v in TAGNAME.items()]
        self.tags_panel.items = [{"group": "tag", "key": k, "label": label, "count": d["counts"].get(k, 0), "on": self.tag == k, "host": self}
                                 for k, label in tags]
        rows = self.rows()
        self.nudge_all_button.visible = self.tag != "all" and bool(rows)
        self.nudge_all_button.text = "Message these %d" % len(rows)
        shown = rows if self.all else rows[:40]
        self.clients_panel.items = [{"c": c, "host": self} for c in shown]
        self.more_row.visible = len(rows) > len(shown)
        self.more_button.text = "Show all %d" % len(rows)
        self.empty.visible = not rows
        hb.text(self.dom_nodes["empty_text"], "Try another filter." if d["counts"].get("all") else "People who book or buy a pass show up here.")

    def chip_panel_for(self, group):
        return self.tags_panel

    def chip(self, group, key):
        self.tag = key
        self.draw()

    @handle("drift_button", "click")
    def drift_button_click(self, **event_args):
        self.chip("tag", "drifting")

    @handle("search_box", "change")
    def search_box_change(self, **event_args):
        self.q = self.search_box.text or ""
        if self._timer:
            window.clearTimeout(self._timer)
        self._timer = window.setTimeout(self.draw, 200)

    @handle("more_button", "click")
    def more_button_click(self, **event_args):
        self.all = True
        self.draw()

    def message(self, people, tag=None):
        from ...Dialogs.Nudge import Nudge
        if hb.ask(Nudge(slug=self.slug, studio=self.studio.get("name"), people=people, tag=tag)):
            self.load()

    @handle("nudge_all_button", "click")
    def nudge_all_button_click(self, **event_args):
        self.message(self.rows(), self.tag)

    def detail(self, c):
        from ...Dialogs.ClientDetail import ClientDetail
        hb.ask(ClientDetail(slug=self.slug, user_id=c["id"]), large=True)

    @handle("export_button", "click")
    def export_button_click(self, **event_args):
        r = state.call("export_csv", self.slug, "clients")
        if r:
            hb.download(r["filename"], r["csv"], "text/csv")
            state.toast("Downloaded " + r["filename"], "ok")
