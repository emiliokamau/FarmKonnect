"""Smoke-test the Global & Local Events API and run an end-to-end registration.

Run with:
    python manage.py shell < _verify_events.py
or:
    python _verify_events.py   (with DJANGO_SETTINGS_MODULE set)
"""

import json
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "farmkonnect.settings")
django.setup()

from django.test import Client, override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402

from backend.models import Event, EventRegistration  # noqa: E402

# The test client talks to "testserver"; keep the project settings untouched.
settings_override = override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
settings_override.enable()

client = Client()
ok = True


def check(label, condition, detail=""):
    global ok
    mark = "PASS" if condition else "FAIL"
    if not condition:
        ok = False
    print(f"[{mark}] {label}{(' — ' + str(detail)) if detail else ''}")


def rows(response):
    """DRF returns either a bare list or a paginated {"results": [...]}."""
    data = response.json()
    return data.get("results", data) if isinstance(data, dict) else data


# 1. Upcoming listing
r = client.get("/api/events/?window=upcoming")
check("GET /api/events/ returns 200", r.status_code == 200, r.status_code)
items = rows(r)
check("upcoming events returned", len(items) > 0, f"{len(items)} events")
check("payload has joined fields", all(k in items[0] for k in
      ("join_link", "join_mode_display", "event_type_display", "registrations_count")))

# 2. Every upcoming event has a usable access path
missing = [e["title"] for e in items
           if not (e.get("join_link") or e.get("location") or e.get("registration_url"))]
check("every event has some access path", not missing, missing[:3])

# 3. Scope filter
g_items = rows(client.get("/api/events/?scope=global&window=upcoming"))
check("scope=global filters", all(e["scope"] == "global" for e in g_items), f"{len(g_items)} global")
l_items = rows(client.get("/api/events/?scope=local&window=upcoming"))
check("scope=local filters", all(e["scope"] == "local" for e in l_items), f"{len(l_items)} local")

# 4. Search
s_items = rows(client.get("/api/events/?search=maize&window=all"))
check("search responds", isinstance(s_items, list), f"{len(s_items)} hits for 'maize'")
s2_items = rows(client.get("/api/events/?search=fao&window=all"))
check("search matches host text", len(s2_items) >= 1, f"{len(s2_items)} hits for 'fao'")

# 5. Summary
sm = client.get("/api/events/summary/")
check("GET /api/events/summary/ 200", sm.status_code == 200, sm.status_code)
summary = sm.json()
check("summary counts add up",
      summary["global"] + summary["local"] == summary["total"],
      summary)

# 6. Join details for a Google Meet event
meet = Event.objects.filter(join_mode="google_meet").first()
check("a Google Meet event exists", meet is not None)
if meet:
    ji = client.get(f"/api/events/{meet.id}/join/")
    body = ji.json()
    check("join info exposes the Meet link", body.get("join_link", "").startswith("https://meet.google.com/"),
          body.get("join_link"))
    check("join info exposes the passcode", bool(body.get("join_code")), body.get("join_code"))

    # 7. Registration flow (anonymous farmer)
    EventRegistration.objects.filter(event=meet, phone="08030000001").delete()
    payload = {"event": meet.id, "full_name": "Test Farmer", "phone": "08030000001",
               "county": "Kaduna", "wants_reminder": True}
    reg = client.post("/api/event-registrations/", data=json.dumps(payload),
                      content_type="application/json")
    check("anonymous registration accepted", reg.status_code == 201, f"{reg.status_code} {reg.content[:120]}")
    reg_body = reg.json() if reg.status_code == 201 else {}
    check("booking reference issued", str(reg_body.get("reference", "")).startswith("FK-"),
          reg_body.get("reference"))
    check("registration returns join link", bool(reg_body.get("join_link")), reg_body.get("join_link"))

    # 8. Duplicate registration is idempotent (no double booking)
    before = EventRegistration.objects.filter(event=meet, phone="08030000001").count()
    again = client.post("/api/event-registrations/", data=json.dumps(payload),
                        content_type="application/json")
    after = EventRegistration.objects.filter(event=meet, phone="08030000001").count()
    check("duplicate registration is idempotent", again.status_code == 200 and before == after == 1,
          f"{again.status_code}, rows={after}")

    # 9. Registered farmer can POST to join and gets the details
    joined = client.post(f"/api/events/{meet.id}/join/",
                         data=json.dumps({"reference": reg_body.get("reference")}),
                         content_type="application/json")
    check("join POST returns access details", joined.status_code == 200 and joined.json().get("join_link"),
          joined.status_code)

    # 10. Cancelling with the wrong reference is refused
    bad = client.post(f"/api/event-registrations/{reg_body.get('id')}/cancel/",
                      data=json.dumps({"reference": "FK-WRONG1"}), content_type="application/json")
    check("cancel with wrong reference refused", bad.status_code == 403, bad.status_code)

    # 11. Cancelling with the right reference works
    good = client.post(f"/api/event-registrations/{reg_body.get('id')}/cancel/",
                       data=json.dumps({"reference": reg_body.get("reference")}),
                       content_type="application/json")
    check("cancel with right reference works", good.status_code == 200, good.status_code)

    # clean up the test booking
    EventRegistration.objects.filter(event=meet, phone="08030000001").delete()

# 12. Invalid phone rejected
bad_phone = client.post("/api/event-registrations/",
                        data=json.dumps({"event": items[0]["id"], "full_name": "X", "phone": "12"}),
                        content_type="application/json")
check("short phone rejected", bad_phone.status_code == 400, bad_phone.status_code)

# 13. Past events hidden by default
past = Event.objects.filter(start_date__lt=timezone.now()).count()
default_ids = {e["id"] for e in items}
past_ids = set(Event.objects.filter(start_date__lt=timezone.now()).values_list("id", flat=True))
check("past events excluded from default view", not (past_ids & default_ids), f"{past} past events in db")

print()
print("RESULT:", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
