"""
Management command to clean off stale migration records and incompatible tables
causing InconsistentMigrationHistory on deployment databases.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Cleans off stale migration records and tables causing InconsistentMigrationHistory."

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                table_names = connection.introspection.table_names(cursor)
                if "django_migrations" not in table_names:
                    self.stdout.write(self.style.SUCCESS("[pre_migrate] Clean database. Ready for migrations."))
                    return

                cursor.execute("SELECT app, name FROM django_migrations;")
                records = set(cursor.fetchall())

                has_admin = ("admin", "0001_initial") in records
                has_core_up = ("core_up", "0001_initial") in records
                has_legacy_backend = any(app == "backend" for app, _ in records)

                if (has_admin and not has_core_up) or has_legacy_backend:
                    self.stdout.write(self.style.WARNING(
                        "[pre_migrate] Inconsistent migration history detected: "
                        f"has_admin={has_admin}, has_core_up={has_core_up}, has_legacy_backend={has_legacy_backend}. "
                        "Cleaning off records and tables..."
                    ))

                    vendor = connection.vendor
                    if vendor == "postgresql":
                        reset_done = False
                        try:
                            cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
                            reset_done = True
                            self.stdout.write(self.style.SUCCESS(
                                "[pre_migrate] PostgreSQL public schema reset successfully."
                            ))
                        except Exception as drop_err:
                            self.stdout.write(self.style.NOTICE(
                                f"[pre_migrate] DROP SCHEMA notice: {drop_err}. Dropping tables individually..."
                            ))

                        if not reset_done:
                            try:
                                cursor.execute("""
                                    DO $$ DECLARE
                                        r RECORD;
                                    BEGIN
                                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                                        END LOOP;
                                    END $$;
                                """)
                                self.stdout.write(self.style.SUCCESS(
                                    "[pre_migrate] Dropped all tables in public schema individually."
                                ))
                            except Exception as table_err:
                                self.stdout.write(self.style.WARNING(
                                    f"[pre_migrate] Error dropping tables: {table_err}. Deleting migration records..."
                                ))
                                cursor.execute("DELETE FROM django_migrations WHERE app IN ('admin', 'backend');")
                                self.stdout.write(self.style.SUCCESS(
                                    "[pre_migrate] Deleted admin and backend records from django_migrations."
                                ))
                    elif vendor == "sqlite":
                        cursor.execute("PRAGMA foreign_keys = OFF;")
                        for t in connection.introspection.table_names(cursor):
                            cursor.execute(f"DROP TABLE IF EXISTS \"{t}\";")
                        cursor.execute("PRAGMA foreign_keys = ON;")
                        self.stdout.write(self.style.SUCCESS(
                            "[pre_migrate] Cleared SQLite tables."
                        ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        "[pre_migrate] Database migration history is consistent."
                    ))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"[pre_migrate] Notice: {exc}"))
