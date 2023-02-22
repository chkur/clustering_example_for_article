from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "New partition generation on cron."

    def handle(self, *args, **options):
        # Get the last partition key value.
        SQL_LAST_VALUE = "SELECT MAX ({column}) from {table_name}"
        # SQL for partition creation
        SQL_CHECK_PARTITION = """
            CREATE TABLE IF NOT EXISTS {table_name}_{min_value}_{max_value}
                PARTITION OF {table_name} FOR VALUES FROM ({min_value}) TO ({max_value});
        """

        # Walk through the our local apps
        for app_name in settings.LOCAL_APPS:
            # Get  all models for app
            app_models = apps.get_app_config(app_name).get_models()
            # Walk through the local app models
            for model in app_models:
                # Check "custom_partitioned" attr. For inherited models you should set in explicitly
                custom_partitioned = getattr(model, "custom_partitioned", None)
                if not custom_partitioned:
                    continue
                # Get table name in the database
                table_name = model._meta.db_table
                with connection.cursor() as cursor:
                    # Get current maximum for partition key
                    cursor.execute(
                        SQL_LAST_VALUE.format(
                            table_name=table_name,
                            column=custom_partitioned["column"],
                        )
                    )
                    last_value = cursor.fetchone()[0] or 0

                    # Get partition key range for parttitions that should exist
                    partition_size = custom_partitioned["size"]
                    last_partition_limit = (
                        last_value // partition_size * partition_size
                        + partition_size * settings.PARTITIONS_EXTRA_COUNT
                    )
                    partition_ranges = [
                        [i, i + partition_size]
                        for i in range(
                            partition_size, last_partition_limit, partition_size
                        )
                    ]

                    # Run SQL that will create partitions if they are not exist
                    partition_ranges.insert(0, [1, partition_size])
                    for partition in partition_ranges:
                        cursor.execute(
                            SQL_CHECK_PARTITION.format(
                                table_name=table_name,
                                min_value=partition[0],
                                max_value=partition[1],
                            ),
                            {},
                        )
