# wevote_functions/create_trigram_index.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import hashlib
import logging
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings") 

django.setup()

from django.db import connection, transaction
from django.db.models import CharField, TextField
from django.conf import settings
from django.apps import apps
from psycopg2 import sql

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

POSTGRES_INDEX_NAME_LIMIT = 63


def create_trigram_index(model, fields, logger_func=print):
    """
    model: Django model class
    fields: list[str]
    Returns: dict with 'success', 'status', 'indexes_created', and 'status_level' keys
    """
    status_messages = None
    indexes_created = []
    indexes_already_existed = []

    if connection.vendor != "postgresql":
        error_msg = "Trigram index attempted on non-PostgreSQL database."
        logger.error(error_msg)
        return {
            'success': False,
            'status': error_msg,
            'indexes_created': [],
            'indexes_already_existed': [],
            'status_level': 'error'
        }

    table_name = model._meta.db_table
    logger_func(f"Starting trigram index creation | table={table_name} | fields={fields}")

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                _ensure_extensions(cursor, logger_func=logger_func)
                for field_name in fields:
                    field = _get_valid_field(model, field_name)
                    index_name = _generate_safe_index_name(table_name, field.column)

                    if _index_exists(cursor, table_name, index_name):
                        msg = f"Index already exists, skipping | index={index_name}"
                        logger_func(msg)
                        status_messages= msg
                        indexes_already_existed.append(index_name)
                        continue
                    
                    create_index_sql = sql.SQL(
                        "CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} USING gist ({column_name} gist_trgm_ops);"
                    ).format(
                        index_name=sql.Identifier(index_name),
                        table_name=sql.Identifier(table_name),
                        column_name=sql.Identifier(field.column)
                    )
                    msg = f"Creating trigram index | index={index_name} | table={table_name} | column={field.column}"
                    logger_func(msg)

                    
                    cursor.execute(create_index_sql)
                    indexes_created.append(index_name)


        if indexes_created:
            success_msg = f"Trigram index creation completed successfully | index ={index_name}."
            logger_func(success_msg)
            status_messages= success_msg

        return {
            'success': True,
            'status': status_messages,
            'indexes_created': indexes_created,
            'indexes_already_existed': indexes_already_existed,
            'status_level': 'success' if indexes_created else 'info'

        }

    except Exception as e:
        error_msg = f"Failed to create trigram index: {str(e)}"
        logger.exception("Failed to create trigram index | table=%s | fields=%s", table_name, fields)
        status_messages.append(error_msg)
        return {
            'success': False,
            'status': ' | '.join(status_messages),
            'indexes_created': indexes_created
        }


# ---------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------

def _ensure_extensions(cursor, logger_func=print):
    logger_func("Ensuring PostgreSQL extensions exist (pg_trgm, btree_gist)")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")


def _get_valid_field(model, field_name):
    try:
        field = model._meta.get_field(field_name)
    except Exception:
        logger.error("Field not found | field=%s", field_name)
        raise ValueError(f"Field '{field_name}' not found")

    if not isinstance(field, (CharField, TextField)):
        logger.error("Invalid field type for trigram | field=%s | type=%s", field_name, field.__class__.__name__)
        raise ValueError(f"Field '{field_name}' must be CharField or TextField")

    return field


def _index_exists(cursor,table_name, index_name):
    cursor.execute(
        """
        SELECT 1
        FROM pg_indexes
        WHERE tablename = %s
        AND indexname = %s;
        """,
        [table_name, index_name],
    )
    exists = cursor.fetchone() is not None

    if exists:
        logger.debug("Index existence check: FOUND | index=%s", index_name)
    else:
        logger.debug("Index existence check: NOT FOUND | index=%s", index_name)

    return exists


def _generate_safe_index_name(table_name, column_name):
    table_name =  table_name.split("_", 1)[1] if "_" in table_name else table_name
    base_name = f"{table_name}_{column_name}_trgm_idx"

    if len(base_name) <= POSTGRES_INDEX_NAME_LIMIT:
        return base_name

    hash_suffix = hashlib.md5(base_name.encode()).hexdigest()[:8]
    trimmed = base_name[: POSTGRES_INDEX_NAME_LIMIT - 9]
    safe_name = f"{trimmed}_{hash_suffix}"

    logger.debug("Index name truncated due to 63-char limit | original=%s | new=%s", base_name, safe_name)

    return safe_name



def check_trigram_index_exists(model, field_name):
    table_name = model._meta.db_table
    index_name = _generate_safe_index_name(table_name, field_name)
    with connection.cursor() as cursor:
        return _index_exists(cursor, table_name, index_name)


# ---------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_trigram_index.py <app_label.ModelName> <field1> [<field2> ...]")
        sys.exit(1)

    model_name = sys.argv[1]
    field_names = sys.argv[2:]

    try:
        app_label, class_name = model_name.split(".")
        model = apps.get_model(app_label, class_name)
    except Exception as e:
        print(f"Failed to load model '{model_name}': {e}")
        sys.exit(1)

    create_trigram_index(model, field_names)