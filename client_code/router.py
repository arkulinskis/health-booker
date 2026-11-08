"""Page addresses: #name/arg1/arg2 -> a page Form (open_form), with sign-in rules. The addresses are the same as the
JavaScript version had, so links people shared (studio pages, direct booking links, friend passes) keep working.

Links in templates are plain <a href="#discover">; code calls router.go("class", id).

    PAGES[name] = (who may open it, browser-tab title)   who: None = anyone, "guest" = signed out only, "user", "admin"
    nav() = the main menu (header + phone tab bar): Discover for everyone, Practice for members, Teach for teachers,
            Studio for owners / front desk. At most 4.
New page: add it to PAGES and to _form() (and to nav() if it belongs in the menu).
"""
import anvil
import anvil.js
from anvil.js import window

from . import state

PAGES = {
    "landing": (None, "Yoga classes across Montréal"),
    "auth": ("guest", "Sign in"),
    "discover": (None, "Find a class"),
    "studio": (None, "Studio"),
    "class": (None, "Class"),
    "gift": (None, "A friend pass for you"),
    "open": (None, "List your studio"),
    "practice": ("user", "My practice"),
    "inbox": ("user", "Inbox"),
    "teach": ("user", "Teach"),
    "manage": ("user", "Run my studio"),
    "kiosk": ("user", "Check-in"),
    "profile": ("user", "Your profile"),
    "admin": ("admin", "Admin"),
}
APP_NAME = "Health Booker"
_r: dict = {"after": "", "listening": False, "page": None}


def _loose(x):
    """Untyped pass-through for DOM objects the type checker can't follow."""
    return x


def nav():
    """(page, label, icon) for the menu: who sees what depends on the signed-in person's roles."""
    me = state.me()
    out = [("discover", "Discover", "search")]
    if me:
        out.append(("practice", "Practice", "leaf"))
        if me.get("teaches"):
            out.append(("teach", "Teach", "mat"))
        if me.get("manages"):
            out.append(("manage", "Studio", "door"))
    return out[:4]


def _form(name):
    """The page's Form class (imported when first needed, so start-up stays quick)."""
    if name == "landing":
        from .Pages.Landing import Landing
        return Landing
    if name == "auth":
        from .Pages.Auth import Auth
        return Auth
    if name == "discover":
        from .Pages.Discover import Discover
        return Discover
    if name == "studio":
        from .Pages.Studio import Studio
        return Studio
    if name == "class":
        from .Pages.ClassPage import ClassPage
        return ClassPage
    if name == "gift":
        from .Pages.Gift import Gift
        return Gift
    if name == "open":
        from .Pages.Open import Open
        return Open
    if name == "practice":
        from .Pages.Practice import Practice
        return Practice
    if name == "inbox":
        from .Pages.Inbox import Inbox
        return Inbox
    if name == "teach":
        from .Pages.Teach import Teach
        return Teach
    if name == "manage":
        from .Pages.Manage import Manage
        return Manage
    if name == "kiosk":
        from .Pages.Kiosk import Kiosk
        return Kiosk
    if name == "profile":
        from .Pages.Profile import Profile
        return Profile
    from .Pages.Admin import Admin
    return Admin


def parse(hash_text):
    h = (hash_text or "").lstrip("#").lstrip("!").lstrip("/").split("?")[0]
    parts = [window.decodeURIComponent(p) for p in h.split("/") if p]
    return (parts[0] if parts else ""), parts[1:]


def href(name, *args):
    """'#name/arg1/arg2' with every part URL-encoded (row ids contain brackets and commas)."""
    return "#" + "/".join([name] + [window.encodeURIComponent(str(a)) for a in args if a not in (None, "")])


def home_page():
    return "discover" if state.me() else "landing"


def show():
    """Open the page for the current address."""
    name, args = parse(window.location.hash)
    if name not in PAGES:
        name, args = home_page(), []
    who = PAGES[name][0]
    if who == "guest" and state.me():
        name, args = home_page(), []
    elif who in ("user", "admin") and not state.me():
        _r["after"] = window.location.hash
        name, args = "auth", []
    elif who == "admin" and not state.is_admin():
        state.toast("That page is for admins only.", "error")
        name, args = home_page(), []
    old = _r["page"]
    if old is not None and hasattr(old, "leave"):
        old.leave()  # pages with timers (the kiosk clock) stop them here
    _loose(window.document.documentElement).classList.remove("hb-solo")  # a studio's direct booking link turns it back on
    window.document.title = PAGES[name][1] + " · " + APP_NAME
    window.UI_READY = False
    page = _form(name)(args=args)
    _r["page"] = page
    anvil.open_form(page)
    shell = getattr(page, "layout", None)
    if shell is not None and hasattr(shell, "refresh"):
        shell.refresh(name)  # Anvil reuses the layout between pages: tell it who is signed in and which page is open
    window.scrollTo(0, 0)
    window.UI_READY = True  # tests and screenshots wait for this


def go(name, *args):
    """Go to a page. Same address again = reload the page."""
    target = href(name, *args)
    if window.location.hash == target:
        show()
    else:
        window.location.hash = target


def replace(name, *args):
    """Change the address without opening anything (a page that switches its own view)."""
    window.history.replaceState(None, "", href(name, *args))


def after_sign_in():
    """Where to go once someone signs in: the page they were heading for, or Discover."""
    target = _r["after"]
    _r["after"] = ""
    if target and target != window.location.hash:
        window.location.hash = target
    else:
        go(home_page())


def remember_after(target):
    _r["after"] = target


def need_account(after, message):
    """Booking, buying and claiming need an account: remember where they were and send them to sign up."""
    _r["after"] = after
    state.toast(message)
    go("auth", "signup")


def refresh_shell():
    """Redraw the header (the bell's count, the menu after a role change) without reopening the page."""
    page = _r["page"]
    shell = getattr(page, "layout", None) if page is not None else None
    if shell is not None and hasattr(shell, "refresh"):
        shell.refresh(parse(window.location.hash)[0] or home_page())


def _on_hash(event):
    show()


def start():
    if not _r["listening"]:
        window.addEventListener("hashchange", anvil.js.report_exceptions(_on_hash))
        _r["listening"] = True
    show()
