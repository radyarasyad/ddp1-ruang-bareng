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

# Vercel otomatis mengisi variabel VERCEL=1 di servernya.
IS_VERCEL = bool(os.environ.get("VERCEL"))

# Kunci untuk menandatangani cookie login. Nilai default hanya untuk laptop sendiri.
DEV_SECRET_KEY = "dev-only-ganti-sebelum-deploy"
SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET_KEY)

# Lokasi file SQLite untuk laptop. Path relatif dihitung dari root proyek.
_db_path = os.environ.get("DATABASE_PATH", os.path.join("instance", "ruangbareng.db"))
DATABASE_PATH = _db_path if os.path.isabs(_db_path) else os.path.join(BASE_DIR, _db_path)

# Alamat Postgres untuk deploy (Neon). Integrasi Neon di Vercel mengisi DATABASE_URL;
# beberapa template memakai nama POSTGRES_URL, jadi keduanya diterima.
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""

# Yang benar-benar dipakai aplikasi: Postgres jika ada, kalau tidak SQLite.
DATABASE_TARGET = DATABASE_URL or DATABASE_PATH
