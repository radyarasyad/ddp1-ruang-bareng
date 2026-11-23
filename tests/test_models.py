import unittest
from datetime import datetime

from app.models import (
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FULL,
    STATUS_OPEN,
    StudySession,
    compute_display_status,
    slots_left,
)

NOW = datetime(2026, 12, 1, 9, 0)


def make_session(capacity=5, status=STATUS_OPEN, ends_at="2026-12-02T15:00"):
    return StudySession(
        id="s1", host_user_id="u1", title="Belajar", subject="DDP1", topic=None,
        description=None, starts_at="2026-12-02T13:00", ends_at=ends_at, mode="OFFLINE",
        location_text="Perpustakaan", map_url=None, meeting_url=None,
        capacity=capacity, status=status, created_at="2026-11-30T10:00:00",
    )


class ComputeDisplayStatusTest(unittest.TestCase):
    def test_open_when_slots_remain(self):
        self.assertEqual(compute_display_status(make_session(), 3, NOW), STATUS_OPEN)

    def test_full_counts_host(self):
        # Kapasitas 5 = host + 4 peserta. 4 peserta aktif berarti penuh.
        self.assertEqual(compute_display_status(make_session(), 4, NOW), STATUS_FULL)

    def test_cancelled_is_kept(self):
        session = make_session(status=STATUS_CANCELLED)
        self.assertEqual(compute_display_status(session, 0, NOW), STATUS_CANCELLED)

    def test_completed_from_status(self):
        session = make_session(status=STATUS_COMPLETED)
        self.assertEqual(compute_display_status(session, 0, NOW), STATUS_COMPLETED)

    def test_completed_when_time_passed(self):
        session = make_session(ends_at="2026-11-30T15:00")
        self.assertEqual(compute_display_status(session, 0, NOW), STATUS_COMPLETED)


class NowWibTest(unittest.TestCase):
    def test_now_wib_is_utc_plus_7(self):
        from datetime import timedelta, timezone
        from app.models import now_wib
        utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
        difference = now_wib() - utc_now
        # Selisih harus 7 jam (beri toleransi beberapa detik untuk waktu eksekusi).
        self.assertLess(abs(difference - timedelta(hours=7)), timedelta(seconds=5))
        self.assertIsNone(now_wib().tzinfo)


class SlotsLeftTest(unittest.TestCase):
    def test_slots_left(self):
        self.assertEqual(slots_left(make_session(), 3), 1)

    def test_never_negative(self):
        self.assertEqual(slots_left(make_session(capacity=2), 5), 0)


if __name__ == "__main__":
    unittest.main()
