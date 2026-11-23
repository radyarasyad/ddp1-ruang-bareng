"""Mengisi database dengan akun dan sesi DEMO untuk mencoba aplikasi.

Semua data di sini diberi label DEMO. Jangan disajikan sebagai penggunaan nyata.

Menjalankan dari folder root proyek:
    python scripts/seed_demo.py
"""

import os
import sys
from datetime import timedelta

# Supaya "import app" bisa ditemukan saat file ini dijalankan langsung.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config, storage  # noqa: E402
from app.models import now_wib  # noqa: E402
from app.services import enrollment_service, session_service  # noqa: E402

# Enam akun: cukup untuk demo kapasitas 5 (host + 4 peserta) lalu 1 orang ditolak.
DEMO_USERS = [
    ("host_a", "Host A (demo)"),
    ("peserta_b", "Peserta B (demo)"),
    ("peserta_c", "Peserta C (demo)"),
    ("peserta_d", "Peserta D (demo)"),
    ("peserta_e", "Peserta E (demo)"),
    ("peserta_f", "Peserta F (demo)"),
]


def at(days_from_now, hour, minute=0):
    """Waktu ISO untuk 'N hari lagi, jam sekian'."""
    day = now_wib() + timedelta(days=days_from_now)
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat(timespec="minutes")


def main():
    conn = storage.connect(config.DATABASE_TARGET)
    storage.init_db(conn)

    users = {}
    for username, display_name in DEMO_USERS:
        user = storage.get_user_by_username(conn, username)
        if user is None:
            user = storage.insert_user(conn, username, display_name)
            print(f"Akun dibuat   : {display_name}")
        users[username] = user

    # Sesi contoh hanya dibuat sekali.
    if storage.list_sessions_by_host(conn, users["host_a"].id):
        print("Sesi demo sudah ada, tidak dibuat ulang.")
        conn.close()
        return

    demo_sessions = [
        {
            "title": "DEMO - Latihan soal Struktur Data",
            "subject": "Struktur Data dan Algoritma",
            "topic": "Linked list dan stack",
            "description": "Data contoh untuk demo. Bawa laptop dan catatan kuliah minggu lalu.",
            "starts_at": at(2, 13), "ends_at": at(2, 15),
            "mode": "OFFLINE", "location_text": "Perpustakaan Pusat UI, lantai 2",
            "map_url": "https://maps.google.com/?q=Perpustakaan+Universitas+Indonesia",
            "capacity": "5",
        },
        {
            "title": "DEMO - Review kuis Matematika Diskret",
            "subject": "Matematika Diskret 1",
            "topic": "Induksi matematika",
            "description": "Data contoh untuk demo. Kita bahas soal kuis bersama.",
            "starts_at": at(3, 19), "ends_at": at(3, 20, 30),
            "mode": "ONLINE", "meeting_url": "https://meet.google.com/demo-ruang-bareng",
            "capacity": "4",
        },
    ]
    for data in demo_sessions:
        ok, result = session_service.create_session(conn, users["host_a"].id, data)
        if not ok:
            print("Gagal membuat sesi demo:", result)
            continue
        print(f"Sesi dibuat   : {result.title}")

    # Satu peserta sudah bergabung ke sesi pertama, supaya daftar tidak kosong.
    first = storage.list_sessions_by_host(conn, users["host_a"].id)[0]
    enrollment_service.join_session(conn, first.id, users["peserta_c"].id)

    conn.close()
    print("Selesai. Database:", "Postgres (DATABASE_URL)" if config.DATABASE_URL else config.DATABASE_PATH)


if __name__ == "__main__":
    main()
