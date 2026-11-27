# Bugs, kendala, dan batas interpretasi

| ID | Jenis / tingkat | Temuan | Tindakan berikutnya |
| --- | --- | --- | --- |
| B01 | Ketidaksesuaian kode–komentar / sedang | `substitution_cost(l,r)` dan arah sebaliknya terkena `same_place=0.6` sebelum aturan lateral/getar 0.4; satu tes formula gagal. | Konfirmasi spesifikasi fonetik yang diinginkan, lalu usulkan perbaikan urutan kondisi beserta tes. Tidak diperbaiki pada audit ini. |
| E01 | Dependensi lingkungan / tinggi untuk contoh suara | Piper tidak ready dan fallback espeak tidak tersedia; layanan TTS mengembalikan 503. Delapan tes gagal langsung/tidak langsung. | Sediakan model/engine yang diizinkan, kemudian ulangi tes terkait; jangan mengubah assertion menjadi menerima 503. |
| E02 | Dependensi lingkungan | Whisper tidak mempunyai snapshot bobot valid. | Sediakan bobot lokal yang sah dengan izin; evaluasi ulang Whisper terhadap transkripsi ujaran aktual. |
| E03 | Percobaan awal / teratasi pada run akhir | Koneksi MongoDB awal terputus, menyebabkan HTTP timeout/500. Penyebab proses berhenti tidak dipastikan. | Gunakan mongod/data pengujian terisolasi; run akhir berhasil menjalankan integrasi selain TTS. |
| T01 | Desain tes / sedang | Beberapa tes lama bergantung pada hasil tes TTS/pelafalan sebelumnya. | Pertahankan hasil gagal, tambah fixture mandiri; tiga tes mandiri telah lulus. |
| M01 | Validitas metodologi | Belum ada label temporal VAD, gaze manusia, rating pelafalan, atau label fusion ahli yang independen. | Lakukan anotasi/protokol manual; jangan menyimpulkan akurasi manusia dari fixture sintetis. |
| M02 | Domain | BAHANA Inggris memakai CMUdict; runtime Indonesia memakai hitung vokal. | Laporkan perbedaan dan validasi suku kata Indonesia; jangan menganggap ekuivalen. |
| M03 | Ruang lingkup coverage | Coverage pytest tidak memasukkan server HTTP terpisah dan bukan seluruh frontend/backend. | Gunakan angka sesuai scope. Jangan menyebut 100% basis CFG sebagai 100% coverage kode. |
| M04 | Performa | Satu mesin, n kecil untuk audio, warm sequential, RAM/CPU proses terbatas. | Uji perangkat target dan concurrency sebelum menetapkan SLA. |

Kegagalan harness yang diperbaiki: dependensi coverage awal tidak tersedia; paket uji dipasang hanya di `_test_dependencies`. Akses jaringan sandbox awal ditolak lalu instalasi yang diizinkan berhasil. Satu proses plotting mengalami OpenBLAS allocation error saat beban bersamaan; pekerjaan berikutnya membatasi thread BLAS pada proses pengujian dan menjalankan pekerjaan berat berurutan. Akses paket uji yang dipasang di luar sandbox memerlukan proses uji berizin. Tidak ada alasan ini dipakai untuk mengubah expected output algoritma.

Tidak ada source produksi yang diperbaiki. Model tidak dilatih ulang. Seluruh hasil yang belum memiliki ground truth dipisahkan dari hasil verifikasi implementasi.
