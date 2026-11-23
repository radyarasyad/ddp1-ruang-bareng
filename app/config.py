"""Konfigurasi aplikasi yang dibaca dari variabel lingkungan (environment variable).

Nilai rahasia seperti SECRET_KEY tidak boleh ditulis langsung di kode,
karena kode ini publik di GitHub. Isi lewat file .env atau terminal.
"""

import os

# Folder root proyek (satu tingkat di atas folder app/).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv(path):
    """Membaca file .env sederhana (baris KUNCI=nilai) tanpa library tambahan."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            # Lewati baris kosong, komentar, dan baris tanpa tanda '='.
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            # setdefault: variabel yang sudah diset di terminal tetap menang.
            if value.strip():
                os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(os.path.join(BASE_DIR, ".env"))

# Kunci untuk menandatangani cookie login. Nilai default hanya untuk laptop sendiri.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-ganti-sebelum-deploy")

# Lokasi file database. Path relatif dihitung dari root proyek.
_db_path = os.environ.get("DATABASE_PATH", os.path.join("instance", "ruangbareng.db"))
DATABASE_PATH = _db_path if os.path.isabs(_db_path) else os.path.join(BASE_DIR, _db_path)
