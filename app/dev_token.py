"""Print a short-lived local-development token for an explicitly chosen user.

Run: python -m app.dev_token --user-id YOUR_UUID
The signing secret must already be configured; this command never prints it.
Production authentication must use your OIDC identity provider instead.
"""

import argparse
import time
from uuid import UUID

from dotenv import load_dotenv
import jwt

from app.auth import get_verifier


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", type=UUID, required=True)
    args = parser.parse_args()
    load_dotenv()
    verifier = get_verifier()
    if verifier.secret is None:
        parser.error("Token creation requires explicit development authentication configuration")
    now = int(time.time())
    print(jwt.encode({"sub": str(args.user_id), "iss": verifier.issuer,
                      "aud": verifier.audience, "iat": now, "exp": now + 3600},
                     verifier.secret, algorithm="HS256"))


if __name__ == "__main__":
    main()
