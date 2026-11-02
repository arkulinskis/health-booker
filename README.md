# Health Booker

A yoga-studio marketplace and studio back office, built as a friendlier answer to Mindbody. Students find and book
classes across Montréal's independent studios with **one account**: they pick their mat, join fair waitlists, keep a
practice journal and hold every studio's pass in one wallet. Studio owners, front desks and teachers run their
schedule, passes, class lists, subs, teacher pay, clients and insights, with **no commission, no contract and a
free data export**. Built on [Anvil](https://anvil.works).

- **App repo:** github.com/arkulinskis/health-booker (branch `master`). Anvil pulls `master`.
- **Live:** https://health-booker.anvil.app

## What it does

**For everyone (no account needed to look):**
- **Landing page** for both audiences: students, plus a "what studios told us / what we do" section built on the
  pain points of the incumbents (stacked fees and marketplace commissions, 12-24-month contracts, paid data export,
  competitors shown to your students, tier-gated pick-a-spot, sub scrambles, spreadsheet pay, dated dashboard).
- **Discover** (`#discover`): every live studio's classes for the next 7 days; day strip with counts; search; style and
  neighbourhood filters; chips for time of day, beginner-friendly, heated / not heated, en français, mats left,
  workshops, following; filters remembered. **Class matcher**: four questions (how you want to feel, experience,
  when, heat) → three suggested classes with reasons. **Studios** tab with accent-coloured cards and intro offers.
- **Studio page** (`#studio/<slug>`): schedule (one week, "show the following week"), pricing, teachers, reviews,
  about + amenities + policies + waiver. Share sheet. **Direct booking link** `#studio/<slug>/solo` hides the
  marketplace navigation, so a studio can put it on Instagram/its website without showing competitors.
- **Class page** (`#class/<id>`): details, intensity, level, tags, sub notice, teacher bio + reviews, the room with
  **pick-a-mat**, which pass to use, cancellation deadline.

**For students (signed in):**
- **Booking flow:** first time at a studio → a 20-second **waiver** (typed signature, optional health notes with a
  "show my teachers" switch, emergency contact) → **choose a pass** (intro offers first, shown only to first-timers;
  paid at the studio, no card payments yet) → **booked**, with a breathing-circle confirmation and an .ics calendar file.
- **Waitlists:** full classes take a waitlist (no credit spent); when a mat frees up the oldest waiter is moved in
  automatically and messaged. Moved in inside the cancel window → they can still cancel for free ("grace").
- **Cancel:** free until the studio's window (shown before booking); later = late cancel (credit used). Studio
  cancellations refund automatically and message everyone.
- **My practice** (`#practice`): stats (classes this month, weeks-in-a-row streak, hours, how you usually leave),
  **Upcoming** (mat, pass, calendar, cancel/leave waitlist), **Journal** (12-week heatmap, styles, mood-after-class
  line, every class with its reflection; add mood + note + optional review), **Wallet** (passes at every studio,
  pay-at-desk badge, pause a membership 1-4 weeks, late cancels/no-shows, friend passes), **Following**.
- **Inbox** (bell with unread count): waitlist moves, cancellations, subs, studio notes, review replies, forgiven credits.
- **Friend passes:** pack/membership holders share up to 2 links a month per studio (`#gift/<code>`): a free first class.
- **Reviews:** only after attending; first name shown; studios can reply.

**For teachers** (`#teach`, any active team member):
- Next 2 weeks of classes across studios with booked/capacity and first-timers; **class list** with check-in and
  shared health notes; **Ask for a sub** → colleagues are messaged → one taps **I'll cover it** → the class moves to
  them, the owner, the original teacher and the booked students are told. **Pay** statement per month
  (base + per head above a threshold; CSV download). Their reviews and rating.

**For studio owners and front desk** (`#manage/<slug>/<tab>`; admins can manage every studio):
- **Today:** day navigation, mats booked/fill, first-timers, passes sold, passes to collect; class timeline with fill
  bars and "on now"; **class list** (check in, no-show, forgive late cancels, mark paid, add walk-ins by name or account
  email, milestone badges like "10th class!"); unpaid passes to collect.
- **Schedule:** week grid; **new class** (style, level, teacher, room, mats, intensity, heated, tags, workshop price,
  repeat weekly for up to 12 weeks); edit one or "this and following"; cancel (with message + refunds) / restore.
- **Clients:** tags (new, member, intro, drifting, unpaid, pass ending) with counts, search, **personal messages**
  (templated per tag, one or many), client detail (passes with mark-paid, visits, waiver + shared health notes), CSV.
- **Pricing:** passes (intro, drop-in, pack, membership): credits, validity, price, first-visit only, on sale.
- **Team:** invite by email (access when they sign in), role (owner/desk/teacher), styles, bio, pay rule with a live
  example; this month's classes, average students, pay, rating; sub log.
- **Insights:** 7 days / 4 weeks / 3 months: visits, fill, passes sold, no-shows, new students, mood; passes sold per
  day, by kind, fill heatmap (weekday × hour), intro funnel (started → came back → bought), top classes, teachers.
- **Reviews:** public replies, hide abusive reviews (they stop counting).
- **Settings:** profile, styles, amenities, languages, accent colour, cancel window, waiver text, **rooms editor**
  (rows × mats, tap to block a pillar), share links, kiosk link, **CSV export** of clients, bookings and passes.
- **Check-in kiosk** (`#kiosk/<slug>`): full-screen tablet page, students tap their name, "Welcome back" breath.
- **Open a studio** (`#open`): one-page form with live preview; creates the studio (in review), a room, the owner
  as staff and four starter passes.

**For admins** (`#admin`; arkulinskis@gmail.com becomes an admin on first sign-in):
- **Overview** (people, live studios, studios in review, classes next 7 days, bookings this week), **Studios**
  (publish / pause / feature, link to manage), **Feedback inbox**, **Users**, **Demo data**.

**Demo:** six fictional Montréal studios (Sage & Stone Yoga, Lumen Hot Yoga, Petit Lotus, Fleuve Yoga & Breath,
Mile End Movement, and Kula Laval in review), 18 teachers, ~140 students, three weeks of history at Sage & Stone, a
rolling schedule ~12 days ahead (topped up automatically), reviews, an open and a filled sub request, a full class
with a waitlist. All fictional; removable in Admin → Demo data.

## Setting it up in Anvil (once)

1. In the Anvil editor: **Create app → Clone from GitHub**, and paste `https://github.com/arkulinskis/health-booker`.
2. **Users** service: email + password and "Continue with Google", sign-up allowed (already set in `anvil.yaml`; check it).
3. Open the app in the editor. If it shows a **Schema Mismatch** alert, choose **"The schema of the source code is correct"** so Anvil creates the tables.
4. **Run** it and sign up with **arkulinskis@gmail.com** straight away (that account becomes the admin).
5. **Publish** (Publish → public URL, or your own domain).

<!-- libraries:start -->
## Libraries and outside services

What this project uses besides its own code. Generated by `APP_MAKER/tools/libraries.py`; to change it, edit `APP_MAKER/libraries/catalog.py` and re-run the script.

| Name | How it gets in | Used here for |
|---|---|---|
| [Google Fonts](https://fonts.google.com) | Loaded from a CDN | DM Sans, Fraunces |

**Built into the browser:** localStorage, Clipboard, File downloads (Blob).

**Anvil platform:** Anvil, Anvil Data Tables, Anvil JS bridge (anvil.js), Anvil Users.

**Build and test tools (not shipped):** Node.js, PyYAML, Headless Chrome (DevTools Protocol).

<!-- libraries:end -->

## Working on it

See `.claude/skills/healthbooker/SKILL.md`. In short:

```
python -I tools/check.py --ui                    # syntax, server tests, headless UI tests → ALL CHECKS PASSED
python -I tools/preview/devserver.py 8765        # local app: ?as=ana (student), ?as=maya (owner), ?as=theo (teacher), ?as=admin
python tools/deploy.py                           # dry run (needs PyYAML, so no -I)
python tools/deploy.py --push "Message"          # deploy: commit + push to GitHub, Anvil pulls it
```

## Project layout

```
web/            core.js/core.css (engine + Sage & Clay tokens), app.js (header with bell, footer), pages/*.html
                (_hb.html shared HB helpers, _mg.html back-office tabs, then one file per page)
client_code/    Main.py (the only Anvil form: bridge to the server, sign-in), legal.py
server_code/    common.py, Accounts.py, Feedback.py, Admin.py, DemoData.py, legal_server.py,
                Model.py (rules + dicts), Studios.py (marketplace), Booking.py (students), Manage.py (studios), Teach.py
assets/         icon.svg (sage tile, cream leaf, clay sun) + generated PNG icons
tools/          sync_to_anvil.py (settings + table schema), deploy.py, check.py, preview/ (dev server, UI tests, screenshots), testing/
```
