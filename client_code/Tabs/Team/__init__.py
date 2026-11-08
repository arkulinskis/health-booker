from anvil import *

from ._anvil_designer import TeamTemplate
from ... import hb, state


class Team(TeamTemplate):
    """Back office > Team: everyone on the team with this month's classes, average students, pay and rating; invite
    by email, edit pay rules, remove; the sub requests. Server: team, save_staff, remove_staff."""

    def __init__(self, slug="", studio=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.load()

    def load(self):
        from anvil.js import window
        d = state.call("team", self.slug, str(window.HBD.fmt.monthStart(0)), str(window.HBD.fmt.nowIso()))
        if d is None:
            return
        self.d: dict = d
        self.team_panel.items = [{"t": t, "host": self} for t in d["team"]]
        lines = []
        for x in d["subs"]:
            c = x.get("class") or {}
            st = x.get("status")
            lines.append({"title": "%s · %s" % (c.get("title") or "", hb.when(c.get("start"))),
                          "sub": (x.get("from") or "") + ((': "%s"' % x["reason"]) if x.get("reason") else ""),
                          "badge": ("Covered by " + (x.get("filled_by") or "")) if st == "filled" else "Open" if st == "open" else "Withdrawn",
                          "badge_cls": {"filled": "good", "open": "warn"}.get(st, "")})
        self.subs_panel.items = lines
        self.no_subs.visible = not lines

    def edit(self, t):
        from ...Dialogs.StaffForm import StaffForm
        if hb.ask(StaffForm(slug=self.slug, staff=t), large=True):
            self.load()

    def remove(self, t):
        if confirm("They lose access to this studio. Their past classes stay in your records.", title="Remove from the team?",
                   buttons=[("Cancel", False), ("Remove", True)], role="app-dialog"):
            if state.call("remove_staff", t["id"]):
                state.toast("Removed.")
                self.load()

    @handle("invite_button", "click")
    def invite_button_click(self, **event_args):
        self.edit(None)
