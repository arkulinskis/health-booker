from anvil import *

from ._anvil_designer import ManageTemplate
from ... import hb, router, state

TABS = ["today", "schedule", "clients", "pricing", "team", "insights", "reviews", "settings"]


class Manage(ManageTemplate):
    """#manage[/<slug>/<tab>]: the studio back office for owners, front desk and admins. The tab bodies are Forms in
    client_code/Tabs (Today, Schedule, Clients, Pricing, Team, Insights, Reviews, Settings), each loading its own data
    from Manage.py. The last studio opened is remembered in this browser (key "mg-slug")."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.tab = args[1] if len(args) > 1 and args[1] in TABS else "today"
        slug = args[0] if args else ""
        self.list = state.call("manage_list") or []
        self.none.visible = not self.list
        self.main.visible = bool(self.list)
        if not self.list:
            return
        slugs = [s["slug"] for s in self.list]
        if slug not in slugs:
            last = state.store_get("mg-slug", "")
            own = [s for s in self.list if s.get("role") != "admin"]
            slug = last if last in slugs else (own or self.list)[0]["slug"]
            router.replace("manage", slug, self.tab)
        self.slug = slug
        state.store_set("mg-slug", slug)
        self.studio: dict = [s for s in self.list if s["slug"] == slug][0]
        self.draw_top()
        self.show_tab()

    def draw_top(self):
        s, dn = self.studio, self.dom_nodes
        hb.set_acc(self.page, s.get("accent"))
        hb.text(dn["name"], s["name"])
        hb.text(dn["role"], "Admin view" if s.get("role") == "admin" else "Front desk" if s.get("role") == "desk" else "Your studio")
        self.status_badge.visible = s.get("status") != "live"
        hb.text(dn["status_text"], "In review" if s.get("status") == "review" else "Paused")
        self.studio_box.visible = len(self.list) > 1
        self.studio_box.items = [(x["name"] + (" (demo)" if x.get("demo") else ""), x["slug"]) for x in self.list]
        self.studio_box.selected_value = self.slug
        state.set_control_attr(self.studio_box, "aria-label", "Studio")
        state.set_attr(self.page_link, "href", router.href("studio", self.slug))
        state.set_attr(self.kiosk_link, "href", router.href("kiosk", self.slug))
        for t in TABS:
            link = getattr(self, "tab_" + t)
            state.set_attr(link, "href", router.href("manage", self.slug, t))
            link.classes["on"] = t == self.tab

    def show_tab(self):
        """Make the open tab's Form (fresh each time, so it loads current data)."""
        self.body_panel.clear()
        if self.tab == "today":
            from ...Tabs.Today import Today as T
        elif self.tab == "schedule":
            from ...Tabs.Schedule import Schedule as T
        elif self.tab == "clients":
            from ...Tabs.Clients import Clients as T
        elif self.tab == "pricing":
            from ...Tabs.Pricing import Pricing as T
        elif self.tab == "team":
            from ...Tabs.Team import Team as T
        elif self.tab == "insights":
            from ...Tabs.Insights import Insights as T
        elif self.tab == "reviews":
            from ...Tabs.Reviews import Reviews as T
        else:
            from ...Tabs.Settings import Settings as T
        self.body_panel.add_component(T(slug=self.slug, studio=self.studio))

    @handle("studio_box", "change")
    def studio_box_change(self, **event_args):
        state.store_set("mg-slug", self.studio_box.selected_value)
        router.go("manage", self.studio_box.selected_value, self.tab)
