"""Database connection helpers (PostgreSQL via psycopg).

The connection URL is NOT written in the code. It is read from the
DATABASE_URL setting in the .env file (copy .env.example to .env and edit it).
"""

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

# Read the .env file that sits next to this script, so DATABASE_URL is available
# even if the program is started from another folder.
load_dotenv(Path(__file__).resolve().with_name(".env"))


def get_database_url() -> str:
    """Return the DATABASE_URL setting, or stop with a helpful message if it is missing."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and configure "
            "the credentials for the existing PostgreSQL database."
        )
    return url


def connect() -> psycopg.Connection:
    """Open a new database connection. Rows come back as dicts: {"column": value}."""
    return psycopg.connect(get_database_url(), row_factory=dict_row)


def get_connection() -> Iterator[psycopg.Connection]:
    """FastAPI dependency: gives each request its own connection.

    The `with` block commits when the request succeeds, rolls back if it fails,
    and always closes the connection afterwards.
    """
    with connect() as connection:
        yield connection
