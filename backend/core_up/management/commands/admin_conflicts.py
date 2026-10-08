"""Report which account holds a username, email or phone that would clash with
the SUPERUSER_* values, so a failed create_admin run can be understood quickly.

Usage (from backend/ or the repo root):
    python manage.py admin_conflicts

Prints one row per conflicting user. Nothing is modified.
"""

from django.core.management.base import BaseCommand

from core_up.models import User


class Command(BaseCommand):
    help = "Show accounts that clash with the configured SUPERUSER_* credentials."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=None, help="Defaults to $SUPERUSER_USERNAME")
        parser.add_argument("--email", default=None, help="Defaults to $SUPERUSER_EMAIL")
        parser.add_argument("--phone", default=None, help="Defaults to $SUPERUSER_PHONE")

    def handle(self, *args, **options):
        import os

        username = options["username"] or os.environ.get("SUPERUSER_USERNAME")
        email = options["email"] or os.environ.get("SUPERUSER_EMAIL")
        phone = options["phone"] or os.environ.get("SUPERUSER_PHONE")

        self.stdout.write(f"Checking username={username!r} email={email!r} phone={phone!r}")
        self.stdout.write(f"Total users in database: {User.objects.count()}")

        found = False
        if phone:
            # phone is unique, so at most one holder - this is what blocks creation.
            holder = User.objects.filter(phone=phone).first()
            if holder:
                found = True
                self.stdout.write(self.style.WARNING(
                    f"PHONE {phone} is held by user id={holder.id} username={holder.username!r} "
                    f"email={holder.email!r} staff={holder.is_staff} superuser={holder.is_superuser} "
                    f"active={holder.is_active}"
                ))
                self.stdout.write(
                    "  -> create_admin cannot reuse this number unless it is freed. "
                    "Re-run it with SUPERUSER_RECLAIM_PHONE=1 to move the number to the admin."
                )
            else:
                self.stdout.write(self.style.SUCCESS(f"PHONE {phone} is free."))

        if username:
            clash = User.objects.filter(username=username).first()
            if clash:
                found = True
                self.stdout.write(self.style.WARNING(
                    f"USERNAME {username!r} already exists (id={clash.id}). "
                    "create_admin will update that account and set its password."
                ))
            else:
                self.stdout.write(self.style.SUCCESS(f"USERNAME {username!r} is free (will be created)."))

        if email:
            clash = User.objects.filter(email=email).exclude(username=username).first()
            if clash:
                found = True
                self.stdout.write(self.style.WARNING(
                    f"EMAIL {email!r} is also used by username={clash.username!r} (id={clash.id}). "
                    "Email is not unique so this is allowed, but OTP login may be ambiguous."
                ))
            else:
                self.stdout.write(self.style.SUCCESS(f"EMAIL {email!r} is free."))

        self.stdout.write("")
        if found:
            self.stdout.write(self.style.WARNING("Conflicts found - see above."))
        else:
            self.stdout.write(self.style.SUCCESS("No conflicts. create_admin should succeed."))
