"""Create or update the FarmKonnect superuser during deployment.

Designed to be safe inside a Render build:
  * If the SUPERUSER_* credentials are not configured, it prints a notice and
    exits 0 instead of aborting the build. Admin creation is a convenience, not
    a build requirement.
  * Output is plain ASCII, because build consoles are frequently cp1252 and any
    non-ASCII character raises UnicodeEncodeError and fails the build.

The password is never printed.
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "farmkonnect.settings")
django.setup()

from core_up.models import User  # noqa: E402

REQUIRED_VARS = ("SUPERUSER_USERNAME", "SUPERUSER_EMAIL", "SUPERUSER_PHONE", "SUPERUSER_PASSWORD")


def missing_vars():
    return [name for name in REQUIRED_VARS if not os.environ.get(name)]


def create_superuser():
    username = os.environ["SUPERUSER_USERNAME"]
    email = os.environ["SUPERUSER_EMAIL"]
    phone = os.environ["SUPERUSER_PHONE"]
    password = os.environ["SUPERUSER_PASSWORD"]
    first_name = os.environ.get("SUPERUSER_FIRST_NAME", "FarmKonnect")
    last_name = os.environ.get("SUPERUSER_LAST_NAME", "Admin")

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": True,
            "is_superuser": True,
            "is_phone_verified": True,
            "profile_completed": True,
        },
    )

    if created:
        user.set_password(password)
        user.save()
        print(f"[create_admin] Superuser '{user.username}' created successfully.")
    else:
        user.is_staff = True
        user.is_superuser = True
        user.is_phone_verified = True
        user.profile_completed = True
        user.email = email
        user.phone = phone
        user.first_name = first_name
        user.last_name = last_name
        user.set_password(password)
        user.save()
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
