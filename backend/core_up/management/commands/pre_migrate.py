"""
Management command to resolve InconsistentMigrationHistory on databases
that had Django default auth/admin migrations applied before FarmKonnect's
custom User model and initial backend migrations.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Checks for and fixes InconsistentMigrationHistory before running migrate."

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                table_names = connection.introspection.table_names(cursor)
                if "django_migrations" not in table_names:
                    self.stdout.write(self.style.SUCCESS("[pre_migrate] Clean database. Ready for migrations."))
                    return

                cursor.execute(
                    """
                    SELECT app, name, applied
                    FROM django_migrations
                    WHERE app IN ('admin', 'core_up', 'backend')
                    ORDER BY applied ASC
                    """
                )
                rows = cursor.fetchall()

                admin_applied = None
                core_applied = None

                for app, name, applied in rows:
                    if app == "admin" and name == "0001_initial":
                        admin_applied = applied
                    if (app == "core_up" or app == "backend") and name == "0001_initial":
                        core_applied = applied

                is_inconsistent = False
                if admin_applied and not core_applied:
                    is_inconsistent = True
                elif admin_applied and core_applied and admin_applied < core_applied:
                    is_inconsistent = True

                if is_inconsistent:
                    self.stdout.write(
                        self.style.WARNING(
                            "[pre_migrate] Detected InconsistentMigrationHistory: "
                            "'admin.0001_initial' was applied before 'core_up.0001_initial'."
                        )
                    )

                    vendor = connection.vendor
                    if vendor == "postgresql":
                        self.stdout.write(
                            self.style.NOTICE(
                                "[pre_migrate] Resetting PostgreSQL public schema to enable clean initial migration..."
                            )
                        )
                        cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
                        self.stdout.write(
                            self.style.SUCCESS(
                                "[pre_migrate] PostgreSQL public schema reset successfully."
                            )
                        )
                    elif vendor == "sqlite":
                        self.stdout.write(
                            self.style.NOTICE(
                                "[pre_migrate] Clearing migrations table on SQLite..."
                            )
                        )
                        cursor.execute("DROP TABLE django_migrations;")
                        self.stdout.write(
                            self.style.SUCCESS(
                                "[pre_migrate] SQLite migrations table cleared."
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "[pre_migrate] Database migration history is consistent."
                        )
                    )
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"[pre_migrate] Notice: {exc}"))
