"""Быстрые тесты чистых функций (без Django и базы)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.identity import pure  # noqa: E402


class CodeTests(unittest.TestCase):
    def test_code_is_six_digits(self):
        for _ in range(200):
            code = pure.generate_code()
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isdigit())

    def test_hash_depends_on_secret_email_and_code(self):
        base = pure.hash_code("s", "a@x.ru", "123456")
        self.assertEqual(base, pure.hash_code("s", "a@x.ru", "123456"))
        self.assertNotEqual(base, pure.hash_code("t", "a@x.ru", "123456"))
        self.assertNotEqual(base, pure.hash_code("s", "b@x.ru", "123456"))
        self.assertNotEqual(base, pure.hash_code("s", "a@x.ru", "123457"))
        self.assertEqual(len(base), 64)

    def test_key_hashes_do_not_contain_input(self):
        key = pure.hash_key("code-request-email", "user@example.com")
        self.assertNotIn("user", key)
        self.assertNotEqual(key, pure.hash_key("code-request-ip", "user@example.com"))


class ClientIpTests(unittest.TestCase):
    def test_forwarded_header_ignored_without_trusted_proxy(self):
        self.assertEqual(pure.extract_client_ip("10.0.0.1", "1.2.3.4", 0), "10.0.0.1")

    def test_single_proxy_uses_last_entry(self):
        self.assertEqual(pure.extract_client_ip("10.0.0.1", "6.6.6.6, 1.2.3.4", 1), "1.2.3.4")

    def test_two_proxies_use_second_from_end(self):
        self.assertEqual(pure.extract_client_ip("10.0.0.1", "6.6.6.6, 1.2.3.4, 10.0.0.9", 2), "1.2.3.4")

    def test_short_header_falls_back_to_remote(self):
        self.assertEqual(pure.extract_client_ip("10.0.0.1", "1.2.3.4", 2), "10.0.0.1")
        self.assertEqual(pure.extract_client_ip(None, None, 0), "unknown")


class NameAndPhoneTests(unittest.TestCase):
    def test_name_is_cleaned(self):
        self.assertEqual(pure.clean_display_name("  Анна   Иванова "), "Анна Иванова")

    def test_name_rejects_bad_values(self):
        for bad in ("", " ", "A", "x" * 61, "<b>Анна</b>", "Анна>", "Ан\x00на"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                pure.clean_display_name(bad)

    def test_phone_normalised_or_rejected(self):
        self.assertEqual(pure.clean_phone("+7 (900) 123-45-67"), "+79001234567")
        self.assertEqual(pure.clean_phone(""), "")
        for bad in ("abc", "123", "+7900123456789012", "8900-12"):
            with self.assertRaises(ValueError, msg=bad):
                pure.clean_phone(bad)


if __name__ == "__main__":
    unittest.main()
