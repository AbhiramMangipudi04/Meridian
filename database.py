#!/usr/bin/env python3
"""
Root entry point for the Nexus Data module.

    python database.py            # create the schema (meridian.db) if it doesn't exist
    python database.py --seed     # create the schema AND run the deterministic seed process
    python database.py --drop     # drop all tables first, then recreate the schema
    python database.py --drop --seed

Schema creation, seeding, and connection management are deliberately kept
in separate modules (data/database/connection.py and data/seed/seed.py);
this script is only a thin CLI wrapper over them.
"""
from __future__ import annotations

import argparse
import sys

from data.database.connection import DEFAULT_DB_PATH, init_schema
from data.seed.seed import run_seed


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize and/or seed meridian.db")
    parser.add_argument(
        "--seed", action="store_true", help="Run the deterministic seed process after schema creation."
    )
    parser.add_argument(
        "--drop", action="store_true", help="Drop all tables before recreating the schema."
    )
    parser.add_argument(
        "--db-path", default=None, help=f"Override the SQLite file path (default: {DEFAULT_DB_PATH})."
    )
    args = parser.parse_args()

    print(f"Initializing schema at: {args.db_path or DEFAULT_DB_PATH}")
    init_schema(db_path=args.db_path, drop_first=args.drop)
    print("Schema ready.")

    if args.seed:
        print("Running deterministic seed process...")
        run_seed(db_path=args.db_path)
        print("Seeding complete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
