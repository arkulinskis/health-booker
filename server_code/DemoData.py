"""Demo content, so the marketplace is alive for the first visitor: six fictional Montréal studios (one still
in review), their teachers, weekly schedules (ten days of history at Sage & Stone, ~12 days ahead everywhere),
~60 students with passes, bookings, reflections and reviews, a sub request, friend passes.

Loaded automatically the first time anyone opens Discover (ensure_loaded); removed or reloaded from
Admin -> Demo data, and removing it is remembered. top_up() keeps the demo schedule rolling forward so it
never runs dry. Every demo row has is_demo=True; demo people use @example.com addresses and can't sign in.
All names, studios, addresses and reviews are made up.
"""
import datetime as dt
import random

from anvil.tables import app_tables

from . import common as C
from . import Model as Mo

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Toronto")
except Exception:  # no tz database: Montréal winter time is close enough for demo times
    TZ = dt.timezone(dt.timedelta(hours=-5))

DEMO_TABLES = ["notices", "friend_passes", "follows", "subs", "reviews", "bookings", "waivers", "passes", "products",
               "classes", "staff", "rooms", "studios"]
STUDIO_TABLES = ["notices", "friend_passes", "subs", "reviews", "bookings", "waivers", "passes", "products", "classes", "rooms"]
AHEAD = 12
HISTORY = {"sage-and-stone": 21}

FIRST = ["Camille", "Noah", "Léa", "Arjun", "Sofia", "Gabriel", "Hannah", "Mathis", "Zoé", "Ethan", "Amira", "Lucas",
         "Olivia", "Félix", "Maya", "Jules", "Chloé", "Daniel", "Rosalie", "Sam", "Élise", "Victor", "Ingrid", "Malik",
         "Juliette", "Omar", "Florence", "Liam", "Nora", "Thomas"]
LAST = ["Fortin", "Williams", "Bouchard", "Patel", "Rossi", "Lavoie", "Kim", "Côté", "Pelletier", "Murphy", "Haddad",
        "Moreau", "Brown", "Girard", "Singh", "Bergeron", "Martin", "Okafor", "Gagné", "Nguyen", "Dubois", "Leblanc",
        "Larsen", "Diallo", "Roy", "Chen", "Lopez", "Ouellet", "Ahmed", "Fischer"]
N_STUDENTS = 140

H = "Beginner-friendly"
STUDIOS: list = [
    {"slug": "sage-and-stone", "name": "Sage & Stone Yoga", "hood": "Plateau-Mont-Royal", "addr": "4410 rue Saint-Denis (demo)",
     "tagline": "Slow mornings, strong practice.", "accent": "sage", "featured": True, "weight": 6,
     "about": "A sunny second-floor studio above Saint-Denis with wooden floors, big windows and a tea bar that's always on. "
              "We teach mindful vinyasa, slow yin and alignment-based hatha in small classes, in English and French. "
              "New to yoga? Start with Yoga 101 on Saturdays: no flexibility required.",
     "styles": ["Vinyasa", "Yin", "Hatha", "Restorative"], "amen": ["Mats & props provided", "Showers", "Tea bar", "Lockers", "Step-free access"],
     "langs": ["English", "Français"], "cancel": 12,
     "rooms": [("Main room", 4, 5, ["A1"]), ("Garden room", 3, 4, [])],
     "team": [("Maya Chen", "maya", "owner", "Founder. Twenty years of practice, ten of teaching; believes the best class is the one you leave lighter.", ["Vinyasa", "Hatha"], 45, 3, 8),
              ("Theo Martin", "theo", "teacher", "Former climber who teaches strong, playful vinyasa with lots of options.", ["Vinyasa"], 40, 3, 8),
              ("Inès Ozola", "ines", "teacher", "Yin, nidra and restorative. Soft voice, long holds, warm blankets.", ["Yin", "Restorative"], 40, 3, 8),
              ("Samir Haddad", "samir", "teacher", "Alignment nerd. Teaches hatha and Yoga 101 with patience and good jokes.", ["Hatha"], 40, 3, 8)],
     "products": [("Intro week: unlimited for 7 days", "intro", None, 7, 29, True, "New here? Try every class for a week."),
                  ("Drop-in", "dropin", 1, 30, 24, False, "One class, use it within 30 days."),
                  ("5-class pack", "pack", 5, 90, 110, False, "Five classes, valid three months."),
                  ("10-class pack", "pack", 10, 180, 200, False, "Ten classes, valid six months."),
                  ("Monthly unlimited", "unlimited", None, 30, 149, False, "Practise as much as you like. Pause anytime.")],
     # (weekdays, "HH:MM", title, style, minutes, level, intensity, heated, tags, teacher index, room index)
     "week": [([0, 1, 2, 3, 4], "07:00", "Sunrise Vinyasa", "Vinyasa", 60, "all", 3, False, ["Props provided"], 1, 0),
              ([0, 2, 4], "12:15", "Lunch Flow", "Vinyasa", 45, "all", 3, False, [], 0, 0),
              ([1, 3], "12:15", "Desk Release Hatha", "Hatha", 45, "beginner", 2, False, [H, "Bilingual"], 3, 0),
              ([0, 2], "18:00", "Strong Flow", "Vinyasa", 75, "intermediate", 4, False, ["Live music"], 1, 0),
              ([1, 3], "18:00", "Alignment Hatha", "Hatha", 75, "all", 2, False, ["Props provided", "En français"], 3, 0),
              ([0, 1, 2, 3], "19:45", "Yin & Yoga Nidra", "Yin", 75, "all", 1, False, [H, "Candlelit"], 2, 1),
              ([4], "18:00", "Candlelit Yin", "Yin", 75, "all", 1, False, ["Candlelit", "Trauma-informed"], 2, 1),
              ([5], "09:30", "Saturday Slow Flow", "Vinyasa", 75, "all", 2, False, [H], 0, 1),
              ([5], "11:30", "Yoga 101: Foundations", "Hatha", 60, "beginner", 1, False, [H, "Props provided", "Bilingual"], 3, 0),
              ([6], "10:00", "Restorative & Sound", "Restorative", 75, "all", 1, False, ["Live music", "Trauma-informed"], 2, 1),
              ([6], "17:00", "Sunday Vinyasa", "Vinyasa", 60, "intermediate", 3, False, [], 1, 0)],
     "workshops": [(5, "14:00", "Inversions Without Fear", "Vinyasa", 120, 45, 1, "Headstand and forearm stand, step by step, with a wall and a lot of laughing. All levels welcome; no one goes upside down before they're ready.")]},
    {"slug": "lumen-hot-yoga", "name": "Lumen Hot Yoga", "hood": "Griffintown", "addr": "1100 rue Ottawa (demo)",
     "tagline": "Turn up the heat, turn down the noise.", "accent": "clay", "featured": False, "weight": 4,
     "about": "Infrared-heated rooms at 35°C, filtered fresh air and a no-mirrors policy. Sweat, breathe, go home calm.",
     "styles": ["Hot", "Vinyasa", "Hatha"], "amen": ["Infrared heat", "Showers", "Towel service", "Filtered water"],
     "langs": ["English", "Français"], "cancel": 8,
     "rooms": [("Hot room", 5, 6, [])],
     "team": [("Jordan Price", "jordan", "owner", "Opened Lumen after a decade in hot studios in Vancouver.", ["Hot"], 50, 2, 12),
              ("Chloé Tremblay", "chloe.t", "teacher", "Teaches hot flow like a dance class. Great playlists.", ["Hot", "Vinyasa"], 45, 2, 12),
              ("Marcus Bell", "marcus", "teacher", "Calm, precise hot hatha. Tells you exactly where to breathe.", ["Hot", "Hatha"], 45, 2, 12)],
     "products": [("Two intro weeks", "intro", None, 14, 40, True, "Two weeks unlimited for new students."),
                  ("Drop-in", "dropin", 1, 30, 27, False, "One class."),
                  ("10-class pack", "pack", 10, 120, 220, False, "Valid four months."),
                  ("Monthly unlimited", "unlimited", None, 30, 165, False, "Includes towel service.")],
     "week": [([0, 1, 2, 3, 4], "06:30", "Hot Vinyasa", "Hot", 60, "all", 4, True, ["Heated"], 1, 0),
              ([0, 1, 2, 3, 4], "12:00", "Hot Express", "Hot", 45, "all", 3, True, ["Heated"], 2, 0),
              ([0, 2, 4], "17:30", "Hot Hatha 90", "Hot", 90, "all", 3, True, ["Heated"], 0, 0),
              ([1, 3], "17:30", "Hot Power Flow", "Hot", 60, "intermediate", 5, True, ["Heated", "Live music"], 1, 0),
              ([0, 1, 2, 3], "19:15", "Hot Yin", "Yin", 60, "all", 1, True, ["Heated", H], 2, 0),
              ([5, 6], "09:00", "Weekend Hot Flow", "Hot", 75, "all", 4, True, ["Heated"], 1, 0),
              ([5, 6], "11:00", "Hot Hatha for Beginners", "Hot", 60, "beginner", 2, True, ["Heated", H], 2, 0)],
     "workshops": []},
    {"slug": "petit-lotus", "name": "Petit Lotus", "hood": "Rosemont", "addr": "2870 rue Masson (demo)",
     "tagline": "Yoga for bumps, babies and grown-ups who need gentle.", "accent": "plum", "featured": False, "weight": 2,
     "about": "A small, soft studio for prenatal and postnatal yoga, baby-and-me classes and chair yoga. Strollers welcome, "
              "change table in the bathroom, and nobody minds a crying baby.",
     "styles": ["Prenatal", "Kids & family", "Chair", "Restorative"], "amen": ["Stroller parking", "Change table", "Chairs & bolsters", "Step-free access"],
     "langs": ["Français", "English"], "cancel": 4,
     "rooms": [("Studio", 3, 4, [])],
     "team": [("Amélie Roy", "amelie", "owner", "Doula and prenatal yoga teacher, mother of three.", ["Prenatal", "Kids & family"], 40, 4, 5),
              ("Nadia Benali", "nadia", "teacher", "Physiotherapist who teaches chair yoga and postnatal recovery.", ["Chair", "Restorative"], 45, 4, 5)],
     "products": [("First class free", "intro", 1, 30, 0, True, "Come and see. No strings."),
                  ("Drop-in", "dropin", 1, 30, 20, False, "One class."),
                  ("8-class prenatal series", "pack", 8, 120, 136, False, "Through your pregnancy at your pace.")],
     "week": [([1, 3], "10:00", "Prenatal Flow", "Prenatal", 60, "all", 2, False, ["Prenatal-safe", "Props provided", "En français"], 0, 0),
              ([0, 2], "10:30", "Baby & Me Yoga", "Kids & family", 60, "all", 1, False, ["Bring a baby", "Bilingual"], 0, 0),
              ([2, 4], "14:00", "Chair Yoga", "Chair", 45, "beginner", 1, False, ["Chair-friendly", H], 1, 0),
              ([1, 3], "18:30", "Evening Prenatal", "Prenatal", 60, "all", 2, False, ["Prenatal-safe", "Bilingual"], 0, 0),
              ([5], "09:30", "Family Yoga", "Kids & family", 45, "all", 1, False, ["Bring a baby", H], 1, 0)],
     "workshops": [(6, "13:00", "Birth Prep for Partners", "Prenatal", 150, 60, 0, "Breathing, comfort positions and massage for labour. Bring your partner and two pillows.")]},
    {"slug": "fleuve-yoga", "name": "Fleuve Yoga & Breath", "hood": "Verdun", "addr": "4680 rue Wellington (demo)",
     "tagline": "A quiet room by the river.", "accent": "lake", "featured": False, "weight": 3,
     "about": "Two minutes from the river path. Hatha in the morning, breathwork at dusk, yin and sound baths at night.",
     "styles": ["Hatha", "Breathwork", "Yin", "Sound"], "amen": ["Mats & props provided", "Tea bar", "Bike parking"],
     "langs": ["Français", "English"], "cancel": 12,
     "rooms": [("River room", 4, 4, ["D4"])],
     "team": [("Léa Gagnon", "lea.g", "owner", "Breathwork facilitator and hatha teacher. Grew up on Wellington.", ["Breathwork", "Hatha"], 45, 2, 8),
              ("Owen Park", "owen", "teacher", "Sound healer and yin teacher with a gong collection.", ["Yin", "Sound"], 40, 2, 8)],
     "products": [("Intro: 3 classes", "intro", 3, 21, 35, True, "Three classes in three weeks."),
                  ("Drop-in", "dropin", 1, 30, 22, False, "One class."),
                  ("10-class pack", "pack", 10, 180, 190, False, "Valid six months."),
                  ("Monthly unlimited", "unlimited", None, 30, 135, False, "Pause anytime.")],
     "week": [([0, 1, 2, 3, 4], "08:00", "Riverside Hatha", "Hatha", 60, "all", 2, False, [H, "En français"], 0, 0),
              ([0, 2, 4], "18:30", "Breathwork Circle", "Breathwork", 60, "all", 2, False, ["Trauma-informed"], 0, 0),
              ([1, 3], "18:30", "Slow Hatha", "Hatha", 60, "beginner", 1, False, [H, "Bilingual"], 0, 0),
              ([0, 1, 2, 3], "20:00", "Yin by Candlelight", "Yin", 60, "all", 1, False, ["Candlelit"], 1, 0),
              ([5, 6], "10:00", "Weekend Hatha", "Hatha", 75, "all", 2, False, [], 0, 0)],
     "workshops": [(6, "16:00", "Gong Sound Bath", "Sound", 90, 30, 1, "Lie down, cover up, let seven gongs do the rest. Mats, bolsters and blankets provided.")]},
    {"slug": "mile-end-movement", "name": "Mile End Movement", "hood": "Mile End", "addr": "5350 boul. Saint-Laurent (demo)",
     "tagline": "Ashtanga, Pilates and mobility for curious bodies.", "accent": "sun", "featured": False, "weight": 3,
     "about": "A bright loft for traditional Mysore practice at dawn, mat Pilates at lunch and a mobility lab after work.",
     "styles": ["Ashtanga", "Pilates", "Mobility"], "amen": ["Lockers", "Showers", "Bike parking"],
     "langs": ["English"], "cancel": 12,
     "rooms": [("Loft", 4, 5, [])],
     "team": [("Daniel Kowalski", "daniel.k", "owner", "Authorised Ashtanga teacher; runs the Mysore room.", ["Ashtanga"], 50, 2, 10),
              ("Yuki Sato", "yuki", "teacher", "Mat Pilates with a dancer's eye for detail.", ["Pilates"], 45, 2, 10),
              ("Priya Nair", "priya", "teacher", "Mobility coach: hips, shoulders and the joy of moving well.", ["Mobility"], 45, 2, 10)],
     "products": [("Intro month", "intro", None, 30, 79, True, "Your first month, unlimited."),
                  ("Drop-in", "dropin", 1, 30, 25, False, "One class."),
                  ("10-class pack", "pack", 10, 180, 210, False, "Valid six months."),
                  ("Monthly unlimited", "unlimited", None, 30, 159, False, "Includes Mysore.")],
     "week": [([0, 1, 2, 3, 4], "06:30", "Mysore Ashtanga", "Ashtanga", 90, "all", 4, False, [], 0, 0),
              ([0, 2, 4], "12:00", "Mat Pilates", "Pilates", 50, "all", 3, False, [], 1, 0),
              ([1, 3], "12:00", "Pilates Basics", "Pilates", 50, "beginner", 2, False, [H], 1, 0),
              ([0, 1, 2, 3], "18:00", "Mobility Lab", "Mobility", 60, "all", 2, False, [H], 2, 0),
              ([1, 3], "19:15", "Led Ashtanga Primary", "Ashtanga", 75, "intermediate", 5, False, [], 0, 0),
              ([5], "10:00", "Saturday Pilates", "Pilates", 60, "all", 3, False, [], 1, 0)],
     "workshops": []},
    {"slug": "kula-laval", "name": "Kula Laval", "hood": "Laval", "addr": "1600 boul. Le Corbusier (demo)",
     "tagline": "Community yoga, pay what you can.", "accent": "moss", "featured": False, "status": "review", "weight": 0,
     "about": "A community studio opening soon in Laval, with pay-what-you-can classes every evening.",
     "styles": ["Hatha", "Vinyasa"], "amen": ["Free parking"], "langs": ["Français", "English"], "cancel": 6,
     "rooms": [("Main hall", 5, 6, [])],
     "team": [("Raj Mehta", "raj", "owner", "Community organiser and hatha teacher.", ["Hatha"], 0, 0, 0)],
     "products": [("Pay what you can", "dropin", 1, 30, 10, False, "Suggested $10.")], "week": [], "workshops": []},
]

REVIEWS = [
    ("sage-and-stone", "Yin & Yoga Nidra", 5, "Best sleep of my week, every week. Inès has the kindest voice and the blankets are heavenly."),
    ("sage-and-stone", "Sunrise Vinyasa", 5, "Theo gives options for every level so I never feel lost at 7 am. The tea after class is a lovely touch."),
    ("sage-and-stone", "Yoga 101: Foundations", 5, "I was nervous as a total beginner. Samir explained everything twice, in French and English, and made us laugh."),
    ("sage-and-stone", "Strong Flow", 4, "Challenging and fun with live music. Gets busy, so book early."),
    ("sage-and-stone", "Saturday Slow Flow", 5, "My Saturday ritual. Maya remembers everyone's name."),
    ("sage-and-stone", "Alignment Hatha", 4, "I finally understand what my shoulders are supposed to do in down dog."),
    ("lumen-hot-yoga", "Hot Vinyasa", 5, "Proper heat without the stuffy air. Showers are spotless."),
    ("lumen-hot-yoga", "Hot Yin", 4, "Surprisingly relaxing in the heat. Bring a big towel!"),
    ("lumen-hot-yoga", "Hot Express", 5, "Perfect lunch break. In, sweat, out, back at my desk smiling."),
    ("petit-lotus", "Prenatal Flow", 5, "Amélie made my third trimester so much more comfortable. The breathing practice helped during labour."),
    ("petit-lotus", "Baby & Me Yoga", 5, "Nobody blinks when the baby cries. Made friends here too."),
    ("petit-lotus", "Chair Yoga", 5, "My mother (82) goes twice a week now. Nadia adapts everything."),
    ("fleuve-yoga", "Breathwork Circle", 5, "Left feeling three kilos lighter. Very safe, well guided."),
    ("fleuve-yoga", "Yin by Candlelight", 4, "Lovely quiet room. Wish there were more evening spots."),
    ("fleuve-yoga", "Riverside Hatha", 5, "Morning class then a walk by the river: perfect start to the day."),
    ("mile-end-movement", "Mobility Lab", 5, "My shoulders thank Priya. Desk-worker heaven."),
    ("mile-end-movement", "Mat Pilates", 4, "Small details, big burn. Yuki is precise and encouraging."),
    ("mile-end-movement", "Mysore Ashtanga", 5, "Daniel's Mysore room is focused and welcoming, even for newcomers."),
]
NOTES = ["Hips finally let go in pigeon.", "Came in stressed, left calm.", "Held crow for 3 breaths!", "Tired today, chose child's pose a lot. Fine.",
         "Loved the slow pace.", "Breathing felt easier.", "Lower back better after this one.", "Nidra = best nap."]
HEALTH = ["Recovering from a left knee sprain: no deep lunges please.", "Mild lower back pain; I take it easy on backbends.",
          "Pregnant, 24 weeks.", "High blood pressure: no long inversions."]
POP = {"Saturday Slow Flow": 1.1, "Strong Flow": 0.95, "Yin & Yoga Nidra": 0.85, "Sunrise Vinyasa": 0.6, "Hot Vinyasa": 0.75,
       "Prenatal Flow": 0.9, "Breathwork Circle": 0.8, "Mysore Ashtanga": 0.55, "Mobility Lab": 0.7, "Weekend Hot Flow": 0.8,
       "Restorative & Sound": 0.85, "Yoga 101: Foundations": 0.7}


def state():
    return C.get_setting("demo", "never")  # "never" | "loaded" | "removed"


def ensure_loaded():
    if state() == "never":
        load()


def _email(handle):
    return handle + ".demo@example.com"


def _local(day, hhmm):
    h, m = [int(x) for x in hhmm.split(":")]
    return dt.datetime(day.year, day.month, day.day, h, m, tzinfo=TZ).astimezone(dt.timezone.utc)


def _today():
    return C.now().astimezone(TZ).date()


def _person(name, handle, days_ago=60):
    email = _email(handle)
    u = app_tables.users.get(email=email) or app_tables.users.add_row(email=email, enabled=False)
    u.update(display_name=name, is_demo=True, signed_up=C.now() - dt.timedelta(days=days_ago))
    return u


def _key(v):
    if hasattr(v, "get_id"):
        return v.get_id()
    if isinstance(v, dt.datetime):
        return C.iso(v)
    return v


def _bulk(table, rows, keys=None):
    """Add many rows in few round trips (add_rows, 300 at a time). Returns the new rows in order: from add_rows,
    or found again by `keys` columns if this Anvil version's add_rows doesn't return them."""
    if not rows:
        return []
    adder = getattr(table, "add_rows", None)
    if adder is None:
        return [table.add_row(**r) for r in rows]
    out = []
    complete = True
    for i in range(0, len(rows), 300):
        chunk = rows[i:i + 300]
        got = adder(chunk)
        got = list(got) if got is not None else []
        if len(got) != len(chunk):
            complete = False
        out += got
    if complete or keys is None:
        return out
    index = {}
    for r in table.search(is_demo=True):
        index[tuple(_key(r[k]) for k in keys)] = r
    return [index.get(tuple(_key(d[k]) for k in keys)) for d in rows]


def _students(rng, now):
    names, seen = [], set()
    i = 0
    while len(names) < N_STUDENTS:
        f, l = FIRST[i % len(FIRST)], LAST[(i * 7 + i // len(FIRST)) % len(LAST)]
        i += 1
        if (f, l) in seen:
            continue
        seen.add((f, l))
        names.append((f + " " + l, "student%02d" % len(names)))
    rows = [dict(email=_email(h), enabled=False, display_name=n, is_demo=True,
                 signed_up=now - dt.timedelta(days=rng.randint(15, 400))) for n, h in names]
    return _bulk(app_tables.users, rows, keys=("email",))


def load():
    remove(remember=False)
    rng = random.Random(7)
    now = C.now()
    today = _today()
    ctx = {"studios": {}, "students": _students(rng, now)}
    for spec in STUDIOS:
        team_users = [_person(t[0], t[1], 300) for t in spec["team"]]
        s = app_tables.studios.add_row(
            slug=spec["slug"], name=spec["name"], tagline=spec["tagline"], about=spec["about"], neighbourhood=spec["hood"],
            address=spec["addr"], city="Laval" if spec["hood"] == "Laval" else "Montréal", styles=spec["styles"],
            amenities=spec["amen"], languages=spec["langs"], accent=spec["accent"], status=spec.get("status", "live"),
            featured=spec["featured"], cancel_hours=spec["cancel"], waiver_text=None, owner=team_users[0], rating=0, rating_n=0,
            created=now - dt.timedelta(days=200), is_demo=True)
        rooms = [app_tables.rooms.add_row(studio=s, name=r[0], rows=r[1], cols=r[2], blocked=r[3], is_demo=True) for r in spec["rooms"]]
        staff = []
        for t, u in zip(spec["team"], team_users):
            staff.append(app_tables.staff.add_row(studio=s, user=u, email=u["email"], name=t[0], bio=t[3], role=t[2], teaches=True,
                                                  styles=t[4], pay_base=t[5], pay_per_head=t[6], pay_after=t[7], active=True,
                                                  created=now - dt.timedelta(days=200), is_demo=True))
        products = {}
        for i, p in enumerate(spec["products"]):
            products.setdefault(p[1], []).append(app_tables.products.add_row(
                studio=s, name=p[0], kind=p[1], credits=p[2], days=p[3], price=p[4], intro_only=p[5], about=p[6],
                active=True, order=i, is_demo=True))
        ctx["studios"][spec["slug"]] = {"row": s, "rooms": rooms, "staff": staff, "products": products, "spec": spec}
    _passes(ctx, rng, now)
    for slug, st in ctx["studios"].items():
        first = today - dt.timedelta(days=HISTORY.get(slug, 3))
        _make_classes(st, first, today + dt.timedelta(days=AHEAD), rng, ctx["members"].get(slug, []))
    C.set_setting("demo_through", (today + dt.timedelta(days=AHEAD)).isoformat())
    _extras(ctx, rng, now)
    for st in ctx["studios"].values():
        _rating(st["row"])
    C.set_setting("demo", "loaded")
    return counts()


def _passes(ctx, rng, now):
    """Each student practises at one studio (some at two), with a pass and a signed waiver at each."""
    live = [k for k in ctx["studios"] if ctx["studios"][k]["spec"].get("status", "live") == "live"]
    weights = [ctx["studios"][k]["spec"]["weight"] for k in live]
    plan = []
    for i, u in enumerate(ctx["students"]):
        home = rng.choices(live, weights)[0]
        places = [home]
        if rng.random() < 0.3:
            places.append(rng.choice([k for k in live if k != home]))
        for j, slug in enumerate(places):
            prods = ctx["studios"][slug]["products"]
            roll = rng.random()
            kind = "intro" if (j == 1 or roll < 0.16) else ("unlimited" if roll < 0.58 else "pack")
            if kind not in prods:
                kind = "pack" if "pack" in prods else "dropin"
            prod = prods[kind][-1] if kind == "pack" else prods[kind][0]
            started = now - dt.timedelta(days=rng.randint(3, 12) if kind == "intro" else rng.randint(12, 30))
            plan.append((u, slug, prod, kind, started))
            if kind == "intro" and (now - started).days >= 6 and rng.random() < 0.4:
                nxt = (prods.get("unlimited") or prods.get("pack") or [None])[0]
                if nxt is not None:  # liked it: bought a pack or membership after the intro
                    plan.append((u, slug, nxt, nxt["kind"], now - dt.timedelta(days=rng.randint(0, 2))))
    pass_rows, waiver_rows, signed_up = [], [], set()
    for (u, slug, prod, kind, started) in plan:
        s = ctx["studios"][slug]["row"]
        days = prod["days"] or 30
        pass_rows.append(dict(user=u, studio=s, product=prod, name=prod["name"], kind=kind, credits_total=prod["credits"],
                              credits_left=prod["credits"], starts=started, expires=started + dt.timedelta(days=days if kind == "intro" else max(days, 40)),
                              paused_until=None, paid=rng.random() > 0.12 or (prod["price"] or 0) == 0,
                              pay_method=rng.choice(["card", "card", "e-transfer", "cash"]), price=prod["price"] or 0,
                              source="buy", created=started, is_demo=True))
        if (u.get_id(), slug) in signed_up:  # a second pass at the same studio: they signed the waiver already
            continue
        signed_up.add((u.get_id(), slug))
        share = rng.random() < 0.15
        waiver_rows.append(dict(studio=s, user=u, signed=started, signature=u["display_name"], emergency="",
                                health=rng.choice(HEALTH) if share else "", share=share, is_demo=True))
    passes = _bulk(app_tables.passes, pass_rows, keys=("user", "studio", "created"))
    _bulk(app_tables.waivers, waiver_rows)
    ctx["members"] = {k: [] for k in live}
    for (u, slug, prod, kind, started), p in zip(plan, passes):
        again = any(m["user"].get_id() == u.get_id() for m in ctx["members"][slug])  # bought a second pass after the intro week
        freq = {"unlimited": rng.uniform(2, 4.5), "pack": rng.uniform(0.8, 2), "intro": rng.uniform(2, 4)}.get(kind, 1)
        # A few members drift away: they came in the first week of the history and not since.
        stop = now - dt.timedelta(days=rng.randint(15, 19)) if kind in ("unlimited", "pack") and rng.random() < 0.12 else None
        ctx["members"][slug].append({"user": u, "pass": p, "kind": kind, "since": started if kind == "intro" or again else started - dt.timedelta(days=60),
                                     "seen": False, "freq": freq, "credits": prod["credits"], "stop": stop})


def _one_each(people):
    """One entry per person (someone with an intro pass and a later pack is still one person): the newest pass wins."""
    best = {}
    for m in people:
        k = m["user"].get_id()
        if k not in best or m["since"] > best[k]["since"]:
            best[k] = m
    return [m for m in people if best[m["user"].get_id()] is m]


def _pick(rng, people, n):
    """n distinct people, the keen ones (high freq) more likely."""
    keyed = sorted(people, key=lambda m: rng.random() ** (1.0 / max(0.1, m["freq"])), reverse=True)
    return keyed[:n]


def _make_classes(st, first_day, last_day, rng, members):
    """Classes from the weekly template for first_day..last_day (inclusive), with bookings for the past and next week."""
    spec, s = st["spec"], st["row"]
    now = C.now()
    today = _today()
    plan = []
    day = first_day
    while day <= last_day:
        for (wds, hhmm, title, style, mins, level, inten, heated, tags, ti, ri) in spec["week"]:
            if day.weekday() in wds:
                plan.append((day, hhmm, title, style, mins, level, inten, heated, tags, ti, ri, "class", 0, _about(style, title)))
        for (wd, hhmm, title, style, mins, price, ti, about) in spec["workshops"]:
            if day.weekday() == wd and 3 <= (day - today).days <= 9:
                plan.append((day, hhmm, title, style, mins, "all", 2, False, ["Props provided"], ti, 0, "workshop", price, about))
        day += dt.timedelta(days=1)
    rows: list = []
    for (day, hhmm, title, style, mins, level, inten, heated, tags, ti, ri, kind, price, about) in plan:
        room = st["rooms"][ri]
        cap = 12 if kind == "workshop" else st["caps"][ri] if "caps" in st else _cap(room)
        rows.append(dict(studio=s, series="demo-%s-%s-%s" % (spec["slug"], title, hhmm), title=title, style=style, level=level,
                         intensity=inten, heated=heated, tags=tags, about=about, teacher=st["staff"][ti], orig_teacher=st["staff"][ti],
                         room=room, start=_local(day, hhmm), minutes=mins, capacity=cap, booked=0, waiting=0, kind=kind,
                         price=price, status="scheduled", cancel_note="", is_demo=True))
    classes = _bulk(app_tables.classes, rows, keys=("series", "start"))
    spots_by_room = {}
    for room in st["rooms"]:
        blocked = room["blocked"] or []
        spots_by_room[room.get_id()] = ["%s%d" % (chr(65 + r), k + 1) for r in range(int(room["rows"])) for k in range(int(room["cols"]))
                                        if "%s%d" % (chr(65 + r), k + 1) not in blocked]
    bookings = []
    for d, c in zip(rows, classes):
        if c is None:
            continue
        start = d["start"]
        days_out = (start - now).total_seconds() / 86400
        if days_out > 8 or not members:
            continue
        cap = d["capacity"]
        base = 0.5 if d["kind"] == "workshop" else POP.get(d["title"], 0.45)
        fade = 1.0 if days_out < 0 else max(0.3, 1 - days_out / 8)
        want = int(round(cap * base * rng.uniform(0.6, 1.0) * fade))
        if d["title"] == "Saturday Slow Flow" and 0 < days_out < 7:
            want = cap + 3
        people = _one_each([m for m in members if m["since"] < start + dt.timedelta(hours=12) and (m.get("stop") is None or start < m["stop"])])
        spots = list(spots_by_room.get(d["room"].get_id(), []))
        rng.shuffle(spots)
        n_in = waiting = 0
        full = want > cap  # the demo's full class: keep picking past people whose pack ran out, until it's full + 3 waiting
        for m in _pick(rng, people, len(people) if full else want):
            if full and n_in + waiting >= want:
                break
            past = start < now
            if d["kind"] != "workshop" and m["credits"] is not None and m["credits"] <= 0:
                continue
            if past:
                status = rng.choices(["checked_in", "booked", "no_show", "late"], [86, 6, 4, 4])[0]
            else:
                status = "waitlist" if n_in >= cap else "booked"
            if past and n_in >= cap:
                continue
            first = not m["seen"] and m["kind"] == "intro"
            if status != "waitlist":
                m["seen"] = True
                if d["kind"] != "workshop" and m["credits"] is not None:
                    m["credits"] -= 1
            mood = rng.choices([3, 4, 5], [2, 5, 4])[0] if status == "checked_in" and rng.random() < 0.45 else None
            bookings.append(dict(klass=c, user=m["user"], studio=s, pass_used=m["pass"] if d["kind"] != "workshop" else None,
                                 start=start, spot=spots.pop() if (spots and status != "waitlist" and rng.random() < 0.75) else None,
                                 status=status, wl_at=start - dt.timedelta(days=2, minutes=-waiting) if status == "waitlist" else None,
                                 first_visit=first, grace=False, forgiven=False, walkin_name=None, mood=mood,
                                 note=rng.choice(NOTES) if mood and rng.random() < 0.4 else "", reviewed=False,
                                 created=start - dt.timedelta(days=rng.uniform(0.3, 4)), updated=start, is_demo=True))
            if status == "waitlist":
                waiting += 1
            elif status in Mo.TAKES_MAT:
                n_in += 1
        c.update(booked=n_in, waiting=waiting)
    _bulk(app_tables.bookings, bookings)
    for m in members:
        p = m["pass"]
        if p is not None and m["credits"] is not None and p["credits_left"] != max(0, m["credits"]):
            p["credits_left"] = max(0, m["credits"])
    return classes


def _cap(room):
    return (room["rows"] or 0) * (room["cols"] or 0) - len(room["blocked"] or [])


def _about(style, title):
    return {
        "Vinyasa": "Breath-led flow linking poses together. Expect sun salutations, standing poses and a long savasana.",
        "Hatha": "Steady, alignment-focused postures held for a few breaths, with time to learn the details.",
        "Yin": "Long, passive holds (3-5 minutes) for hips, spine and fascia. Quiet and deeply calming.",
        "Restorative": "Fully supported rest with bolsters and blankets. Nothing to achieve.",
        "Hot": "Practised in a heated room. Bring water and a towel; take breaks whenever you need.",
        "Ashtanga": "The traditional Ashtanga sequence. Mysore classes are self-paced with hands-on guidance.",
        "Prenatal": "Safe, supportive movement and breathing for every trimester. Tell the teacher how many weeks you are.",
        "Pilates": "Mat Pilates for core strength, posture and control.",
        "Breathwork": "Guided breathing practices to energise or settle the nervous system. Lying down, eyes closed.",
        "Mobility": "Joint-by-joint mobility work and active stretching. Great for desk workers and athletes.",
        "Kids & family": "Gentle, playful yoga with your little one. Bring a blanket for baby.",
        "Chair": "Yoga seated on and standing beside a chair. Accessible, gentle and surprisingly strong.",
        "Sound": "Relax lying down while gongs and bowls wash over you.",
    }.get(style, title)


def _extras(ctx, rng, now):
    by_slug = ctx["studios"]
    for slug, title, stars, text in REVIEWS:
        st = by_slug[slug]
        done = [b for b in app_tables.bookings.search(studio=st["row"], status="checked_in")
                if b["klass"] is not None and b["klass"]["title"] == title and not b["reviewed"]]
        if not done:
            continue
        b = rng.choice(done)
        b["reviewed"] = True
        k = b["klass"]
        app_tables.reviews.add_row(studio=st["row"], klass=k, teacher=k["teacher"], user=b["user"], booking=b, stars=stars, text=text,
                                   created=C.aware(k["start"]) + dt.timedelta(hours=3), hidden=False,
                                   reply="Thank you so much! See you on the mat." if stars == 5 and rng.random() < 0.4 else "",
                                   reply_at=C.aware(k["start"]) + dt.timedelta(hours=9) if stars == 5 else None, is_demo=True)
    sage = by_slug["sage-and-stone"]
    maya, theo, samir = sage["staff"][0], sage["staff"][1], sage["staff"][3]
    future = sorted([c for c in app_tables.classes.search(studio=sage["row"], status="scheduled") if C.aware(c["start"]) > now],
                    key=lambda c: C.aware(c["start"]))
    sunday = [c for c in future if c["title"] == "Sunday Vinyasa"]
    if sunday:
        app_tables.subs.add_row(klass=sunday[0], studio=sage["row"], from_staff=theo, reason="Climbing trip up north", status="open",
                                filled_by=None, created=now - dt.timedelta(hours=20), filled_at=None, is_demo=True)
    lunch = [c for c in future if c["title"] == "Lunch Flow"]
    if lunch:
        lunch[0]["teacher"] = samir
        app_tables.subs.add_row(klass=lunch[0], studio=sage["row"], from_staff=maya, reason="Supplier meeting", status="filled",
                                filled_by=samir, created=now - dt.timedelta(days=2), filled_at=now - dt.timedelta(days=1, hours=20), is_demo=True)
    owner = sage["row"]["owner"]
    C.notify(owner, sage["row"], "sub", "Theo needs a sub for Sunday Vinyasa", "Climbing trip up north. Samir or Inès could cover.", "#teach")
    C.notify(owner, sage["row"], "pause", "Hannah paused her membership", "For 2 weeks. Her end date moved by the same time.", "")
    C.notify(owner, sage["row"], "studio", "Three first-timers this week", "Say hi at the desk: they have a leaf next to their name in the roster.", "#manage")
    members = _one_each(ctx["members"].get("sage-and-stone", []))
    for m in members[:8]:
        app_tables.follows.add_row(user=m["user"], studio=sage["row"], created=now, is_demo=True)
    for i, m in enumerate([m for m in members if m["kind"] in ("pack", "unlimited")][:3]):
        app_tables.friend_passes.add_row(studio=sage["row"], sender=m["user"], code="demo%d%d" % (i, rng.randint(1000, 9999)),
                                         created=now - dt.timedelta(days=5 + i), claimed_by=None, claimed_at=None, is_demo=True)
    intro_users = [m for m in members if m["kind"] == "intro"]
    if intro_users:
        u = intro_users[0]["user"]
        C.notify(u, sage["row"], "nudge", "A note from Sage & Stone Yoga", "So glad you came this week! Your intro week ends soon.", "#studio/sage-and-stone")


def _rating(s):
    rows = [r for r in app_tables.reviews.search(studio=s) if not r["hidden"]]
    s.update(rating=round(sum(r["stars"] for r in rows) / len(rows), 2) if rows else 0, rating_n=len(rows))


def dedupe_once():
    """One-time cleanup (Nov 2026): demo data loaded before the fix gave some people two waivers at one studio and two
    bookings in one class (the Class list crash, 'Élise D.' twice on the kiosk). Demo rows only; real data is untouched."""
    if C.get_setting("demo_dedupe_v1"):
        return 0
    C.set_setting("demo_dedupe_v1", C.now().isoformat())  # first, so a failure can never make it run on every visit
    removed = 0
    seen = set()
    for w in app_tables.waivers.search(is_demo=True):
        if w["studio"] is None or w["user"] is None:
            continue
        k = (w["studio"].get_id(), w["user"].get_id())
        if k in seen:
            w.delete()
            removed += 1
        else:
            seen.add(k)
    groups = {}
    for b in app_tables.bookings.search(is_demo=True):
        if b["user"] is not None and b["klass"] is not None:
            groups.setdefault((b["klass"].get_id(), b["user"].get_id()), []).append(b)
    for rows in groups.values():
        if len(rows) < 2:
            continue
        keep = next((b for b in rows if len(app_tables.reviews.search(booking=b))), rows[0])  # keep the one a review points at
        klass = keep["klass"]
        for b in rows:
            if b is not keep and not len(app_tables.reviews.search(booking=b)):
                b.delete()
                removed += 1
        Mo.recount(klass)
    return removed


def top_up():
    """Keep the demo schedule ~12 days ahead (called from Discover; one settings read when there's nothing to do)."""
    if state() != "loaded":
        return 0
    dedupe_once()
    today = _today()
    through = C.get_setting("demo_through")
    try:
        through = dt.date.fromisoformat(through) if through else today
    except ValueError:
        through = today
    if through >= today + dt.timedelta(days=AHEAD - 3):
        return 0
    C.set_setting("demo_through", (today + dt.timedelta(days=AHEAD)).isoformat())
    rng = random.Random(today.toordinal())
    made = 0
    now = C.now()
    for spec in STUDIOS:
        s = app_tables.studios.get(slug=spec["slug"])
        if s is None or not s["is_demo"] or not spec["week"]:
            continue
        rooms_by_name = {r["name"]: r for r in app_tables.rooms.search(studio=s)}
        staff_by_name = {t["name"]: t for t in app_tables.staff.search(studio=s)}
        rooms = [rooms_by_name.get(r[0]) for r in spec["rooms"]]
        staff = [staff_by_name.get(t[0]) for t in spec["team"]]
        if None in rooms or None in staff:
            continue
        members = []
        for p in app_tables.passes.search(studio=s, kind="unlimited"):
            if p["is_demo"]:
                if C.aware(p["expires"]) < now + dt.timedelta(days=AHEAD):
                    p["expires"] = C.aware(p["expires"]) + dt.timedelta(days=30)
                members.append({"user": p["user"], "pass": p, "kind": "unlimited", "since": C.aware(p["starts"]), "seen": True,
                                "freq": 3, "credits": None})
        st = {"spec": spec, "row": s, "rooms": rooms, "staff": staff}
        made += len(_make_classes(st, max(through + dt.timedelta(days=1), today), today + dt.timedelta(days=AHEAD), rng, members))
    return made


def sample_member(user):
    """Give a real account a believable history (the local dev server's Ana, and tests). Not used by the live app."""
    now = C.now()
    sage = app_tables.studios.get(slug="sage-and-stone")
    fleuve = app_tables.studios.get(slug="fleuve-yoga")
    if sage is None:
        return
    prod = [p for p in app_tables.products.search(studio=sage, kind="unlimited")][0]
    p = app_tables.passes.add_row(user=user, studio=sage, product=prod, name=prod["name"], kind="unlimited", credits_total=None,
                                  credits_left=None, starts=now - dt.timedelta(days=16), expires=now + dt.timedelta(days=14),
                                  paused_until=None, paid=True, pay_method="card", price=prod["price"], source="buy",
                                  created=now - dt.timedelta(days=16), is_demo=False)
    app_tables.waivers.add_row(studio=sage, user=user, signed=now - dt.timedelta(days=16), signature=C.name_of(user), emergency="",
                               health="Tight hamstrings, old wrist injury (right).", share=True, is_demo=False)
    past = sorted([c for c in app_tables.classes.search(studio=sage, status="scheduled") if C.aware(c["start"]) < now - dt.timedelta(hours=2)],
                  key=lambda c: C.aware(c["start"]))
    picks = [c for c in past if c["title"] in ("Yin & Yoga Nidra", "Sunrise Vinyasa", "Saturday Slow Flow", "Strong Flow", "Restorative & Sound")]
    picks = picks[::2][-7:]
    for i, c in enumerate(picks):
        app_tables.bookings.add_row(klass=c, user=user, studio=sage, pass_used=p, start=c["start"], spot=None,
                                    status="checked_in", wl_at=None, first_visit=i == 0, grace=False, forgiven=False, walkin_name=None,
                                    mood=[4, 5, 3, 5, 4, 5, 4][i % 7], note=NOTES[i % len(NOTES)] if i % 2 == 0 else "", reviewed=False,
                                    created=C.aware(c["start"]) - dt.timedelta(days=1), updated=C.aware(c["start"]), is_demo=False)
        Mo.recount(c)
    future = sorted([c for c in app_tables.classes.search(studio=sage, status="scheduled") if C.aware(c["start"]) > now + dt.timedelta(hours=14)],
                    key=lambda c: C.aware(c["start"]))
    for c in [c for c in future if c["title"] == "Yin & Yoga Nidra"][:1]:
        app_tables.bookings.add_row(klass=c, user=user, studio=sage, pass_used=p, start=c["start"], spot=None, status="booked", wl_at=None,
                                    first_visit=False, grace=False, forgiven=False, walkin_name=None, mood=None, note="", reviewed=False,
                                    created=now, updated=now, is_demo=False)
        Mo.recount(c)
    for c in [c for c in future if c["title"] == "Saturday Slow Flow"][:1]:
        app_tables.bookings.add_row(klass=c, user=user, studio=sage, pass_used=p, start=c["start"], spot=None, status="waitlist", wl_at=now,
                                    first_visit=False, grace=False, forgiven=False, walkin_name=None, mood=None, note="", reviewed=False,
                                    created=now, updated=now, is_demo=False)
        Mo.recount(c)
    if fleuve is not None:
        intro = [x for x in app_tables.products.search(studio=fleuve, kind="intro")][0]
        app_tables.passes.add_row(user=user, studio=fleuve, product=intro, name=intro["name"], kind="intro", credits_total=intro["credits"],
                                  credits_left=intro["credits"], starts=now - dt.timedelta(days=2), expires=now + dt.timedelta(days=19),
                                  paused_until=None, paid=False, pay_method="", price=intro["price"], source="buy",
                                  created=now - dt.timedelta(days=2), is_demo=False)
        app_tables.follows.add_row(user=user, studio=fleuve, created=now, is_demo=False)
    app_tables.follows.add_row(user=user, studio=sage, created=now, is_demo=False)
    for t in app_tables.staff.search(studio=sage):
        if t["name"] == "Inès Ozola":
            app_tables.follows.add_row(user=user, teacher=t, created=now, is_demo=False)
    C.notify(user, sage, "waitlist", "You're on the waitlist for Saturday Slow Flow",
             "We'll move you in automatically if a mat opens up.", "#practice")
    C.notify(user, sage, "nudge", "A note from Sage & Stone Yoga",
             "Hi! Inès is running a Yoga Nidra workshop soon, and we thought of you. - Maya", "#studio/sage-and-stone")


def remove(remember=True):
    """Delete the demo: demo studios with everything at them (real people's bookings there too), then demo people."""
    for s in app_tables.studios.search(is_demo=True):
        for name in STUDIO_TABLES:
            for r in getattr(app_tables, name).search(studio=s):
                r.delete()
        for t in app_tables.staff.search(studio=s):
            for f in app_tables.follows.search(teacher=t):
                f.delete()
            t.delete()
        for f in app_tables.follows.search(studio=s):
            f.delete()
    for name in DEMO_TABLES:
        for r in getattr(app_tables, name).search(is_demo=True):
            r.delete()
    for u in app_tables.users.search(is_demo=True):
        for name in ("notices", "follows", "bookings", "passes", "waivers"):
            for r in getattr(app_tables, name).search(user=u):
                r.delete()
        for r in app_tables.friend_passes.search(sender=u):
            r.delete()
        for r in app_tables.staff.search(user=u):
            r.delete()
        u.delete()
    if remember:
        C.set_setting("demo", "removed")
    return counts()


def counts():
    out = {"users": len(app_tables.users.search(is_demo=True))}
    for name in ("studios", "classes", "bookings", "passes", "reviews"):
        out[name] = len(getattr(app_tables, name).search(is_demo=True))
    return out
