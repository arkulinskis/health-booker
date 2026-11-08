import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import GiftTemplate
from ... import hb, router, state


class Gift(GiftTemplate):
    """#gift/<code>: a friend pass someone shared. Signed-in visitors claim it (a free first class), others sign up
    first and come back here. Server: friend_pass_get, friend_pass_claim."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.code = args[0] if args else ""
        d = anvil.server.call("friend_pass_get", self.code)
        ok = bool(d) and d.get("ok") is not False and bool(d.get("studio"))
        self.bad.visible = not ok
        self.card.visible = ok
        if not ok:
            return
        s: dict = d["studio"]
        me = state.me()
        hb.set_acc(self.card, s.get("accent"))
        hb.text(self.dom_nodes["title"], "A gift from %s: your first class at %s is free" % (d.get("from"), s["name"]))
        hb.text(self.dom_nodes["from"], "%s · %s" % (s.get("tagline") or "", s.get("neighbourhood") or ""))
        hb.text(self.dom_nodes["fine"], "For people who haven't been to %s before. Valid 3 weeks after claiming." % s["name"])
        state.set_attr(self.book_link, "href", router.href("studio", s["slug"]))
        mine, claimed, sender = bool(d.get("mine")), bool(d.get("claimed")), bool(d.get("sender_is_me"))
        self.book_link.visible = mine
        self.used.visible = not mine and claimed
        self.mine.visible = not mine and not claimed and sender
        self.claim_button.visible = not mine and not claimed and not sender and bool(me)
        self.join_button.visible = not mine and not claimed and not sender and not me

    @handle("claim_button", "click")
    def claim_button_click(self, **event_args):
        r = state.call("friend_pass_claim", self.code)
        if r:
            state.toast("It's in your wallet. Pick a class!", "ok")
            router.go("studio", r["slug"])

    @handle("join_button", "click")
    def join_button_click(self, **event_args):
        router.need_account("#gift/" + self.code, "Create your free account, then claim your class.")

    @handle("copy_button", "click")
    def copy_button_click(self, **event_args):
        hb.copy(str(window.location.href))
