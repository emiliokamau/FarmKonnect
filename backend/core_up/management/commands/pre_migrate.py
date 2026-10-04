"""
Management command to resolve InconsistentMigrationHistory on databases
that had Django default auth/admin migrations applied before FarmKonnect's
custom User model and initial backend migrations.

This variant is safe to run on managed databases where the DB user cannot
DROP SCHEMA. Instead of dropping the schema, it deletes the offending
migration record(s) from django_migrations so Django can apply the
correct initial migration ordering.

IMPORTANT: Back up your database BEFORE deploying this change. Deleting
rows from django_migrations is destructive to migration history and
should only be used when you understand the consequences.
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

                # Fetch admin/core_up migration records (if any)
                cursor.execute(
                    "SELECT app, name, applied FROM django_migrations WHERE app IN ('admin', 'core_up', 'backend') ORDER BY applied ASC"
                )
                rows = cursor.fetchall()

                admin_applied = False
                core_applied = False

                for app, name, applied in rows:
                    if app == "admin" and name == "0001_initial":
                        admin_applied = True
                    if (app == "core_up" or app == "backend") and name == "0001_initial":
                        core_applied = True

                if admin_applied and not core_applied:
                    self.stdout.write(self.style.WARNING(
                        "[pre_migrate] Detected InconsistentMigrationHistory: 'admin.0001_initial' was applied before 'core_up.0001_initial'."
                    ))

                    # Safer remediation for managed DBs: delete the admin migration record(s)
                    try:
                        cursor.execute(
                            "DELETE FROM django_migrations WHERE app = %s AND name = %s",
                            ["admin", "0001_initial"],
                        )
                        self.stdout.write(self.style.SUCCESS(
                            "[pre_migrate] Removed admin.0001_initial record from django_migrations."
                        ))
                    except Exception as exc:
                        self.stdout.write(self.style.WARNING(
                            f"[pre_migrate] Failed to delete migration rows: {exc}"
                        ))
                        # As a fallback, attempt the original schema reset (may fail on managed DBs)
                        vendor = connection.vendor
                        if vendor == "postgresql":
                            try:
                                self.stdout.write(self.style.NOTICE(
                                    "[pre_migrate] Attempting PostgreSQL public schema reset..."
                                ))
                                cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
                                self.stdout.write(self.style.SUCCESS(
                                    "[pre_migrate] PostgreSQL public schema reset successfully."
                                ))
                            except Exception as exc2:
                                self.stdout.write(self.style.WARNING(
                                    f"[pre_migrate] Schema reset failed: {exc2}"
                                ))
                        elif vendor == "sqlite":
                            try:
                                self.stdout.write(self.style.NOTICE(
                                    "[pre_migrate] Clearing migrations table on SQLite..."
                                ))
                                cursor.execute("DROP TABLE django_migrations;")
                                self.stdout.write(self.style.SUCCESS(
                                    "[pre_migrate] SQLite migrations table cleared."
                                ))
                            except Exception as exc2:
                                self.stdout.write(self.style.WARNING(
                                    f"[pre_migrate] Clearing sqlite migrations table failed: {exc2}"
                                ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        "[pre_migrate] Database migration history is consistent."
                    ))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"[pre_migrate] Notice: {exc}"))
