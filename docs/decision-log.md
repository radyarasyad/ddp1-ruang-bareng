# Decision log

| ID | Tanggal | Keputusan | Opsi yang dipertimbangkan | Alasan | Penanggung jawab |
|---|---|---|---|---|---|
| D-01 | 2026-11-23 | Kapasitas menghitung host. Rentang 2–20. | Host dihitung / tidak dihitung | Default blueprint §11.3; lebih jujur soal jumlah orang di ruangan. | ___ |
| D-02 | 2026-11-23 | Status FULL dihitung otomatis, tidak disimpan. | Simpan FULL / hitung otomatis | Satu sumber kebenaran; tidak ada status yang bertentangan dengan jumlah peserta. | ___ |
| D-03 | 2026-11-23 | Rejoin mengaktifkan ulang baris enrollment lama. | Insert baru / hapus baris / aktifkan ulang | `UNIQUE(session_id, user_id)` menolak baris kedua; riwayat tetap ada. | ___ |
| D-04 | 2026-11-23 | Join dan leave memakai transaksi `BEGIN IMMEDIATE`. | Cek di frontend / transaksi biasa / BEGIN IMMEDIATE | Mencegah dua join bersamaan mengisi slot terakhir (T-15). | ___ |
| D-05 | 2026-11-23 | Login MVP memakai akun demo lokal. | SSO UI / akun demo | SSO butuh izin resmi (blueprint §12). | ___ |
| D-06 | 2026-11-23 | Waktu disimpan sebagai teks ISO lokal (WIB). | Timestamp UTC / teks ISO lokal | Sederhana dan bisa dibandingkan dengan `datetime.fromisoformat`. | ___ |
| D-07 | 2026-11-23 | `create_session` mengembalikan error sebagai dict `{field: pesan}`; `validate_session` tetap tersedia sebagai list. | List pesan / dict per field | UI perlu menampilkan pesan tepat di bawah input yang salah. | ___ |
| D-08 | 2026-11-23 | Link meeting sesi online hanya terlihat oleh host dan peserta. | Publik / setelah join | Blueprint §8.5: hindari menyebar link privat. | ___ |
| D-09 | 2026-11-23 | Font judul Bricolage Grotesque via Google Fonts, bukan Cabinet Grotesk. | Cabinet Grotesk (self-host) / Bricolage | Cabinet Grotesk tidak ada di Google Fonts; fallback yang disepakati di draf issue #8. | ___ |
| D-10 | 2026-11-23 | Deploy di Vercel memakai Neon Postgres; laptop dan test tetap SQLite. Storage memilih otomatis dari `DATABASE_URL`. | PythonAnywhere + SQLite / Vercel + SQLite di /tmp / Vercel + Postgres | SQLite di serverless tidak persisten dan tidak konsisten antar-instance (blueprint §10.1). Mengubah aturan awal "SQLite untuk MVP" untuk lingkungan produksi saja. | ___ |
| D-11 | 2026-11-23 | Di Postgres, transaksi join/leave memakai `pg_advisory_xact_lock` sebagai pengganti `BEGIN IMMEDIATE`. | SELECT ... FOR UPDATE / SERIALIZABLE + retry / advisory lock | Perilakunya sama dengan SQLite (satu penulis pada satu waktu), tanpa logika retry. | ___ |
| D-12 | 2026-11-23 | "Sekarang" selalu dihitung dalam WIB (`now_wib()`), bukan jam server. | `datetime.now()` / WIB tetap | Server Vercel memakai UTC; tanpa ini validasi waktu dan status Selesai meleset 7 jam. | ___ |
