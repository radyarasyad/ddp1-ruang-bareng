import unittest

from app import storage
from app.models import STATUS_CANCELLED, STATUS_FULL, STATUS_OPEN
from app.services import enrollment_service, session_service
from tests.helpers import NOW, make_conn, valid_offline_data, valid_online_data


class SessionServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.host = storage.insert_user(self.conn, "host", "Host")
        self.other = storage.insert_user(self.conn, "budi", "Budi")

    def tearDown(self):
        self.conn.close()

    def create(self, **overrides):
        ok, session = session_service.create_session(
            self.conn, self.host.id, valid_offline_data(**overrides), now=NOW
        )
        self.assertTrue(ok, session)
        return session

    def test_valid_session_saved_and_listed(self):
        # T-01
        session = self.create()
        items = session_service.list_open_sessions(self.conn, now=NOW)
        self.assertEqual([item["session"].id for item in items], [session.id])
        self.assertEqual(items[0]["display_status"], STATUS_OPEN)
        self.assertEqual(items[0]["total_people"], 1)

    def test_invalid_input_creates_no_record(self):
        # T-02
        ok, errors = session_service.create_session(
            self.conn, self.host.id, valid_offline_data(title=""), now=NOW
        )
        self.assertFalse(ok)
        self.assertIn("title", errors)
        self.assertEqual(storage.list_sessions(self.conn), [])

    def test_online_session_drops_location_fields(self):
        ok, session = session_service.create_session(
            self.conn, self.host.id, valid_online_data(location_text="Kantin"), now=NOW
        )
        self.assertTrue(ok)
        self.assertIsNone(session.location_text)
        self.assertEqual(session.meeting_url, "https://meet.google.com/abc-defg-hij")

    def test_keyword_search_case_insensitive(self):
        self.create(title="Belajar Struktur Data")
        self.create(title="Kalkulus bareng", subject="Kalkulus 1", topic="Integral")
        items = session_service.list_open_sessions(self.conn, keyword="struktur", now=NOW)
        self.assertEqual([i["session"].title for i in items], ["Belajar Struktur Data"])

    def test_search_without_match_returns_empty(self):
        # T-13
        self.create()
        self.assertEqual(session_service.list_open_sessions(self.conn, keyword="biologi", now=NOW), [])

    def test_subject_filter(self):
        self.create(subject="Kalkulus 1")
        self.create(subject="Struktur Data")
        items = session_service.list_open_sessions(self.conn, subject="kalkulus 1", now=NOW)
        self.assertEqual([i["session"].subject for i in items], ["Kalkulus 1"])

    def test_sorted_by_start_time(self):
        later = self.create(starts_at="2026-12-05T10:00", ends_at="2026-12-05T12:00")
        sooner = self.create(starts_at="2026-12-03T10:00", ends_at="2026-12-03T12:00")
        ids = [i["session"].id for i in session_service.list_open_sessions(self.conn, now=NOW)]
        self.assertEqual(ids, [sooner.id, later.id])

    def test_full_session_still_listed(self):
        session = self.create(capacity="2")
        enrollment_service.join_session(self.conn, session.id, self.other.id, now=NOW)
        items = session_service.list_open_sessions(self.conn, now=NOW)
        self.assertEqual(items[0]["display_status"], STATUS_FULL)

    def test_cancelled_not_listed(self):
        session = self.create()
        session_service.cancel_session(self.conn, session.id, self.host.id, now=NOW)
        self.assertEqual(session_service.list_open_sessions(self.conn, now=NOW), [])

    def test_non_host_cannot_cancel(self):
        # T-11
        session = self.create()
        ok, _ = session_service.cancel_session(self.conn, session.id, self.other.id, now=NOW)
        self.assertFalse(ok)
        self.assertEqual(storage.get_session(self.conn, session.id).status, STATUS_OPEN)

    def test_host_cancel_changes_status(self):
        session = self.create()
        ok, _ = session_service.cancel_session(self.conn, session.id, self.host.id, now=NOW)
        self.assertTrue(ok)
        self.assertEqual(storage.get_session(self.conn, session.id).status, STATUS_CANCELLED)
        ok, _ = session_service.cancel_session(self.conn, session.id, self.host.id, now=NOW)
        self.assertFalse(ok)  # Tidak bisa dibatalkan dua kali.

    def test_detail_contains_host_and_members(self):
        session = self.create()
        enrollment_service.join_session(self.conn, session.id, self.other.id, now=NOW)
        detail = session_service.get_session_detail(self.conn, session.id, now=NOW)
        self.assertEqual(detail["host"].display_name, "Host")
        self.assertEqual([m.display_name for m in detail["members"]], ["Budi"])
        self.assertIsNone(session_service.get_session_detail(self.conn, "tidak-ada", now=NOW))

    def test_my_sessions(self):
        session = self.create()
        enrollment_service.join_session(self.conn, session.id, self.other.id, now=NOW)
        mine = session_service.list_my_sessions(self.conn, self.other.id, now=NOW)
        self.assertEqual(len(mine["joined"]), 1)
        self.assertEqual(mine["hosted"], [])


if __name__ == "__main__":
    unittest.main()
