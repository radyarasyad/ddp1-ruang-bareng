"""Aturan bisnis untuk sesi belajar: buat, cari, lihat detail, batalkan.

Setiap fungsi yang bisa gagal mengembalikan tuple (berhasil, hasil):
- berhasil : True/False
- hasil    : objek/data jika berhasil, atau pesan error jika gagal
"""

from datetime import datetime

from app import storage
from app.models import (
    MODE_OFFLINE,
    MODE_ONLINE,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FULL,
    STATUS_OPEN,
    StudySession,
    compute_display_status,
    now_wib,
    slots_left,
)
from app.validation import clean_text, validate_session_fields


def _optional_text(value):
    """Teks kosong disimpan sebagai None (NULL di database)."""
    text = clean_text(value)
    return text if text else None


def _normalize_time(value):
    """'2026-12-01T14:00:00' -> '2026-12-01T14:00' supaya format seragam."""
    return datetime.fromisoformat(clean_text(value)).isoformat(timespec="minutes")


def _build_item(conn, session, now):
    """Menggabungkan data sesi dengan angka yang dihitung (peserta, slot, status)."""
    active_count = storage.count_active_members(conn, session.id)
    return {
        "session": session,
        "active_count": active_count,
        "total_people": active_count + 1,  # +1 untuk host
        "slots_left": slots_left(session, active_count),
        "display_status": compute_display_status(session, active_count, now),
    }


# ---------------------------------------------------------------------------
# Buat sesi (US-04, US-08)
# ---------------------------------------------------------------------------
def create_session(conn, host_user_id, data, now=None):
    """Memvalidasi lalu menyimpan sesi baru.

    Mengembalikan (True, StudySession) atau (False, dict error per field).
    """
    errors = validate_session_fields(data, now)
    if errors:
        return False, errors  # Data tidak valid: tidak ada yang disimpan.

    mode = clean_text(data.get("mode")).upper()
    is_offline = mode == MODE_OFFLINE

    session = StudySession(
        id=storage.new_id(),
        host_user_id=host_user_id,
        title=clean_text(data.get("title")),
        subject=clean_text(data.get("subject")),
        topic=_optional_text(data.get("topic")),
        description=_optional_text(data.get("description")),
        starts_at=_normalize_time(data.get("starts_at")),
        ends_at=_normalize_time(data.get("ends_at")),
        mode=mode,
        # Simpan hanya informasi yang relevan untuk mode yang dipilih.
        location_text=_optional_text(data.get("location_text")) if is_offline else None,
        map_url=_optional_text(data.get("map_url")) if is_offline else None,
        meeting_url=_optional_text(data.get("meeting_url")) if mode == MODE_ONLINE else None,
        capacity=int(clean_text(data.get("capacity"))),
        status=STATUS_OPEN,
        created_at=storage.now_text(),
    )
    storage.insert_session(conn, session)
    return True, session


# ---------------------------------------------------------------------------
# Daftar dan pencarian (US-01, US-02)
# ---------------------------------------------------------------------------
def list_open_sessions(conn, keyword=None, subject=None, now=None):
    """Sesi yang masih akan berlangsung (OPEN atau FULL), bisa difilter.

    keyword dicocokkan ke judul, mata kuliah, dan topik tanpa memedulikan
    huruf besar/kecil. subject harus sama persis (juga tanpa memedulikan huruf).
    """
    if now is None:
        now = now_wib()
    keyword_text = clean_text(keyword).lower()
    subject_text = clean_text(subject).lower()

    results = []
    for session in storage.list_sessions(conn, [STATUS_OPEN]):
        item = _build_item(conn, session, now)

        # Sesi yang sudah lewat waktunya tidak ditampilkan di daftar utama.
        if item["display_status"] not in (STATUS_OPEN, STATUS_FULL):
            continue

        if keyword_text:
            searchable = " ".join([session.title, session.subject, session.topic or ""]).lower()
            if keyword_text not in searchable:
                continue

        if subject_text and session.subject.lower() != subject_text:
            continue

        results.append(item)

    # Urutkan berdasarkan waktu mulai: sesi terdekat tampil paling atas.
    results.sort(key=lambda item: item["session"].starts_at)
    return results


def list_subjects(conn, now=None):
    """Daftar mata kuliah unik dari sesi yang masih tampil, untuk pilihan filter."""
    subjects = set()
    for item in list_open_sessions(conn, now=now):
        subjects.add(item["session"].subject)
    return sorted(subjects, key=str.lower)


# ---------------------------------------------------------------------------
# Detail (US-03)
# ---------------------------------------------------------------------------
def get_session_detail(conn, session_id, now=None):
    """Data lengkap satu sesi, atau None jika tidak ditemukan."""
    if now is None:
        now = now_wib()
    session = storage.get_session(conn, session_id)
    if session is None:
        return None

    item = _build_item(conn, session, now)
    item["host"] = storage.get_user(conn, session.host_user_id)
    item["members"] = storage.list_active_members(conn, session.id)
    return item


# ---------------------------------------------------------------------------
# Pembatalan oleh host (US-07)
# ---------------------------------------------------------------------------
def cancel_session(conn, session_id, user_id, now=None):
    """Host membatalkan sesinya. Data tidak dihapus; status menjadi CANCELLED."""
    if now is None:
        now = now_wib()
    session = storage.get_session(conn, session_id)
    if session is None:
        return False, "Sesi tidak ditemukan."
    if session.host_user_id != user_id:
        return False, "Hanya host yang boleh membatalkan sesi ini."

    active_count = storage.count_active_members(conn, session_id)
    status = compute_display_status(session, active_count, now)
    if status == STATUS_CANCELLED:
        return False, "Sesi ini sudah dibatalkan."
    if status == STATUS_COMPLETED:
        return False, "Sesi yang sudah selesai tidak bisa dibatalkan."

    storage.update_session_status(conn, session_id, STATUS_CANCELLED)
    return True, "Sesi dibatalkan. Peserta akan melihat statusnya di halaman sesi."


# ---------------------------------------------------------------------------
# Sesi saya
# ---------------------------------------------------------------------------
def list_my_sessions(conn, user_id, now=None):
    """Sesi yang dibuat (hosted) dan diikuti (joined) oleh satu user."""
    if now is None:
        now = now_wib()
    hosted = [_build_item(conn, s, now) for s in storage.list_sessions_by_host(conn, user_id)]
    joined = [_build_item(conn, s, now) for s in storage.list_sessions_joined(conn, user_id)]
    return {"hosted": hosted, "joined": joined}
