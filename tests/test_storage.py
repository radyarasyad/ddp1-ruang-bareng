import os
import sqlite3
import tempfile
import unittest

from app import storage
from app.models import ENROLLMENT_CANCELLED, STATUS_OPEN, StudySession
from tests.helpers import make_conn


def make_session(host_id, capacity=5):
    return StudySession(
        id=storage.new_id(), host_user_id=host_id, title="Belajar", subject="DDP1",
        topic=None, description=None, starts_at="2026-12-02T13:00", ends_at="2026-12-02T15:00",
        mode="OFFLINE", location_text="Perpustakaan", map_url=None, meeting_url=None,
        capacity=capacity, status=STATUS_OPEN, created_at=storage.now_text(),
    )


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.host = storage.insert_user(self.conn, "host", "Host")
        self.user = storage.insert_user(self.conn, "budi", "Budi")

    def tearDown(self):
        self.conn.close()

    def test_insert_and_get_session(self):
        session = make_session(self.host.id)
        storage.insert_session(self.conn, session)
        self.assertEqual(storage.get_session(self.conn, session.id), session)

    def test_get_missing_returns_none(self):
        self.assertIsNone(storage.get_session(self.conn, "tidak-ada"))
        self.assertIsNone(storage.get_user(self.conn, "tidak-ada"))

    def test_duplicate_enrollment_rejected_by_database(self):
        session = make_session(self.host.id)
        storage.insert_session(self.conn, session)
        storage.insert_enrollment(self.conn, session.id, self.user.id)
        with self.assertRaises(sqlite3.IntegrityError):
            storage.insert_enrollment(self.conn, session.id, self.user.id)

    def test_count_only_active_members(self):
        session = make_session(self.host.id)
        storage.insert_session(self.conn, session)
        enrollment = storage.insert_enrollment(self.conn, session.id, self.user.id)
        self.assertEqual(storage.count_active_members(self.conn, session.id), 1)
        storage.set_enrollment_status(self.conn, enrollment.id, ENROLLMENT_CANCELLED)
        self.assertEqual(storage.count_active_members(self.conn, session.id), 0)

    def test_transaction_rolls_back_on_error(self):
        session = make_session(self.host.id)
        with self.assertRaises(RuntimeError):
            with storage.transaction(self.conn):
                storage.insert_session(self.conn, session)
                raise RuntimeError("gagal di tengah jalan")
        self.assertIsNone(storage.get_session(self.conn, session.id))

    def test_capacity_check_in_database(self):
        with self.assertRaises(sqlite3.IntegrityError):
            storage.insert_session(self.conn, make_session(self.host.id, capacity=1))

    def test_list_sessions_joined_and_members(self):
        session = make_session(self.host.id)
        storage.insert_session(self.conn, session)
        storage.insert_enrollment(self.conn, session.id, self.user.id)
        self.assertEqual([s.id for s in storage.list_sessions_joined(self.conn, self.user.id)], [session.id])
        self.assertEqual([u.id for u in storage.list_active_members(self.conn, session.id)], [self.user.id])


class HelperTest(unittest.TestCase):
    def test_detect_postgres_url(self):
        self.assertTrue(storage.is_postgres_url("postgresql://u:p@host/db"))
        self.assertTrue(storage.is_postgres_url("postgres://u:p@host/db"))
        self.assertFalse(storage.is_postgres_url("instance/ruangbareng.db"))
        self.assertFalse(storage.is_postgres_url(":memory:"))

    def test_placeholder_conversion(self):
        self.assertEqual(
            storage.to_postgres_sql("SELECT * FROM users WHERE id = ? AND username = ?"),
            "SELECT * FROM users WHERE id = %s AND username = %s",
        )


class PersistenceTest(unittest.TestCase):
    def test_data_survives_reconnect(self):
        # T-12: data tetap ada setelah koneksi ditutup dan dibuka lagi.
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.db")
            conn = storage.connect(path)
            storage.init_db(conn)
            host = storage.insert_user(conn, "host", "Host")
            session = make_session(host.id)
            storage.insert_session(conn, session)
            conn.close()

            conn = storage.connect(path)
            self.assertEqual(storage.get_session(conn, session.id).title, "Belajar")
            conn.close()


if __name__ == "__main__":
    unittest.main()
