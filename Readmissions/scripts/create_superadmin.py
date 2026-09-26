"""
Create our team's superadmin account, or promote an existing account to one.

WHY THIS EXISTS
---------------
No endpoint can grant the superadmin role - otherwise a hospital admin, or
anyone who found the endpoint, could make one. So the first superadmin, and any
after it, comes from here, run by someone with direct access to the cluster.

    .venv/bin/python scripts/create_superadmin.py you@ourteam.com

Prompts for a password when creating a new account. When the email already
exists, the account is promoted and keeps its password unless --reset-password
is given.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from fastapi import HTTPException

from api import auth
from api.db_utils import get_db_name, get_mongo_client


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("email")
    parser.add_argument("--reset-password", action="store_true",
                        help="set a new password even if the account already exists")
    args = parser.parse_args()

    load_dotenv()
    db = get_mongo_client(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))[get_db_name()]

    exists = auth.users(db).find_one({"email": auth.normalise_email(args.email)}) is not None
    password = None
    if not exists or args.reset_password:
        password = getpass.getpass("Password (min 8 characters): ")
        if password != getpass.getpass("Repeat password: "):
            sys.exit("  Passwords do not match; nothing changed.")

    try:
        account = auth.bootstrap_superadmin(db, args.email, password)
    except HTTPException as exc:
        sys.exit(f"  {exc.detail}; nothing changed.")
    print(f"  {'Promoted' if exists else 'Created'} superadmin {account['email']}")


if __name__ == "__main__":
    main()
