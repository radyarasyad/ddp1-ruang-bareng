"""Test yang sama pentingnya dengan test SQLite, tapi dijalankan ke Postgres sungguhan.

Test ini dilewati (skip) kecuali variabel TEST_DATABASE_URL diisi, misalnya:
    $env:TEST_DATABASE_URL = "postgresql://user:pass@localhost:5432/ruangbareng_test"
    python -m unittest tests.test_postgres -v

PERINGATAN: test ini menghapus semua tabel di database tersebut.
Jangan arahkan ke database Neon yang dipakai website.
"""

import os
import threading
import unittest

from app import storage
from app.services import enrollment_service, session_service
from tests.helpers import NOW, valid_offline_data

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")


def fresh_database():
    """Koneksi ke database kosong: hapus tabel lama lalu buat ulang."""
    conn = storage.connect(TEST_DATABASE_URL)
    conn.execute("DROP TABLE IF EXISTS enrollments, study_sessions, users")
    storage.init_db(conn)
    return conn


@unittest.skipUnless(TEST_DATABASE_URL, "TEST_DATABASE_URL tidak diisi")
class PostgresFlowTest(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_database()
        self.host = storage.insert_user(self.conn, "host", "Host")
        self.users = [storage.insert_user(self.conn, f"u{i}", f"User {i}") for i in range(3)]

    def tearDown(self):
        self.conn.close()

    def create(self, capacity="3"):
        ok, session = session_service.create_session(
            self.conn, self.host.id, valid_offline_data(capacity=capacity), now=NOW
        )
        self.assertTrue(ok, session)
        return session

    def test_create_and_list(self):
        session = self.create()
        items = session_service.list_open_sessions(self.conn, keyword="struktur", now=NOW)
        self.assertEqual([item["session"].id for item in items], [session.id])
        self.assertIsInstance(items[0]["session"].capacity, int)

    def test_join_duplicate_full_and_rejoin(self):
        session = self.create(capacity="3")
        join = enrollment_service.join_session
        self.assertTrue(join(self.conn, session.id, self.users[0].id, now=NOW)[0])
        self.assertFalse(join(self.conn, session.id, self.users[0].id, now=NOW)[0])  # T-08
        self.assertTrue(join(self.conn, session.id, self.users[1].id, now=NOW)[0])
        self.assertFalse(join(self.conn, session.id, self.users[2].id, now=NOW)[0])  # T-09 penuh

        enrollment_service.leave_session(self.conn, session.id, self.users[0].id, now=NOW)
        self.assertTrue(join(self.conn, session.id, self.users[0].id, now=NOW)[0])  # D-03
        self.assertEqual(storage.count_active_members(self.conn, session.id), 2)

    def test_cancel_by_host_only(self):
        session = self.create()
        self.assertFalse(session_service.cancel_session(self.conn, session.id, self.users[0].id, now=NOW)[0])
        self.assertTrue(session_service.cancel_session(self.conn, session.id, self.host.id, now=NOW)[0])

    def test_transaction_rollback(self):
        with self.assertRaises(RuntimeError):
            with storage.transaction(self.conn):
                storage.insert_user(self.conn, "sementara", "Sementara")
                raise RuntimeError("gagal")
        self.assertIsNone(storage.get_user_by_username(self.conn, "sementara"))

    def test_concurrent_join_last_slot(self):
        # T-15 di Postgres: kunci advisory harus membuat join kedua menunggu.
        session = self.create(capacity="2")
        results = []
        barrier = threading.Barrier(2)

        def try_join(user):
            conn = storage.connect(TEST_DATABASE_URL)
            barrier.wait()
            results.append(enrollment_service.join_session(conn, session.id, user.id, now=NOW)[0])
            conn.close()

        threads = [threading.Thread(target=try_join, args=(u,)) for u in self.users[:2]]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(storage.count_active_members(self.conn, session.id), 1)


if __name__ == "__main__":
    unittest.main()
