# Bahan BAB IV — Pengujian dan Analisis CORTEXIA

Dokumen ini merupakan naskah ringkas berbasis hasil eksekusi. Alokasi yang disarankan adalah 13–15 halaman BAB IV setelah tata letak kampus diterapkan; jumlah halaman akhir harus diperiksa pada dokumen laporan. Prioritaskan 3 halaman white-box, 2 halaman eksperimen terdahulu, 4–5 halaman pipeline audio/gaze/fusion, 2 halaman nonfungsional/integrasi, dan 1–2 halaman keterbatasan. Tidak ada subbab Black-Box Testing.

## 4.1 Tujuan dan rancangan

Pengujian bertujuan memverifikasi kesesuaian implementasi algoritma, batas input, interaksi antar-modul, serta karakteristik waktu proses. Source terbaru dan perubahan belum di-commit digunakan sebagai acuan. Pengujian dipisahkan menjadi verifikasi terkontrol, regresi terhadap artefak lama, pemeriksaan teknis integrasi/UI, dan validasi manusia yang belum dilaksanakan. Pemisahan tersebut mencegah hasil sintetis ditafsirkan sebagai akurasi asesmen membaca manusia.

Model penelitian tidak dilatih ulang. Kesamaan hash pipeline dan 211 file sumber ETDD70 memastikan hasil terdahulu masih relevan terhadap implementasi penelitian. Pengujian database memakai lingkungan terpisah. Status FAILED tetap dilaporkan meskipun penyebabnya adalah dependensi yang belum tersedia.

## 4.2 White-box dan basis path

Kompleksitas siklomatis dihitung menggunakan V(G)=E−N+2P, dengan P=1. Predicate biner meliputi if/while/for; compound boolean, comprehension dan conditional expression pada CFG fungsi diperlakukan atomik. Diagram quality hanya menyatakan pemilihan kategori akhir, dengan ternary diturunkan menjadi dua keputusan ekuivalen; bukan seluruh fungsi analyze.

| function | nodes | edges | predicate_nodes | cyclomatic_complexity | observed_independent_paths |
| --- | --- | --- | --- | --- | --- |
| _idt | 20 | 23 | 4 | 5 | 5 |
| quality_gate_classification | 9 | 10 | 2 | 3 | 3 |
| fuse | 66 | 80 | 15 | 16 | 16 |


Trace eksekusi dan matriks edge menunjukkan basis 5, 3, dan 16 jalur independen. Expected dan actual setiap jalur tercantum pada `01_whitebox/basis_path_testing.csv`. Kesamaan jumlah basis dengan kompleksitas berlaku pada abstraksi tersebut dan tidak menunjukkan seluruh path loop telah diuji. Statement coverage adalah 817/999=81.78%, sedangkan branch coverage adalah 278/380=73.16%. Coverage server HTTP terpisah tidak termasuk.

Kesimpulan: jalur basis prioritas telah dijalankan, tetapi cabang model yang tidak tersedia serta sejumlah penanganan exception tetap memerlukan verifikasi tambahan. Bukti: laporan, CFG Mermaid/PNG, source bernomor, JUnit, dan coverage pada folder 01.

## 4.3 Perbandingan LR–RF dan eksperimen TURead yang sudah tersedia

| model | unit | accuracy | precision_macro | recall_macro | macro_f1 | roc_auc |
| --- | --- | --- | --- | --- | --- | --- |
| Logistic Regression | recording | 77.14 | 77.63 | 77.14 | 77.04 | 0.8600 |
| Most frequent | recording | 50.00 | 25.00 | 50.00 | 33.33 | 0.5000 |
| Random Forest | recording | 78.10 | 78.11 | 78.10 | 78.09 | 0.8648 |
| Logistic Regression | participant | 84.29 | 85.00 | 84.29 | 84.21 | 0.9216 |
| Most frequent | participant | 50.00 | 25.00 | 50.00 | 33.33 | 0.5000 |
| Random Forest | participant | 81.43 | 81.66 | 81.43 | 81.39 | 0.9290 |


Evaluasi ETDD70 menggunakan prediksi out-of-fold dengan pembagian peserta yang sama, 210 rekaman dan 70 peserta. Angka persentase pada tabel berbeda unit dari AUC. Random Forest memberikan Macro F1 per rekaman 78,09%, lebih tinggi dari LR 77,04%. Setelah probabilitas OOF diagregasi per peserta, LR mencapai Macro F1 84,21% dan RF 81,39%. Pemilihan model bergantung unit evaluasi; tidak dilakukan klaim signifikansi atau generalisasi ke webcam Indonesia.

| model | mae | rmse | r2 |
| --- | --- | --- | --- |
| median_baseline | 14.3615 | 18.2369 | -0.0015 |
| eye_only | 13.4412 | 17.1320 | 0.1162 |
| speech_only | 13.6638 | 17.4066 | 0.0877 |
| multimodal | 13.3309 | 16.9673 | 0.1331 |


TURead mengevaluasi prediksi WPM menggunakan 16.087 observasi oral dari 196 peserta. MAE multimodal 13,3309 sedikit lebih rendah dari eye-only dan speech-only. Hasil ini bersifat eksploratif dan tidak membuktikan peningkatan akurasi diagnosis atau aturan fusi CORTEXIA. Bukti: folder 10 dan 11, digunakan kembali tanpa training.

## 4.4 Eye tracking dan I-DT

I-DT menggunakan dispersi maksimum 80 px, durasi minimum 120 ms, dan gap maksimum 500 ms. Empat puluh kasus terkontrol lulus, termasuk data kosong, NaN, duplikat, batas dispersi/durasi, pemetaan kata, regresi, revisit, skipped words dan cakupan. Pada lintasan sintetis [0,2,0], actual menunjukkan satu progression, satu regression, satu revisited word, dan 33,3% kata tidak tertatap.

Pengubahan lebar viewport dari 800 menjadi 2000 px dengan jitter relatif sama mengubah hasil deteksi dari satu menjadi nol fiksasi. Hasil tersebut konsisten dengan ambang dispersi dalam satuan piksel. Frontend membatalkan kalibrasi pada resize. Kesimpulan terbatas pada kebenaran pemrosesan data sintetis; galat webcam terhadap tatapan manusia belum diukur. Bukti: folder 03. Isian validasi manusia: jumlah peserta ___, galat ___, protokol referensi ___.

## 4.5 VAD dan speech recognition

VAD memakai mode 2, PCM16 mono 16 kHz, frame 20 ms, gap fill 100 ms, segmen minimum 60 ms, pause 250 ms, dan long pause 500 ms. Sepuluh pemeriksaan terkontrol lulus. Enam sampel BAHANA yang sudah diproses sebelumnya diuji ulang sebagai sampel regresi runtime; seluruh durasi aktif cocok dengan artefak lama. Grafik waveform menampilkan prediksi VAD, bukan anotasi ground truth. Precision, Recall, F1 dan boundary error belum dihitung karena anotasi temporal independen belum tersedia.

WER dihitung sebagai (S+D+I)/N. Pada satu rekaman publik 3,7135 s dengan referensi ujaran dari README, Vosk menghasilkan WER=0%, CER=0%, serta S=D=I=0. Timestamp terurut dan berada dalam rentang audio. Hasil tidak mewakili populasi atau keseluruhan BAHANA. Teks stimulus BAHANA tidak dipakai sebagai ground truth ASR. Whisper diblokir oleh ketiadaan bobot lokal; perbandingan akurasi dua model tidak dilakukan. Jalur fallback ke Vosk dan penolakan audio rusak berhasil diuji. Bukti: folder 02 dan 04.

## 4.6 Pronunciation scoring dan fluency

Skor latihan menggabungkan 35% similarity ejaan dan 65% confidence target pada forced-choice. Bila pesaing menang, komponen confidence target bernilai nol. Tanpa forced-choice skor hanya memakai similarity; tanpa ucapan skor null. Weighted phonetic distance menentukan kandidat pesaing, bukan langsung mengisi formula skor. Dari 25 kasus, 24 lulus dan satu gagal: biaya l/r aktual 0,6 tidak sesuai komentar 0,4 karena urutan cabang. Temuan tidak diperbaiki otomatis; keputusan metodologis diperlukan sebelum perubahan produksi.

Lima fitur fluency dihitung sebagai WPM=60W/U, AR=S/A, MLR=S/(J+1), PF=60J/U, dan MPD=D/J untuk J>0. Sepuluh kasus terkontrol lulus. Contoh dua kata, empat suku kata, U=1,5 s, A=1 s, J=1, D=0,5 s menghasilkan WPM 80, AR 4, MLR 2, PF 40, MPD 0,5. WPM rekaman dengan durasi 3 s adalah 40, sehingga kedua WPM tidak dapat dipertukarkan.

| metric | checked | mismatches | tolerance |
| --- | --- | --- | --- |
| wpm | 139 | 0 | 2e-06 |
| articulation_rate_syllables_per_sec | 122 | 0 | 2e-06 |
| mlr_syllables_per_run | 122 | 0 | 2e-06 |
| pause_frequency_per_min | 140 | 0 | 2e-06 |
| mean_pause_duration_sec | 43 | 0 | 2e-06 |


Audit artefak BAHANA mengonfirmasi konsistensi aritmetika pada metrik yang tersedia. CMUdict Inggris dan proxy vokal ortografis Indonesia merupakan metode suku kata berbeda. Mean pause null berarti tidak terdefinisi/tidak tersedia, bukan selalu nol. Kesimpulan: formula terimplementasi konsisten pada fixture, tetapi validitas linguistik terhadap ujaran manusia masih memerlukan anotasi. Bukti: folder 05 dan 06.

## 4.7 Quality gate dan multimodal fusion

Fusion observasional memakai irisan kata salah menurut alignment dan kata yang lama ditatap/dikunjungi ulang. Concordance=100×jumlah kata bersama/jumlah kata salah suara. Sebanyak 118 skenario terkontrol lulus. Batas 39,9%, 40%, dan 40,1% menghasilkan status concordant False, True, True. Ketika satu modalitas tidak layak, sistem tidak menyimpulkan pola gabungan; pembagi nol menghasilkan null. WER>20% dan WPM<60 merupakan aturan awal, bukan norma usia.

Hasil menunjukkan kesesuaian perilaku aturan, bukan peningkatan akurasi asesmen. ETDD70, BAHANA, dan TURead mempunyai peran berbeda dan tidak digabung sebagai dataset supervised multimodal palsu. Bukti: folder 07. Isian validasi ahli berpasangan: target ___, N sesi ___, hasil unimodal/fusion ___.

## 4.8 Nonfungsional dan integrasi

| operation | n | mean_ms | median_ms | p95_ms |
| --- | --- | --- | --- | --- |
| Vosk-ID_warm_recognition | 5 | 396.73900000052527 | 379.34990000212565 | 470.31902000017 |
| gaze_analysis_240_points | 30 | 3.3912599998681494 | 3.2033000024966896 | 4.516029993828851 |
| rule_fusion | 100 | 0.07747999930870719 | 0.07234999793581665 | 0.11138000263599677 |
| audio_decode_asr_vad_fluency | 5 | 329.1389199963305 | 311.51289999252185 | 387.9459399933694 |
| inprocess_session_excluding_http_database | 5 | 648.9460799988592 | 626.0928999981843 | 796.3575799978571 |
| HTTP upload + decode + ASR + VAD + gaze + fusion + MongoDB save | 5 | 581.5215400012676 | 593.6193999950774 | 625.6924800080014 |


Performa diukur pada mesin lokal dengan percobaan berurutan, bukan uji beban. CPU dan RSS merupakan statistik proses dengan keterbatasan resolusi dan sampling. Pemeriksaan keamanan menguji autentikasi, role, ownership, consent, input, upload maksimum dan pembersihan berkas sementara. Pemeriksaan UI menghasilkan 89 checks dan 16 unit tests lulus pada empat viewport, tanpa menyatakan kepuasan pengguna.

Suite backend akhir mencatat 128 lulus, 8 gagal, dan 6 dilewati dari 142 tes. Kegagalan terkait TTS yang tidak tersedia serta dependensi antar-tes tetap dipertahankan. Tiga tes integrasi mandiri berhasil memverifikasi alur audio–gaze–database–review–PDF dan isolasi sesi lintas pengguna. Bukti: folder 08–09. Isian studi usability: responden ___, instrumen ___, hasil ___.

## 4.9 Batas kesimpulan

CORTEXIA telah memperoleh bukti verifikasi algoritma dan integrasi pada skenario yang diuji. Sistem belum dapat dinyatakan tervalidasi secara klinis atau bebas kesalahan. Kendala yang tersisa adalah ketidaksesuaian biaya fonetik l/r, TTS lokal tidak tersedia, Whisper belum tersedia, serta kebutuhan ground truth manusia untuk VAD, gaze, pelafalan, dan fusion. Pengujian manusia dan uji perangkat target harus diselesaikan sebelum klaim akurasi atau usability diperluas.
