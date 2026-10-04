import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "farmkonnect.settings")
django.setup()

from core_up.models import User

USERNAME = "admin_monitor"
EMAIL = "admin@farmkonnect.local"
PHONE = "+254700000000"
PASSWORD = "YourSecurePassword123!"


def create_superuser():
    user, created = User.objects.get_or_create(
        username=USERNAME,
        defaults={
            "email": EMAIL,
            "phone": PHONE,
            "first_name": "Admin",
            "last_name": "Monitor",
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
        user.set_password(PASSWORD)
        user.save()
        print(f"⚠️ Superuser '{user.username}' already existed and was updated with full privileges.")

    print(f"Login: {user.username}")
    print(f"Email: {user.email}")
    print(f"Phone: {user.phone}")
    print(f"Password: {PASSWORD}")
    print("Django admin URL: /admin")


if __name__ == "__main__":
    create_superuser()
