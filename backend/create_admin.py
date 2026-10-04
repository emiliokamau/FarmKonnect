import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "farmkonnect.settings")
django.setup()

from core_up.models import User

USERNAME = "emilio"
EMAIL = "emilio@farmkonnect.local"
PHONE = "0796526647"
PASSWORD = "EmilioAdmin@2026"


def create_superuser():
    user, created = User.objects.get_or_create(
        username=USERNAME,
        defaults={
            "email": EMAIL,
            "phone": PHONE,
            "first_name": "Emilio",
            "last_name": "Admin",
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
        user.first_name = "Emilio"
        user.last_name = "Admin"
        user.set_password(PASSWORD)
        user.save()
        print(f"⚠️ Superuser '{user.username}' already existed and was updated with full privileges.")

    print("\n" + "=" * 50)
    print("SUPERUSER CREDENTIALS")
    print("=" * 50)
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"Phone: {user.phone}")
    print(f"Password: {PASSWORD}")
    print("Gender: Male")
    print("\nAccess Levels:")
    print("✅ is_staff: True")
    print("✅ is_superuser: True")
    print("✅ is_phone_verified: True")
    print("✅ profile_completed: True")
    print("\nDjango Admin URL: /admin")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    create_superuser()
