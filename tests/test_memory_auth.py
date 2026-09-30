import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import jwt

from app.auth import TokenVerifier, get_verifier


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.secret = "synthetic-test-signing-key-at-least-48-characters-long"
        self.user = uuid4()
        self.verifier = TokenVerifier(issuer="test", audience="trip", development_secret=self.secret)

    def token(self, **patch):
        claims = dict(sub=str(self.user), iss="test", aud="trip", iat=int(time.time()), exp=int(time.time())+60)
        claims.update(patch)
        return jwt.encode(claims, self.secret, algorithm="HS256")

    def test_verified_subject_defines_identity(self):
        identity = self.verifier.verify(self.token(user_id=str(uuid4())))
        self.assertEqual(identity.user_id, self.user)

    def test_rejects_wrong_issuer_audience_expired_and_future_tokens(self):
        for patch in ({"iss": "wrong"}, {"aud": "wrong"}, {"exp": int(time.time())-1},
                      {"iat": int(time.time())+60}, {"sub": ""}):
            with self.subTest(patch=patch), self.assertRaises(jwt.InvalidTokenError):
                self.verifier.verify(self.token(**patch))

    def test_signature_and_algorithm_are_pinned(self):
        for token in (jwt.encode({"sub": str(self.user)}, "different-secret-32-characters-long", algorithm="HS256"),
                      jwt.encode({"sub": str(self.user)}, self.secret, algorithm="HS384")):
            with self.assertRaises(jwt.InvalidTokenError):
                self.verifier.verify(token)

    def test_missing_claims_are_rejected(self):
        with self.assertRaises(jwt.InvalidTokenError):
            self.verifier.verify(jwt.encode({"sub": str(self.user)}, self.secret, algorithm="HS256"))

    def test_development_mode_is_explicit(self):
        get_verifier.cache_clear()
        self.addCleanup(get_verifier.cache_clear)
        with patch.dict("os.environ", {"TRAVEL_AUTH_MODE": "development", "APP_ENV": "production"}, clear=True):
            with self.assertRaises(ValueError):
                get_verifier()
