import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        port=os.environ.get("DB_PORT"),
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD")
    )

def country_table_exists(country_code: str) -> bool:
    """Check if a table exists for the given country code in the schema."""
    schema = os.environ.get("DB_SCHEMA")
    table_name = country_code.lower()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    AND table_name = %s
                )
            """, (schema, table_name))
            return cur.fetchone()[0]
    finally:
        conn.close()

def get_extended_codes(country_code: str, six_digit_codes: list[str]) -> dict[str, list[dict]]:
    """
    For each 6-digit code, fetch ALL rows from the country table
    where the first 6 digits of hs_code match.
    Returns a dict grouped by 6-digit code:
    {
        "830110": [
            {"hs_code": "83011010", "description": "..."},
            {"hs_code": "83011090", "description": "..."},
        ],
    }
    """
    schema = os.environ.get("DB_SCHEMA")
    table_name = country_code.lower()

    conn = get_connection()
    grouped = {}

    try:
        with conn.cursor() as cur:
            for code in six_digit_codes:
                # Normalize: strip dots to get raw 6-digit prefix
                clean_code = code.replace(".", "").replace(" ", "")[:6]

                cur.execute(f"""
                    SELECT hs_code, description
                    FROM {schema}."{table_name}"
                    WHERE LEFT(CAST(hs_code AS TEXT), 6) = %s
                    ORDER BY hs_code
                """, (clean_code,))

                rows = cur.fetchall()

                if rows:
                    grouped[clean_code] = [
                        {"hs_code": row[0], "description": row[1]}
                        for row in rows
                    ]
    finally:
        conn.close()

    return grouped