"""Who is signed in, their profile, and who is an admin.

The emails in the App Secret `admin_emails` become admins the first time they sign in with a proven
address (Google sign-in or a confirmed email): see AdminAccess.py. The address is never in the code.
"""
import anvil.server
import anvil.users
from anvil.tables import app_tables

from . import common as C
from . import AdminAccess

ADMIN_EMAILS = AdminAccess.ADMIN_EMAILS  # from the App Secret `admin_emails`


def me_dict(user):
    if user is None:
        return None
    roles = []
    for st in app_tables.staff.search(user=user):
        s = st["studio"]
        if s is not None and st["active"] is not False:
            roles.append({"slug": s["slug"], "name": s["name"], "role": st["role"], "teaches": bool(st["teaches"]),
                          "status": s["status"]})
    return {"id": user.get_id(), "email": user["email"], "name": C.name_of(user),
            "is_admin": C.is_admin(user), "joined": C.iso(user["signed_up"]), "roles": roles,
            "teaches": any(r["teaches"] for r in roles),
            "manages": C.is_admin(user) or any(r["role"] in ("owner", "desk") for r in roles),
            "unread": len(app_tables.notices.search(user=user, read=False))}


def _claim_invites(user):
    """Team invites are made by email: the first time that person signs in, the invite becomes theirs."""
    email = (user["email"] or "").lower()
    if not email:
        return
    for st in app_tables.staff.search(email=email, user=None):
        st["user"] = user


@anvil.server.callable
def get_me():
    """The signed-in user (or None). Called when the app starts and after signing in."""
    user = anvil.users.get_user()
    if user is None:
        return None
    changes: dict = {}
    if AdminAccess.may_promote(user) and not user["is_admin"]:
        changes["is_admin"] = True
    seen = user["last_seen"]
    if seen is None or (C.now() - seen).total_seconds() > 3600:
        changes["last_seen"] = C.now()
    if changes:
        user.update(**changes)
    _claim_invites(user)
    return me_dict(user)


@anvil.server.callable(require_user=True)
def update_profile(name):
    user = C.require_user()
    name = C.text(name, 60)
    if len(name) < 2:
        return C.fail("Please use at least 2 characters for your name.")
    user["display_name"] = name
    return C.ok(me=me_dict(user))
