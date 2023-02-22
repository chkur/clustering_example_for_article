from datetime import datetime

from django.core.management import BaseCommand
from django.db import connection


class Command(BaseCommand):
    def parse_date(self, dt):
        if dt:
            return datetime.strptime(dt, "%m/%d/%Y")

    def print_ddl(self, table_name, constraint_type):
        query = """
            SELECT
                'ALTER TABLE ' || tc.table_name || '\n    DROP CONSTRAINT ' || tc.constraint_name || ';',
                'ALTER TABLE ' || tc.table_name || '\n    ADD CONSTRAINT ' || tc.constraint_name || '\n    FOREIGN KEY (' || kcu.column_name || ') REFERENCES ' || ccu.table_name || '(' || ccu.column_name || ');'
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = %(constraint_type)s AND ccu.table_name = %(table_name)s;
        """
        with connection.cursor() as cursor:
            cursor.execute(
                query, {"table_name": table_name, "constraint_type": constraint_type}
            )
            drop_constraint_sqls = []
            add_constraint_sqls = []
            for row in cursor.fetchall():
                drop_constraint_sqls.append(row[0])
                add_constraint_sqls.append(row[1])
            print(
                f"=============================\nDROP CONSTRAINTS {table_name}\n============================="
            )
            for row in drop_constraint_sqls:
                print(row)
            print(
                f"==============================\nADD CONSTRAINTS {table_name}\n=============================="
            )
            for row in add_constraint_sqls:
                print(row)

    def handle(self, *args, **options):
        self.print_ddl("main_vehicle", "FOREIGN KEY")
        self.print_ddl("main_criminalvehicle", "FOREIGN KEY")
        self.print_ddl("main_comment", "FOREIGN KEY")
        self.print_ddl("main_comment", "PRIMARY KEY")
