# Pronunciation Scoring

Hasil: 24 PASSED, 1 FAILED pada kasus terkontrol. Source: backend/pronunciation.py:218–272 (assess), backend/pronunciation.py:173–182 (phonetic_distance), backend/pronunciation.py:150–170 (substitution_cost).

Similarity aktual memakai `SequenceMatcher` atas ejaan tanpa spasi, bukan normalized Levenshtein. Jika forced-choice tersedia, skor = 0,35×similarity + 0,65×confidence target; komponen confidence bernilai nol bila pesaing menang. Jika target OOV/tidak ada pesaing, hanya similarity dipakai. Tanpa ucapan, skor null. Kategori tepat ≥85, hampir ≥60 dan <85, latihan <60; nama kode kategori terakhir adalah `latihan`, bukan `belum_tepat`.

Weighted phonetic distance adalah Levenshtein dengan biaya sisip/hapus 1 dan biaya substitusi dari fitur fonetik. Jarak ini digunakan untuk memilih pesaing, bukan langsung sebagai komponen formula skor 35/65. Kasus target `apel` yang cocok dan confidence 80% menghasilkan 87. Pesaing dengan similarity 75% menghasilkan 26,2. Perhitungan ini dihitung independen pada fixture dekoder terkontrol.

| case_id | expected | actual | status |
| --- | --- | --- | --- |
| cost_lr | 0.4 | 0.6 | FAILED |


Temuan: komentar aturan cair l/r mengharapkan 0,4, tetapi kondisi `same_place` dievaluasi lebih dahulu dan menghasilkan 0,6 karena keduanya alveolar. Tes khusus memakai nilai yang dinyatakan komentar sebagai expected; ini ketidaksesuaian dokumentasi/intensi dengan prioritas cabang, bukan bukti bahwa 0,4 telah tervalidasi secara fonetik. Cabang 0,4 untuk pasangan l/r tidak tercapai. Tidak dilakukan perbaikan source otomatis.

Confidence per kata pada sesi membaca hanya berasal dari dekode bebas Vosk dan mempunyai cakupan kata cocok. Nilai tersebut berbeda dari skor latihan forced-choice. Tidak tersedia anotasi penilai manusia; kesesuaian skor terhadap pelafalan manusia adalah MANUAL REQUIRED. Grafik skor menampilkan fixture terkontrol, bukan validasi klinis.
