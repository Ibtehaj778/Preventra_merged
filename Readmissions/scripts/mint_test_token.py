#!/usr/bin/env python3
"""Mint a shared-login token without going through the login endpoint.

The signing secret is symmetric, so holding it is enough to produce a token the
products will accept. That makes it possible to exercise the portal and either
frontend end to end before the auth service is reachable, or when testing what a
user with narrower access sees.

    python scripts/mint_test_token.py                      # both apps, 12 hours
    python scripts/mint_test_token.py --app-access glp1    # GLP-1 only
    python scripts/mint_test_token.py --expires-in -60     # already expired
    python scripts/mint_test_token.py --portal-url http://localhost:8080
                                                           # a ready-to-open link

A token from here proves a verifier is self-consistent. It does NOT prove the
secret matches the auth service's - only a token from /auth/login shows that.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import jwt

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    env = ROOT / ".env"
    if not env.is_file():
        return
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    load_env()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sub", default="6aacf23f9088e24368c49583",
                    help="account id the token refers to")
    ap.add_argument("--email", default="doc@test.com")
    ap.add_argument("--role", default="Doctor")
    ap.add_argument("--org-id", default="city-hospital")
    ap.add_argument("--app-access", nargs="+", default=["glp1", "readmissions"],
                    help="applications this token grants (default: both)")
    ap.add_argument("--expires-in", type=int, default=12 * 60 * 60,
                    help="seconds until exp; negative for an already-expired token")
    ap.add_argument("--portal-url", help="print a #token=... link into the portal")
    ap.add_argument("--app-url", help="print a #token=... link straight into an app")
    args = ap.parse_args()

    secret = os.environ.get("SHARED_SECRET_KEY", "")
    if not secret:
        print("SHARED_SECRET_KEY is not set (checked the environment and .env)",
              file=sys.stderr)
        return 1

    claims = {"sub": args.sub, "email": args.email, "role": args.role,
              "org_id": args.org_id, "app_access": list(args.app_access),
              "exp": int(time.time()) + args.expires_in}
    token = jwt.encode(claims, secret, algorithm="HS256")

    print(token)
    for base in (args.portal_url, args.app_url):
        if base:
            print(f"\n{base.rstrip('/')}/#token={quote(token)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
