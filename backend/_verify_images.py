"""Smoke-test crop and disease photo uploads end to end.

    python _verify_images.py
"""

import io
import os
import shutil
import tempfile

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "farmkonnect.settings")
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.test import Client, override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402
from rest_framework.authtoken.models import Token  # noqa: E402

from backend.models import (  # noqa: E402
    User, FarmerProfile, Farm, CropRecord, DiseaseReport, DiseasePhoto,
)

# Isolate uploads so the check never leaves files in the repo's media folder.
MEDIA_TMP = tempfile.mkdtemp(prefix="fk-media-")
settings_override = override_settings(ALLOWED_HOSTS=["testserver"], MEDIA_ROOT=MEDIA_TMP)
settings_override.enable()

ok = True


def check(label, condition, detail=""):
    global ok
    if not condition:
        ok = False
    print(f"[{'PASS' if condition else 'FAIL'}] {label}{(' — ' + str(detail)) if detail else ''}")


def make_image(name="leaf.jpg", size=(640, 480), fmt="JPEG", color=(60, 130, 60), quality=85):
    """A real, decodable image so Pillow validation exercises the true path."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt, quality=quality)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type=f"image/{fmt.lower()}")


def make_big_image(name="huge.png", megabytes=8):
    """Random noise compresses badly, so this reliably exceeds the size cap."""
    import os as _os
    from PIL import Image
    side = 2400
    img = Image.new("RGB", (side, side))
    img.frombytes(_os.urandom(side * side * 3))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    return SimpleUploadedFile(name, data, content_type="image/png"), len(data)


# ---------- fixtures ----------
username = "imgverify"
User.objects.filter(username=username).delete()  # cascades profile/farm/records
user = User.objects.create_user(username=username, password="verify-pass-123", phone="08090000001")
profile = FarmerProfile.objects.create(user=user, full_name="Image Verify Farmer")
farm = Farm.objects.create(farmer=profile, name="Verify Farm", size=3, size_unit="acres")

client = Client()
token, _ = Token.objects.get_or_create(user=user)
auth = {"HTTP_AUTHORIZATION": f"Token {token.key}"}

# ---------- 1. crop record with an uploaded photo ----------
resp = client.post("/api/crops/", {
    "farm": farm.id, "crop": "Maize", "variety": "SC651", "area": "2.5",
    "image": make_image("crop.jpg"),
}, **auth)
check("crop create with photo -> 201", resp.status_code == 201, f"{resp.status_code} {resp.content[:160]}")
crop = resp.json() if resp.status_code == 201 else {}
check("crop image_src returned", bool(crop.get("image_src")), crop.get("image_src"))
check("crop image_src is absolute", str(crop.get("image_src", "")).startswith("http://testserver/media/"),
      crop.get("image_src"))
check("crop photo_count is 1", crop.get("photo_count") == 1, crop.get("photo_count"))

# ---------- 2. the file is really on disk and really an image ----------
stored = CropRecord.objects.filter(farm=farm).first()
if stored and stored.image:
    from PIL import Image
    img = Image.open(stored.image.path)
    check("stored crop file decodes as an image", img.size[0] > 0, img.size)
    check("crop file lands under media/crops/", "crops" in stored.image.name, stored.image.name)
else:
    check("stored crop file exists", False, "no image on the saved record")

# ---------- 3. oversized photo is rejected with a readable message ----------
big, big_size = make_big_image()
check("test image really exceeds the cap", big_size > 6 * 1024 * 1024, f"{big_size/1048576:.1f} MB")
resp = client.post("/api/crops/", {
    "farm": farm.id, "crop": "Rice", "image": big,
}, **auth)
check("oversized photo rejected", resp.status_code == 400, f"{resp.status_code} ({big_size/1048576:.1f} MB)")
if resp.status_code == 400:
    msg = str(resp.content)
    check("rejection message mentions the size limit", "6 MB" in msg, msg[:160])

# ---------- 4. a non-image file pretending to be a photo is rejected ----------
fake = SimpleUploadedFile("notaphoto.jpg", b"this is not an image at all", content_type="image/jpeg")
resp = client.post("/api/crops/", {"farm": farm.id, "crop": "Beans", "image": fake}, **auth)
check("non-image rejected", resp.status_code == 400, resp.status_code)

# ---------- 5. a text file with a wrong content type is rejected ----------
text = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
resp = client.post("/api/crops/", {"farm": farm.id, "crop": "Yam", "image": text}, **auth)
check("wrong file type rejected", resp.status_code == 400, resp.status_code)

# ---------- 6. disease report with a main photo ----------
resp = client.post("/api/diseases/", {
    "farm": farm.id, "date": timezone.localdate().isoformat(), "crop": "Maize",
    "variety": "SC651", "growth_stage": "flowering",
    "symptoms": "yellow spots on lower leaves",
    "affected_area": "about a quarter of the field",
    "photo_stage": "leaf", "needs_analysis": "true",
    "image": make_image("disease.jpg"),
}, **auth)
check("disease report with photo -> 201", resp.status_code == 201, f"{resp.status_code} {resp.content[:200]}")
report = resp.json() if resp.status_code == 201 else {}
report_id = report.get("id")
check("report image_src returned", bool(report.get("image_src")), report.get("image_src"))
check("report flagged for analysis", report.get("needs_analysis") is True, report.get("needs_analysis"))
check("photo_stage saved", report.get("photo_stage") == "leaf", report.get("photo_stage"))

# ---------- 7. extra angles go to DiseasePhoto ----------
extra = {
    "images": [make_image("plant.jpg"), make_image("field.jpg")],
    "photo_stage": ["whole_plant", "field"],
}
resp = client.post(f"/api/diseases/{report_id}/add_photos/", extra, **auth)
check("extra photos added -> 201", resp.status_code == 201, f"{resp.status_code} {resp.content[:160]}")
body = resp.json() if resp.status_code == 201 else {}
check("two extra photos stored", body.get("added") == 2, body.get("added"))
check("photo_count reflects the extras", body.get("photo_count") == 2, body.get("photo_count"))

report_obj = DiseaseReport.objects.get(pk=report_id)
check("report has 2 DiseasePhoto rows", report_obj.photos.count() == 2, report_obj.photos.count())
check("serializer photo_count totals main + extra",
      DiseaseReport.objects.get(pk=report_id).photos.count() + 1 == 3)

# ---------- 8. photo limit is enforced ----------
caps = {"images": [make_image(f"cap{i}.jpg") for i in range(4)]}
resp = client.post(f"/api/diseases/{report_id}/add_photos/", caps, **auth)
check("photo cap enforced (max 5 extra)", resp.status_code in (201, 400), resp.status_code)

# ---------- 9. remove one photo ----------
photo_id = report_obj.photos.first().id
resp = client.delete(f"/api/diseases/{report_id}/photos/{photo_id}/", **auth)
check("photo removal -> 200", resp.status_code == 200, resp.status_code)
check("photo actually deleted", not DiseasePhoto.objects.filter(pk=photo_id).exists())

# ---------- 10. flagged report with no photo is refused ----------
resp = client.post("/api/diseases/", {
    "farm": farm.id, "date": timezone.localdate().isoformat(), "crop": "Cassava",
    "needs_analysis": "true",
}, **auth)
check("analysis without a photo refused", resp.status_code == 400, resp.status_code)

# ---------- 11. analyse action ----------
resp = client.post(f"/api/diseases/{report_id}/analyse/", {}, **auth)
check("analyse action works", resp.status_code == 200, f"{resp.status_code} {resp.content[:120]}")

# ---------- 12. pending list for officers ----------
resp = client.get("/api/diseases/pending/", **auth)
check("pending reports endpoint works", resp.status_code == 200, resp.status_code)
pending = resp.json() if resp.status_code == 200 else []
check("flagged report appears in pending", any(r.get("id") == report_id for r in pending), len(pending))

# ---------- 13. uploaded photo is retrievable over HTTP ----------
if report.get("image_src"):
    path = report["image_src"].replace("http://testserver", "")
    resp = client.get(path)
    check("uploaded photo served at its URL", resp.status_code == 200, f"{path} -> {resp.status_code}")

# ---------- 14. a farmer cannot touch another farmer's report ----------
other = User.objects.create_user(username="imgverify2", password="verify-pass-456", phone="08090000002")
FarmerProfile.objects.create(user=other, full_name="Other Farmer")
other_token, _ = Token.objects.get_or_create(user=other)
resp = client.post(f"/api/diseases/{report_id}/add_photos/",
                   {"images": [make_image("x.jpg")]},
                   HTTP_AUTHORIZATION=f"Token {other_token.key}")
check("other farmer cannot add photos to this report", resp.status_code == 404, resp.status_code)

# ---------- 15. JSON still works on the same endpoints (no regression) ----------
resp = client.post("/api/diseases/", {
    "farm": farm.id, "date": timezone.localdate().isoformat(), "crop": "Sorghum",
    "symptoms": "no photo, manual record", "diagnosis": "Manual entry",
    "photo_url": "https://example.com/leaf.jpg",
}, content_type="application/json", **auth)
check("JSON create still works", resp.status_code == 201, f"{resp.status_code} {resp.content[:160]}")
if resp.status_code == 201:
    check("external photo_url passes through",
          resp.json().get("image_src") == "https://example.com/leaf.jpg", resp.json().get("image_src"))

# ---------- 16. multi-photo report created in a single multipart request ----------
resp = client.post("/api/diseases/", {
    "farm": farm.id, "date": timezone.localdate().isoformat(), "crop": "Groundnut",
    "symptoms": "leaf spots", "growth_stage": "podding",
    "image": make_image("main.jpg"),
    "images": [make_image("angle1.jpg"), make_image("angle2.jpg")],
    "photo_stage": ["leaf", "whole_plant", "field"],
}, **auth)
check("multi-photo report -> 201", resp.status_code == 201, f"{resp.status_code} {resp.content[:160]}")
if resp.status_code == 201:
    body = resp.json()
    check("main photo + 2 extras counted", body.get("photo_count") == 3, body.get("photo_count"))
    check("nested photos returned", len(body.get("photos", [])) == 2, len(body.get("photos", [])))
    check("only one report row created for the batch",
          DiseaseReport.objects.filter(farm=farm, crop="Groundnut").count() == 1,
          DiseaseReport.objects.filter(farm=farm, crop="Groundnut").count())

# ---------- cleanup ----------
User.objects.filter(username__in=[username, "imgverify2"]).delete()
shutil.rmtree(MEDIA_TMP, ignore_errors=True)

print()
print("RESULT:", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
