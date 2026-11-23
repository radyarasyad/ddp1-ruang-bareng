"""Pemeriksaan input form "Buat sesi".

Validasi dilakukan di backend (Python), bukan hanya di browser, karena
pengguna bisa mengirim request tanpa melewati form HTML.
"""

from datetime import datetime
from urllib.parse import urlparse

from app.models import MAX_CAPACITY, MIN_CAPACITY, MODE_OFFLINE, MODE_ONLINE, VALID_MODES

MAX_TEXT_LENGTH = 100


def clean_text(value):
    """Mengubah None menjadi "" dan membuang spasi di awal/akhir."""
    if value is None:
        return ""
    return str(value).strip()


def is_valid_http_url(url):
    """True jika url memakai skema http/https dan punya nama domain.

    Contoh yang ditolak: "javascript:alert(1)", "ftp://x", "google.com" (tanpa skema).
    """
    text = clean_text(url)
    if not text:
        return False
    parsed = urlparse(text)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _parse_datetime(value):
    """Mengembalikan datetime, atau None jika formatnya salah."""
    try:
        result = datetime.fromisoformat(clean_text(value))
    except ValueError:
        return None
    # Kita hanya memakai waktu lokal (WIB) tanpa zona waktu (keputusan D-06).
    if result.tzinfo is not None:
        return None
    return result


def validate_session_fields(data, now=None):
    """Memeriksa data sesi dan mengembalikan dict {nama_field: pesan_error}.

    Dict kosong berarti semua data valid. Bentuk dict dipakai supaya UI
    bisa menampilkan pesan tepat di bawah input yang salah.
    """
    if now is None:
        now = datetime.now()
    errors = {}

    # --- Teks wajib -------------------------------------------------------
    required_text = [("title", "Judul"), ("subject", "Mata kuliah")]
    for field, label in required_text:
        value = clean_text(data.get(field))
        if not value:
            errors[field] = f"{label} wajib diisi."
        elif len(value) > MAX_TEXT_LENGTH:
            errors[field] = f"{label} maksimal {MAX_TEXT_LENGTH} karakter."

    if len(clean_text(data.get("topic"))) > MAX_TEXT_LENGTH:
        errors["topic"] = f"Topik maksimal {MAX_TEXT_LENGTH} karakter."

    # --- Mode -------------------------------------------------------------
    mode = clean_text(data.get("mode")).upper()
    if mode not in VALID_MODES:
        errors["mode"] = "Pilih mode Online atau Offline."

    # --- Waktu ------------------------------------------------------------
    start = _parse_datetime(data.get("starts_at"))
    end = _parse_datetime(data.get("ends_at"))
    if start is None:
        errors["starts_at"] = "Waktu mulai wajib diisi dengan format yang benar."
    elif start < now:
        errors["starts_at"] = "Waktu mulai tidak boleh di masa lalu."
    if end is None:
        errors["ends_at"] = "Waktu selesai wajib diisi dengan format yang benar."
    elif start is not None and end <= start:
        errors["ends_at"] = "Waktu selesai harus setelah waktu mulai."

    # --- Kapasitas --------------------------------------------------------
    try:
        capacity = int(clean_text(data.get("capacity")))
    except ValueError:
        errors["capacity"] = "Kapasitas harus berupa angka bulat."
    else:
        # Blok else berjalan hanya jika try tidak menimbulkan error.
        if capacity < MIN_CAPACITY or capacity > MAX_CAPACITY:
            errors["capacity"] = (
                f"Kapasitas harus antara {MIN_CAPACITY} dan {MAX_CAPACITY} orang (termasuk host)."
            )

    # --- Aturan khusus tiap mode -----------------------------------------
    if mode == MODE_OFFLINE:
        if not clean_text(data.get("location_text")):
            errors["location_text"] = "Lokasi wajib diisi untuk sesi offline."
        map_url = clean_text(data.get("map_url"))
        if map_url and not is_valid_http_url(map_url):
            errors["map_url"] = "Link peta harus diawali http:// atau https://."
    elif mode == MODE_ONLINE:
        if not is_valid_http_url(data.get("meeting_url")):
            errors["meeting_url"] = "Link meeting wajib diisi dan diawali http:// atau https://."

    return errors


def validate_session(data, now=None):
    """Versi daftar dari validate_session_fields: mengembalikan list pesan error."""
    return list(validate_session_fields(data, now).values())
