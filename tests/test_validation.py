import unittest

from app.validation import is_valid_http_url, validate_session, validate_session_fields
from tests.helpers import NOW, valid_offline_data, valid_online_data


class UrlTest(unittest.TestCase):
    def test_http_and_https_are_valid(self):
        self.assertTrue(is_valid_http_url("https://maps.google.com/?q=UI"))
        self.assertTrue(is_valid_http_url("http://example.com"))

    def test_dangerous_or_incomplete_urls_rejected(self):
        # T-14
        for url in ["javascript:alert(1)", "ftp://x", "maps.google.com", "", None, "https://"]:
            with self.subTest(url=url):
                self.assertFalse(is_valid_http_url(url))


class ValidateSessionTest(unittest.TestCase):
    def test_valid_offline(self):
        # T-01
        self.assertEqual(validate_session(valid_offline_data(), now=NOW), [])

    def test_empty_title_rejected(self):
        # T-02
        for title in ["", "   ", None]:
            with self.subTest(title=title):
                errors = validate_session_fields(valid_offline_data(title=title), now=NOW)
                self.assertIn("title", errors)

    def test_end_before_start_rejected(self):
        # T-03
        data = valid_offline_data(starts_at="2026-12-02T15:00", ends_at="2026-12-02T13:00")
        self.assertIn("ends_at", validate_session_fields(data, now=NOW))

    def test_start_in_past_rejected(self):
        data = valid_offline_data(starts_at="2026-11-30T13:00", ends_at="2026-11-30T15:00")
        self.assertIn("starts_at", validate_session_fields(data, now=NOW))

    def test_bad_date_format_rejected(self):
        data = valid_offline_data(starts_at="besok siang")
        self.assertIn("starts_at", validate_session_fields(data, now=NOW))

    def test_invalid_capacity_rejected(self):
        # T-04
        for capacity in ["0", "-1", "abc", "21", "2.5", "", None]:
            with self.subTest(capacity=capacity):
                errors = validate_session_fields(valid_offline_data(capacity=capacity), now=NOW)
                self.assertIn("capacity", errors)

    def test_capacity_boundaries_accepted(self):
        for capacity in ["2", "20", 5]:
            with self.subTest(capacity=capacity):
                errors = validate_session_fields(valid_offline_data(capacity=capacity), now=NOW)
                self.assertNotIn("capacity", errors)

    def test_offline_without_location_rejected(self):
        # T-05
        errors = validate_session_fields(valid_offline_data(location_text="  "), now=NOW)
        self.assertIn("location_text", errors)

    def test_offline_bad_map_url_rejected(self):
        errors = validate_session_fields(valid_offline_data(map_url="javascript:alert(1)"), now=NOW)
        self.assertIn("map_url", errors)

    def test_online_without_location_is_valid(self):
        # T-06
        self.assertEqual(validate_session(valid_online_data(), now=NOW), [])

    def test_online_without_meeting_url_rejected(self):
        errors = validate_session_fields(valid_online_data(meeting_url=""), now=NOW)
        self.assertIn("meeting_url", errors)

    def test_unknown_mode_rejected(self):
        self.assertIn("mode", validate_session_fields(valid_offline_data(mode="HYBRID"), now=NOW))

    def test_none_values_do_not_crash(self):
        data = {key: None for key in valid_offline_data()}
        errors = validate_session_fields(data, now=NOW)
        self.assertIn("title", errors)
        self.assertIn("capacity", errors)

    def test_title_too_long_rejected(self):
        errors = validate_session_fields(valid_offline_data(title="x" * 101), now=NOW)
        self.assertIn("title", errors)


if __name__ == "__main__":
    unittest.main()
