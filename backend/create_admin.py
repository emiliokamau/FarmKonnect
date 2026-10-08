"""Create or update the FarmKonnect superuser during deployment.

Designed to be safe inside a Render build:
  * If the SUPERUSER_* credentials are not configured, it prints a notice and
    exits 0 instead of aborting the build. Admin creation is a convenience, not
    a build requirement.
  * Output is plain ASCII, because build consoles are frequently cp1252 and any
    non-ASCII character raises UnicodeEncodeError and fails the build.
  * If SUPERUSER_PHONE is already held by another account, the whole creation
    used to abort with an IntegrityError and no admin was created at all. The
    phone is now freed from that account (set to NULL - the holder keeps their
    account) and the admin is retried with the requested number.

Environment:
  SUPERUSER_RECLAIM_PHONE=0   never take the number; create the admin without a
                              phone instead (the holder is left untouched).

The password is never printed.
"""

import os
import sys

import django
from django.db import IntegrityError, transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "farmkonnect.settings")
django.setup()

from core_up.models import User  # noqa: E402

REQUIRED_VARS = ("SUPERUSER_USERNAME", "SUPERUSER_EMAIL", "SUPERUSER_PHONE", "SUPERUSER_PASSWORD")


def missing_vars():
    return [name for name in REQUIRED_VARS if not os.environ.get(name)]


def free_phone_for(username):
    """Return the phone to use for this admin, freeing it from any other holder.

    ``User.phone`` is unique, so an account that already owns the number blocks
    superuser creation entirely. The holder keeps their account; only the phone
    is detached (the column is nullable).

    Returns (phone, note). With SUPERUSER_RECLAIM_PHONE=0 the number is left
    alone and the admin is created without one.
    """
    phone = os.environ["SUPERUSER_PHONE"]
    holder = User.objects.filter(phone=phone).exclude(username=username).first()
    if holder is None:
        return phone, None

    if os.environ.get("SUPERUSER_RECLAIM_PHONE", "1") == "0":
        return None, (
            f"phone {phone} is held by '{holder.username}' and SUPERUSER_RECLAIM_PHONE=0, "
            f"so the admin will be created without a phone number."
        )

    holder.phone = None
    holder.save(update_fields=["phone"])
    return phone, (
        f"phone {phone} was held by '{holder.username}' (id={holder.id}); "
        f"detached from that account and assigned to the admin."
    )


def create_superuser():
    username = os.environ["SUPERUSER_USERNAME"]
    email = os.environ["SUPERUSER_EMAIL"]
    password = os.environ["SUPERUSER_PASSWORD"]
    first_name = os.environ.get("SUPERUSER_FIRST_NAME", "FarmKonnect")
    last_name = os.environ.get("SUPERUSER_LAST_NAME", "Admin")

    phone, note = free_phone_for(username)
    if note:
        print(f"[create_admin] {note}")

    defaults = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "is_staff": True,
        "is_superuser": True,
        "is_phone_verified": True,
        "profile_completed": True,
    }
    if phone:
        defaults["phone"] = phone

    try:
        with transaction.atomic():
            user, created = User.objects.get_or_create(username=username, defaults=defaults)
            if not created:
                user.is_staff = True
                user.is_superuser = True
                user.is_phone_verified = True
                user.profile_completed = True
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                if phone:
                    user.phone = phone
            # Applied for both the created and updated paths.
            user.set_password(password)
            user.save()
    except IntegrityError as exc:
        # Never fail the build, and never leave a half-written account behind.
        print(
            f"[create_admin] Could not create the superuser: {exc} "
            "If this is a uniqueness clash, run 'python manage.py admin_conflicts' to see the holder."
        )
        return None

    if created:
        print(f"[create_admin] Superuser '{user.username}' created successfully.")
    else:
        print(f"[create_admin] Superuser '{user.username}' already existed and was updated.")

    print("=" * 50)
    print("SUPERUSER READY")
    print("=" * 50)
    print(f"Username: {user.username}")
    print(f"Email:    {user.email}")
    print(f"Phone:    {user.phone}")
    print("Password: loaded from SUPERUSER_PASSWORD")
    print("Access:   is_staff, is_superuser, is_phone_verified, profile_completed = True")
    print("Admin URL: /admin/")
    print("=" * 50)
    return user


if __name__ == "__main__":
    absent = missing_vars()
    if absent:
        print(
            "[create_admin] Skipping superuser setup: missing "
            + ", ".join(absent)
            + ". Set these environment variables to create the admin account; "
            "the build continues without it."
        )
        sys.exit(0)

    try:
        create_superuser()
    except Exception as exc:  # never fail a deployment over admin provisioning
        print(f"[create_admin] Notice: could not create the superuser ({exc}). Continuing.")
        sys.exit(0)
