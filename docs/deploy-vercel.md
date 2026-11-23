# Deploy ke Vercel + Neon Postgres

Panduan ini membuat RuangBareng bisa dibuka dari internet di alamat `https://<nama-proyek>.vercel.app`.

## Kenapa butuh Neon?

Vercel menjalankan Python sebagai *serverless function*. Disknya hanya bisa dibaca, dan tiap instance server punya folder sementara sendiri. File SQLite di sana akan hilang dan tidak sama antar-instance. Karena itu, di Vercel aplikasi memakai **Postgres dari Neon** (gratis). Di laptop dan saat test, aplikasi tetap memakai SQLite.

Aplikasi memilih database secara otomatis:

| Kondisi | Database yang dipakai |
|---|---|
| `DATABASE_URL` diisi (`postgresql://...`) | Postgres |
| `DATABASE_URL` kosong | SQLite di `instance/ruangbareng.db` |

## Langkah 1 — Push kode ke GitHub

```powershell
git push -u origin feat/mvp
```

Kalau kelompok sudah menggabungkan branch ini ke `main`, Vercel bisa langsung memakai `main`.

## Langkah 2 — Buat proyek di Vercel

1. Login ke <https://vercel.com> memakai akun GitHub.
2. Klik **Add New… → Project**, lalu pilih repo `ddp1-ruang-bareng` dan klik **Import**.
3. **Framework Preset:** pilih **Other**. Build command dan output directory dibiarkan kosong.
4. Jangan klik Deploy dulu. Database perlu disiapkan lebih dulu (langkah 3).

## Langkah 3 — Hubungkan database Neon

1. Di halaman proyek Vercel, buka tab **Storage**, klik **Create Database**, pilih **Neon (Serverless Postgres)**, lalu pilih region **Singapore** (paling dekat dengan Indonesia).
2. Hubungkan database ke proyek ini untuk environment **Production** dan **Preview**.
3. Vercel otomatis menambahkan variabel `DATABASE_URL` (dan beberapa variabel `POSTGRES_*`). Aplikasi membaca `DATABASE_URL`, atau `POSTGRES_URL` kalau yang pertama tidak ada.

## Langkah 4 — Isi `SECRET_KEY`

1. Buat nilai acak di laptop:
   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. Di Vercel, buka **Settings → Environment Variables**, lalu tambahkan `SECRET_KEY` dengan nilai tadi untuk Production dan Preview.

Jangan tulis nilai ini di kode, di README, atau di chat kelompok. Kalau `SECRET_KEY` atau `DATABASE_URL` belum diisi, aplikasi sengaja menolak menyala dan menampilkan pesan error di log Vercel.

## Langkah 5 — Deploy

Buka tab **Deployments**, lalu klik **Deploy** (atau **Redeploy**). Setelah selesai, buka alamat `*.vercel.app` yang diberikan. Tabel database dibuat otomatis saat aplikasi pertama kali menyala.

## Langkah 6 — Isi akun demo

Akun demo dibuat dari laptop, langsung ke database Neon:

1. Di Vercel: **Storage → (database) → .env.local**, lalu salin nilai `DATABASE_URL`.
2. Di laptop, dari folder proyek:
   ```powershell
   .venv\Scripts\activate
   pip install -r requirements.txt
   $env:DATABASE_URL = "<tempel DATABASE_URL di sini>"
   python scripts/seed_demo.py
   Remove-Item Env:DATABASE_URL
   ```
3. Muat ulang website, lalu klik **Masuk (akun demo)**.

Baris `Remove-Item` penting. Tanpa itu, perintah lain di terminal yang sama akan ikut menulis ke database produksi.

## Memperbarui website

Setiap push ke branch yang dihubungkan (biasanya `main`) otomatis membuat deployment baru. Branch lain mendapat URL *preview* sendiri.

## Kalau ada masalah

| Gejala | Penyebab umum |
|---|---|
| Halaman error 500, dan log berisi `SECRET_KEY belum diisi` | Langkah 4 belum dilakukan, atau belum di-redeploy setelah variabel ditambahkan. |
| Log berisi `DATABASE_URL ... belum diisi` | Langkah 3 belum dilakukan untuk environment tersebut. |
| Halaman login bilang "Belum ada akun demo" | Langkah 6 belum dijalankan. |
| Tampilan tanpa CSS | Cek `vercel.json` masih ada dan berisi `includeFiles: app/**`. |

Log bisa dilihat di Vercel: **Deployments → (deployment) → Functions/Logs**.

## Menguji kode Postgres di laptop

Test khusus Postgres ada di `tests/test_postgres.py` dan akan dilewati (skip) kecuali `TEST_DATABASE_URL` diisi. Test ini **menghapus semua tabel**, jadi arahkan ke database uji, jangan ke database Neon yang dipakai website.

```powershell
$env:TEST_DATABASE_URL = "postgresql://user:pass@localhost:5432/ruangbareng_test"
python -m unittest tests.test_postgres -v
```
