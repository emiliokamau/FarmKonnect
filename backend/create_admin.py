import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "farmkonnect.settings")
django.setup()

from core_up.models import User


def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required.")
    return value


USERNAME = required_env("SUPERUSER_USERNAME")
EMAIL = required_env("SUPERUSER_EMAIL")
PHONE = required_env("SUPERUSER_PHONE")
PASSWORD = required_env("SUPERUSER_PASSWORD")
FIRST_NAME = os.environ.get("SUPERUSER_FIRST_NAME", "FarmKonnect")
LAST_NAME = os.environ.get("SUPERUSER_LAST_NAME", "Admin")


def create_superuser():
    user, created = User.objects.get_or_create(
        username=USERNAME,
        defaults={
            "email": EMAIL,
            "phone": PHONE,
            "first_name": FIRST_NAME,
            "last_name": LAST_NAME,
            "is_staff": True,
            "is_superuser": True,
            "is_phone_verified": True,
            "profile_completed": True,
        },
    )

    if created:
        user.set_password(PASSWORD)
        user.save()
        print(f"✅ Superuser '{user.username}' created successfully.")
    else:
        user.is_staff = True
        user.is_superuser = True
        user.is_phone_verified = True
        user.profile_completed = True
        user.email = EMAIL
        user.phone = PHONE
        user.first_name = FIRST_NAME
        user.last_name = LAST_NAME
        user.set_password(PASSWORD)
        user.save()
        print(f"⚠️ Superuser '{user.username}' already existed and was updated with full privileges.")

    print("\n" + "=" * 50)
    print("SUPERUSER CREATED")
    print("=" * 50)
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"Phone: {user.phone}")
    print("Password: loaded from SUPERUSER_PASSWORD")
    print("\nAccess Levels:")
    print("✅ is_staff: True")
    print("✅ is_superuser: True")
    print("✅ is_phone_verified: True")
    print("✅ profile_completed: True")
    print("\nDjango Admin URL: /admin")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    create_superuser()
