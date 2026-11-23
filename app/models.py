"""Bentuk data RuangBareng dan aturan status sesi.

File ini sengaja tidak meng-import modul lain di dalam app/, supaya bisa
dipakai oleh semua modul tanpa membuat import melingkar.
"""

from dataclasses import dataclass
from datetime import datetime

# ---------------------------------------------------------------------------
# Konstanta. Ditulis sekali di sini supaya tidak ada salah ketik "OPNE" di file lain.
# ---------------------------------------------------------------------------
MODE_ONLINE = "ONLINE"
MODE_OFFLINE = "OFFLINE"
VALID_MODES = {MODE_ONLINE, MODE_OFFLINE}

STATUS_OPEN = "OPEN"
STATUS_FULL = "FULL"            # Tidak pernah disimpan; dihitung otomatis (keputusan D-02).
STATUS_CANCELLED = "CANCELLED"
STATUS_COMPLETED = "COMPLETED"
STORED_SESSION_STATUSES = {STATUS_OPEN, STATUS_CANCELLED, STATUS_COMPLETED}

ENROLLMENT_ACTIVE = "ACTIVE"
ENROLLMENT_CANCELLED = "CANCELLED"

# Kapasitas menghitung host (keputusan D-01). Harus sama dengan CHECK di schema.sql.
MIN_CAPACITY = 2
MAX_CAPACITY = 20


# ---------------------------------------------------------------------------
# Dataclass: cara singkat membuat class yang tugas utamanya menyimpan data.
# Python otomatis membuatkan __init__, __repr__, dan __eq__ dari daftar field.
# ---------------------------------------------------------------------------
@dataclass
class User:
    id: str
    username: str
    display_name: str
    created_at: str


@dataclass
class StudySession:
    id: str
    host_user_id: str
    title: str
    subject: str
    topic: str | None
    description: str | None
    starts_at: str              # Teks ISO, misalnya "2026-12-01T14:00" (keputusan D-06)
    ends_at: str
    mode: str                   # MODE_ONLINE atau MODE_OFFLINE
    location_text: str | None   # Wajib untuk OFFLINE
    map_url: str | None         # Opsional untuk OFFLINE
    meeting_url: str | None     # Wajib untuk ONLINE
    capacity: int               # Jumlah orang total, termasuk host
    status: str                 # Salah satu dari STORED_SESSION_STATUSES
    created_at: str


@dataclass
class Enrollment:
    id: str
    session_id: str
    user_id: str
    status: str                 # ENROLLMENT_ACTIVE atau ENROLLMENT_CANCELLED
    joined_at: str


# ---------------------------------------------------------------------------
# Fungsi aturan status
# ---------------------------------------------------------------------------
def parse_time(text):
    """Mengubah teks ISO ("2026-12-01T14:00") menjadi objek datetime."""
    return datetime.fromisoformat(text)


def compute_display_status(session, active_count, now):
    """Menentukan status yang dilihat pengguna.

    active_count adalah jumlah peserta ACTIVE, tidak termasuk host.
    now adalah objek datetime waktu sekarang (dikirim dari luar supaya mudah diuji).
    """
    # 1. Status akhir yang disimpan di database tidak bisa berubah lagi.
    if session.status in (STATUS_CANCELLED, STATUS_COMPLETED):
        return session.status

    # 2. Sesi yang waktunya sudah selesai dianggap COMPLETED.
    if now >= parse_time(session.ends_at):
        return STATUS_COMPLETED

    # 3. Host ikut dihitung (+1). Kapasitas 5 = host + 4 peserta.
    if active_count + 1 >= session.capacity:
        return STATUS_FULL

    return STATUS_OPEN


def slots_left(session, active_count):
    """Sisa tempat untuk peserta baru. Tidak pernah bernilai negatif."""
    left = session.capacity - 1 - active_count
    return max(left, 0)
