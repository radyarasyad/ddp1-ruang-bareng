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
