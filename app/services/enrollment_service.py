"""Aturan bergabung (join) dan keluar (leave) dari sesi.

Bagian paling kritis aplikasi: tidak boleh ada pendaftaran ganda dan
jumlah orang tidak boleh melebihi kapasitas, bahkan ketika dua orang
menekan tombol Join hampir bersamaan.
"""

from datetime import datetime

from app import storage
from app.models import (
    ENROLLMENT_ACTIVE,
    ENROLLMENT_CANCELLED,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FULL,
    compute_display_status,
)


def join_session(conn, session_id, user_id, now=None):
    """Mendaftarkan user ke sesi. Mengembalikan (berhasil, pesan).

    Semua pemeriksaan dan penulisan terjadi di dalam SATU transaksi.
    Selama transaksi berjalan, proses lain yang ingin menulis harus menunggu,
    sehingga jumlah peserta yang kita hitung pasti masih benar saat kita menyimpan.
    """
    if now is None:
        now = datetime.now()

    with storage.transaction(conn):
        session = storage.get_session(conn, session_id)
        if session is None:
            return False, "Sesi tidak ditemukan."

        active_count = storage.count_active_members(conn, session_id)
        status = compute_display_status(session, active_count, now)

        # Urutan pemeriksaan mengikuti flowchart blueprint §8.3.
        if status in (STATUS_CANCELLED, STATUS_COMPLETED):
            return False, "Sesi tidak lagi menerima peserta."

        if session.host_user_id == user_id:
            return False, "Kamu adalah host sesi ini, jadi sudah termasuk peserta."

        enrollment = storage.get_enrollment(conn, session_id, user_id)
        if enrollment is not None and enrollment.status == ENROLLMENT_ACTIVE:
            return False, "Kamu sudah bergabung di sesi ini."

        if status == STATUS_FULL:
            return False, "Sesi sudah penuh."

        # Pernah keluar sebelumnya? Aktifkan lagi baris lama (keputusan D-03),
        # karena UNIQUE(session_id, user_id) menolak baris kedua.
        if enrollment is None:
            storage.insert_enrollment(conn, session_id, user_id)
        else:
            storage.set_enrollment_status(conn, enrollment.id, ENROLLMENT_ACTIVE)

    return True, "Berhasil bergabung. Sampai jumpa di sesi!"


def leave_session(conn, session_id, user_id, now=None):
    """Membatalkan keikutsertaan. Baris tidak dihapus; status menjadi CANCELLED."""
    if now is None:
        now = datetime.now()

    with storage.transaction(conn):
        session = storage.get_session(conn, session_id)
        if session is None:
            return False, "Sesi tidak ditemukan."

        active_count = storage.count_active_members(conn, session_id)
        status = compute_display_status(session, active_count, now)
        if status in (STATUS_CANCELLED, STATUS_COMPLETED):
            return False, "Sesi ini sudah ditutup."

        enrollment = storage.get_enrollment(conn, session_id, user_id)
        if enrollment is None or enrollment.status != ENROLLMENT_ACTIVE:
            return False, "Kamu belum terdaftar di sesi ini."

        storage.set_enrollment_status(conn, enrollment.id, ENROLLMENT_CANCELLED)

    return True, "Kamu sudah keluar dari sesi ini."
