"""
Move the shared accounts onto fixed roles, then let the database enforce them.

WHY THIS EXISTS
---------------
Until now an account's role was whatever its owner typed at signup ("Doctor",
"Hospital", anything at all), and its hospital was whatever name they typed.
Neither can be trusted. This rewrites every such account as an active
case_manager with no hospital - the reading api/auth.py:effective already gives
them - and then installs a $jsonSchema validator on shared_identity.users, so a
role outside the fixed list or a missing status is refused by the database
itself, whatever code tries to write it.

Run once against each cluster, after deploying the code that knows the new
fields. Needs a database user allowed to run collMod (dbAdmin or higher), which
is more than the API's own user normally has.

    .venv/bin/python scripts/migrate_user_roles.py --dry-run
    .venv/bin/python scripts/migrate_user_roles.py

Idempotent: re-running it changes nothing.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pymongo.errors import OperationFailure

from api import auth
from api.db_utils import get_db_name, get_mongo_client


def apply_validator(db) -> None:
    identity = db.client[auth.IDENTITY_DB]
    if auth.USERS_COLLECTION in identity.list_collection_names():
        identity.command("collMod", auth.USERS_COLLECTION,
                         validator=auth.USERS_VALIDATOR,
                         validationLevel="strict", validationAction="error")
    else:
        identity.create_collection(auth.USERS_COLLECTION, validator=auth.USERS_VALIDATOR)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing anything")
    args = parser.parse_args()

    load_dotenv()
    db = get_mongo_client(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))[get_db_name()]
    users = auth.users(db)

    legacy = users.count_documents({"$or": [{"status": {"$nin": list(auth.STATUSES)}},
                                            {"role": {"$nin": list(auth.ROLES)}}]})
    print(f"  {users.count_documents({})} accounts, {legacy} on free-text roles")

    if args.dry_run:
        print("  Dry run: nothing written.")
        return

    changed = auth.backfill_users(db)
    print(f"  Backfilled {changed} account(s) to case_manager / active / no hospital")

    auth.ensure_indexes(db)
    try:
        apply_validator(db)
    except OperationFailure as exc:
        # The usual cause: the API's own database user can read and write but
        # not change a collection's rules. The backfill above has already been
        # saved, and re-running is safe, so only the validator is left to do.
        sys.exit(f"  Could not install the validator ({exc.code_name or exc}).\n"
                 f"  The accounts are already backfilled. Re-run this script with a\n"
                 f"  database user that has the Atlas admin role, or dbAdmin on\n"
                 f"  {auth.IDENTITY_DB}.")
    print(f"  Validator installed on {auth.IDENTITY_DB}.{auth.USERS_COLLECTION}: "
          f"role in {list(auth.ROLES)}, status in {list(auth.STATUSES)}")


if __name__ == "__main__":
    main()
