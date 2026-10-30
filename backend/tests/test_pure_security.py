"""Быстрые тесты TOTP, одноразовых кодов и очистки журнала (без Django и базы)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.audit.pure import sanitize_changes  # noqa: E402
from apps.identity import totp  # noqa: E402

RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # ASCII "12345678901234567890" из RFC 6238


class TotpTests(unittest.TestCase):
    def test_rfc6238_vectors(self):
        # Значения из приложения B RFC 6238 (SHA-1), последние 6 цифр восьмизначных кодов.
        for moment, expected in ((59, "287082"), (1111111109, "081804"), (1111111111, "050471"),
                                 (1234567890, "005924"), (2000000000, "279037")):
            self.assertEqual(totp.totp_now(RFC_SECRET, moment), expected, moment)

    def test_window_accepts_neighbour_steps_only(self):
        now = 1111111109
        previous = totp.hotp(RFC_SECRET, totp.current_step(now) - 1)
        far = totp.hotp(RFC_SECRET, totp.current_step(now) - 3)
        self.assertIsNotNone(totp.verify_totp(RFC_SECRET, previous, now))
        self.assertIsNone(totp.verify_totp(RFC_SECRET, far, now))

    def test_replay_is_rejected(self):
        now = 1111111109
        code = totp.totp_now(RFC_SECRET, now)
        step = totp.verify_totp(RFC_SECRET, code, now)
        self.assertIsNotNone(step)
        self.assertIsNone(totp.verify_totp(RFC_SECRET, code, now, last_step=step))

    def test_garbage_is_rejected(self):
        for bad in ("", "12345", "1234567", "abcdef", None):
            self.assertIsNone(totp.verify_totp(RFC_SECRET, bad, 1111111109))

    def test_secret_and_uri(self):
        secret = totp.generate_secret()
        self.assertEqual(len(secret), 32)
        self.assertNotEqual(secret, totp.generate_secret())
        uri = totp.provisioning_uri(secret, "mod@example.com")
        self.assertTrue(uri.startswith("otpauth://totp/"))
        self.assertIn(f"secret={secret}", uri)
        self.assertIn("digits=6", uri)
        self.assertIn("period=30", uri)


class CodeTests(unittest.TestCase):
    def test_group_code_format_and_alphabet(self):
        code = totp.generate_group_code(2, 5)
        self.assertRegex(code, r"^[A-Z2-9]{5}-[A-Z2-9]{5}$")
        self.assertFalse(set(code.replace("-", "")) & set("01OI"))
        self.assertNotEqual(code, totp.generate_group_code(2, 5))

    def test_normalize_and_hash(self):
        self.assertEqual(totp.normalize_code(" abcde-fghjk "), "ABCDEFGHJK")
        a = totp.hash_secret_code("s", "invite", "abcd-efgh")
        self.assertEqual(a, totp.hash_secret_code("s", "invite", "ABCDEFGH"))
        self.assertNotEqual(a, totp.hash_secret_code("s", "backup", "ABCDEFGH"))
        self.assertNotEqual(a, totp.hash_secret_code("t", "invite", "ABCDEFGH"))
        self.assertEqual(len(a), 64)


class AuditSanitizeTests(unittest.TestCase):
    def test_secrets_are_dropped(self):
        cleaned = sanitize_changes(
            {"status": ["pending", "confirmed"], "password": "x", "otp_code": "123456", "token": "t",
             "backup_codes": "a", "api_key": "k", "secret": "s", "code_hash": "h", "title": "Вода"}
        )
        self.assertEqual(set(cleaned), {"status", "title"})

    def test_values_are_stringified_and_truncated(self):
        cleaned = sanitize_changes({"note": "x" * 500, "n": 5, "none": None, "pair": [1, None]})
        self.assertEqual(len(cleaned["note"]), 201)
        self.assertEqual(cleaned["n"], "5")
        self.assertEqual(cleaned["none"], "")
        self.assertEqual(cleaned["pair"], ["1", ""])

    def test_excluded_fields(self):
        self.assertEqual(sanitize_changes({"note": "имя", "status": "a"}, exclude=("note",)), {"status": "a"})

    def test_empty(self):
        self.assertEqual(sanitize_changes(None), {})


if __name__ == "__main__":
    unittest.main()
