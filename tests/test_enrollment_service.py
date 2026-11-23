import os
import tempfile
import threading
import unittest

from app import storage
from app.services import enrollment_service, session_service
from tests.helpers import NOW, make_conn, valid_offline_data


class EnrollmentTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.host = storage.insert_user(self.conn, "host", "Host")
        self.users = [storage.insert_user(self.conn, f"u{i}", f"User {i}") for i in range(4)]

    def tearDown(self):
        self.conn.close()

    def create(self, capacity="5"):
        ok, session = session_service.create_session(
            self.conn, self.host.id, valid_offline_data(capacity=capacity), now=NOW
        )
        self.assertTrue(ok)
        return session

    def join(self, session, user):
        return enrollment_service.join_session(self.conn, session.id, user.id, now=NOW)

    def count(self, session):
        return storage.count_active_members(self.conn, session.id)

    def test_join_open_session(self):
        # T-07
        session = self.create()
        ok, _ = self.join(session, self.users[0])
        self.assertTrue(ok)
        self.assertEqual(self.count(session), 1)

    def test_join_twice_rejected(self):
        # T-08
        session = self.create()
        self.join(session, self.users[0])
        ok, message = self.join(session, self.users[0])
        self.assertFalse(ok)
        self.assertIn("sudah bergabung", message)
        self.assertEqual(self.count(session), 1)

    def test_join_full_rejected(self):
        # T-09: kapasitas 3 = host + 2 peserta.
        session = self.create(capacity="3")
        self.assertTrue(self.join(session, self.users[0])[0])
        self.assertTrue(self.join(session, self.users[1])[0])
        ok, message = self.join(session, self.users[2])
        self.assertFalse(ok)
        self.assertIn("penuh", message)
        self.assertEqual(self.count(session), 2)

    def test_join_cancelled_rejected(self):
        # T-10
        session = self.create()
        session_service.cancel_session(self.conn, session.id, self.host.id, now=NOW)
        ok, _ = self.join(session, self.users[0])
        self.assertFalse(ok)
        self.assertEqual(self.count(session), 0)

    def test_host_cannot_join_own_session(self):
        session = self.create()
        ok, _ = self.join(session, self.host)
        self.assertFalse(ok)

    def test_join_missing_session(self):
        ok, message = enrollment_service.join_session(self.conn, "tidak-ada", self.users[0].id, now=NOW)
        self.assertFalse(ok)
        self.assertIn("tidak ditemukan", message)

    def test_leave_then_rejoin_reuses_row(self):
        # Keputusan D-03
        session = self.create()
        self.join(session, self.users[0])
        ok, _ = enrollment_service.leave_session(self.conn, session.id, self.users[0].id, now=NOW)
        self.assertTrue(ok)
        self.assertEqual(self.count(session), 0)

        ok, _ = self.join(session, self.users[0])
        self.assertTrue(ok)
        rows = self.conn.execute(
            "SELECT COUNT(*) FROM enrollments WHERE session_id = ?", (session.id,)
        ).fetchone()[0]
        self.assertEqual(rows, 1)

    def test_leave_without_joining_rejected(self):
        session = self.create()
        ok, _ = enrollment_service.leave_session(self.conn, session.id, self.users[0].id, now=NOW)
        self.assertFalse(ok)

    def test_leave_frees_a_slot(self):
        session = self.create(capacity="2")
        self.join(session, self.users[0])
        self.assertFalse(self.join(session, self.users[1])[0])
        enrollment_service.leave_session(self.conn, session.id, self.users[0].id, now=NOW)
        self.assertTrue(self.join(session, self.users[1])[0])


class ConcurrentJoinTest(unittest.TestCase):
    def test_two_joins_for_last_slot(self):
        # T-15: dua orang menekan Join hampir bersamaan untuk slot terakhir.
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "race.db")
            setup = storage.connect(path)
            storage.init_db(setup)
            host = storage.insert_user(setup, "host", "Host")
            a = storage.insert_user(setup, "a", "A")
            b = storage.insert_user(setup, "b", "B")
            ok, session = session_service.create_session(
                setup, host.id, valid_offline_data(capacity="2"), now=NOW
            )
            self.assertTrue(ok)

            results = []
            start_signal = threading.Barrier(2)  # Supaya kedua thread mulai bersamaan.

            def try_join(user):
                conn = storage.connect(path)  # Tiap "pengguna" punya koneksi sendiri.
                start_signal.wait()
                results.append(enrollment_service.join_session(conn, session.id, user.id, now=NOW)[0])
                conn.close()

            threads = [threading.Thread(target=try_join, args=(user,)) for user in (a, b)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(sorted(results), [False, True])
            self.assertEqual(storage.count_active_members(setup, session.id), 1)
            setup.close()


if __name__ == "__main__":
    unittest.main()
