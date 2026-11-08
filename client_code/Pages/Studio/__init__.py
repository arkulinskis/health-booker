import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import StudioTemplate
from ... import hb, router, state

TABS = ["schedule", "pricing", "teachers", "reviews", "about"]


class Studio(StudioTemplate):
    """#studio/<slug>[/solo]: one studio. Schedule (14 days, a week at a time), pricing, teachers, reviews, about +
    policies + friend passes; follow, share, buy a pass. "solo" is the studio's own booking link: the marketplace
    menu is hidden (html.hb-solo) so its students don't see other studios. One server call: get_studio."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.slug = args[0] if args else ""
        self.solo = len(args) > 1 and args[1] == "solo"
        if self.solo:
            hb.loose(window.document.documentElement).classList.add("hb-solo")
        t = state.store_get("studio-tab", "schedule")
        self.tab = t if t in TABS else "schedule"
        self.weeks = 1
        self.load()

    def load(self):
        r = anvil.server.call("get_studio", self.slug)
        if not r or r.get("ok") is False:
            self.d: dict = {}
            self.hero.visible = self.body.visible = self.preview.visible = False
            self.not_found.visible = True
            return
        self.not_found.visible = False
        self.d = r
        self.draw()

    def following(self):
        return self.slug in self.d["follows"]["studios"]

    def draw(self):
        d, s = self.d, self.d["studio"]
        me = state.me()
        dn = self.dom_nodes
        window.document.title = s["name"] + " · Health Booker"
        self.preview.visible = s.get("status") != "live"
        hb.text(dn["preview_text"], "Preview: this studio is %s. Only its team and admins can see it." % (
            "waiting for review" if s.get("status") == "review" else "paused"))
        hb.set_acc(self.hero, s.get("accent"))
        hb.set_acc(self.body, s.get("accent"))
        self.back_link.visible = not self.solo
        hb.text(dn["name"], s["name"])
        hb.text(dn["tagline"], s.get("tagline"))
        hb.text(dn["where"], (s.get("neighbourhood") or "") + (" · " + s["address"] if s.get("address") else ""))
        if s.get("rating_n"):
            hb.stars(dn["stars"], s.get("rating") or 0)
        else:
            dn["stars"].textContent = ""
        hb.text(dn["rating"], hb.rating_text(s.get("rating"), s.get("rating_n")))
        self.langs.visible = bool(s.get("languages"))
        hb.text(dn["langs_text"], " · ".join(s.get("languages") or []))
        self.follow_button.visible = bool(me)
        f = self.following()
        self.follow_button.text = "Following" if f else "Follow"
        self.follow_button.role = ["btn", "ic-heartfill" if f else "ic-heart"]
        state.set_control_attr(self.follow_button, "aria-pressed", "true" if f else "false")
        self.manage_link.visible = bool(d.get("can_manage"))
        state.set_attr(self.manage_link, "href", router.href("manage", self.slug))
        counts = {"reviews": s.get("rating_n") or 0, "teachers": len(d["teachers"])}
        for name in TABS:
            btn = getattr(self, "tab_" + name)
            n = counts.get(name, 0)
            btn.text = {"schedule": "Schedule", "pricing": "Pricing", "teachers": "Teachers", "reviews": "Reviews",
                        "about": "About"}[name] + (" (%d)" % n if n else "")
            btn.role = ["tab", "ic-" + {"schedule": "calendar", "pricing": "ticket", "teachers": "users",
                                        "reviews": "star", "about": "info"}[name]] + (["on"] if name == self.tab else [])
            state.set_control_attr(btn, "aria-pressed", "true" if name == self.tab else "false")
            getattr(self, name + "_part").visible = name == self.tab
        getattr(self, "_draw_" + self.tab)()
        # side
        intro = [p for p in d["products"] if p.get("intro_only") and p.get("eligible")]
        self.intro.visible = bool(intro)
        if intro:
            self._intro = intro[0]
            hb.text(dn["intro_price"], hb.money(intro[0].get("price")))
            hb.text(dn["intro_name"], intro[0]["name"])
        mine = [p for p in d["passes"] if p.get("state") in ("active", "paused")]
        self.mine_card.visible = bool(mine)
        self.mine_panel.items = [{"p": p} for p in mine]
        hb.text(dn["good"], "Cancel for free up to %s hours before class. %s Pay the studio at your first visit." % (
            s.get("cancel_hours"), "Your waiver is signed." if d.get("waiver") else "You'll sign a short waiver the first time you book."))
        self.powered.visible = self.solo

    # ---- tabs
    def _draw_schedule(self):
        d = self.d
        until = hb.ms(hb.start_of_day(7 * self.weeks))
        cls = [c for c in d["classes"] if hb.ms(c["start"]) < until]
        rows = [{"c": c, "mine": d["mine"].get(c["id"]), "mode": "studio", "solo": self.solo, "host": self} for c in cls]
        self.days_panel.items = hb.by_day(rows)
        self.more_row.visible = len(d["classes"]) > len(cls)
        self.no_classes.visible = not cls
        hb.text(self.dom_nodes["no_classes_text"], "Add your first class in Manage studio." if d.get("can_manage")
                else "Follow the studio to hear when classes open.")

    def _draw_pricing(self):
        self.products_panel.items = [{"p": p, "host": self} for p in self.d["products"]]
        hb.text(self.dom_nodes["pay_studio"], self.d["studio"]["name"])

    def _draw_teachers(self):
        me = state.me()
        ft = self.d["follows"]["teachers"]
        self.teachers_panel.items = [{"t": t, "following": t["id"] in ft, "me": bool(me), "host": self} for t in self.d["teachers"]]
        self.no_teachers.visible = not self.d["teachers"]

    def _draw_reviews(self):
        revs = self.d["reviews"]
        self.reviews_panel.items = [{"r": r, "studio": self.d["studio"]["name"], "mode": "studio"} for r in revs]
        self.reviews_hint.visible = bool(revs)
        self.no_reviews.visible = not revs

    def _draw_about(self):
        s, dn = self.d["studio"], self.dom_nodes
        hb.text(dn["about"], s.get("about") or s.get("tagline"))
        self.amen_block.visible = bool(s.get("amenities"))
        hb.fill(dn["amenities"], [(a, "st-amen-i", "check") for a in s.get("amenities") or []])
        hb.fill(dn["styles"], [(x, "hb-tag", None) for x in s.get("styles") or []])
        hb.text(dn["policy"], "Free cancellation until %s hours before class. Later cancels and no-shows count against your "
                "pass. If the studio cancels, your credit comes back automatically." % s.get("cancel_hours"))
        hb.text(dn["waiver"], s.get("waiver_text"))
        can_gift = any(p.get("kind") in ("pack", "unlimited") and p.get("state") == "active" for p in self.d["passes"])
        self.gift_card.visible = can_gift
        hb.text(dn["gift_text"], "Your pass comes with friend passes: their first class at %s is free." % s["name"])

    def _tab(self, name):
        self.tab = name
        state.store_set("studio-tab", name)
        self.draw()

    @handle("tab_schedule", "click")
    def tab_schedule_click(self, **event_args):
        self._tab("schedule")

    @handle("tab_pricing", "click")
    def tab_pricing_click(self, **event_args):
        self._tab("pricing")

    @handle("tab_teachers", "click")
    def tab_teachers_click(self, **event_args):
        self._tab("teachers")

    @handle("tab_reviews", "click")
    def tab_reviews_click(self, **event_args):
        self._tab("reviews")

    @handle("tab_about", "click")
    def tab_about_click(self, **event_args):
        self._tab("about")

    @handle("more_button", "click")
    def more_button_click(self, **event_args):
        self.weeks += 1
        self._draw_schedule()

    # ---- actions
    @handle("follow_button", "click")
    def follow_button_click(self, **event_args):
        r = state.call("toggle_follow", "studio", self.slug)
        if r is None:
            return
        f = self.d["follows"]["studios"]
        if r.get("following") and self.slug not in f:
            f.append(self.slug)
        elif not r.get("following") and self.slug in f:
            f.remove(self.slug)
        state.toast("Following %s." % self.d["studio"]["name"] if r.get("following") else "Unfollowed.")
        self.draw()

    def follow_teacher(self, tid):
        r = state.call("toggle_follow", "teacher", tid)
        if r is None:
            return
        f = self.d["follows"]["teachers"]
        if r.get("following") and tid not in f:
            f.append(tid)
        elif not r.get("following") and tid in f:
            f.remove(tid)
        self._draw_teachers()

    @handle("share_button", "click")
    def share_button_click(self, **event_args):
        from ...Dialogs.Share import Share
        hb.ask(Share(name=self.d["studio"]["name"], slug=self.slug))

    def buy(self, p):
        if not state.me():
            router.need_account(window.location.hash, "Create your free account first. It works at every studio.")
            return
        rest = [x for x in self.d["products"] if x["id"] != p["id"]]
        if hb.shop(self.d["studio"], [p] + rest):
            self.load()

    @handle("intro_button", "click")
    def intro_button_click(self, **event_args):
        self.buy(self._intro)

    @handle("gift_button", "click")
    def gift_button_click(self, **event_args):
        r = state.call("friend_pass_send", self.slug)
        if r:
            from ...Dialogs.FriendLink import FriendLink
            hb.ask(FriendLink(studio=self.d["studio"]["name"], link=hb.link("#gift/" + r["code"])))

    def book_row(self, c, button):
        button.enabled = False
        try:
            b = hb.book(c)
        finally:
            button.enabled = True
        if b:
            self.load()
