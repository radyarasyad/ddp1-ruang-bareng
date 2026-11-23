"""Pintu masuk untuk Vercel.

Vercel menjalankan file di folder api/ sebagai serverless function dan
mencari variabel bernama `app` (aplikasi WSGI, dalam hal ini Flask).
Semua logika tetap di folder app/; file ini hanya menyambungkan.
"""

import os
import sys

# Supaya paket "app" di root proyek bisa di-import dari dalam folder api/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.web import create_app  # noqa: E402

app = create_app()
