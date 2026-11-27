# FINAL CAPSTONE TEST REPORT — CORTEXIA

Source yang diaudit adalah workspace terbaru, termasuk perubahan belum di-commit, HEAD `1074c7d8ed80db550c495483c5e2cbdc065f164d`. Source aplikasi dan artefak produksi terlindungi tidak berubah selama pekerjaan: **True**, 204 file diperiksa SHA-256. Tidak ada training LR/RF/TURead, cleaning ulang dataset, atau perubahan UI/arsitektur/hyperparameter.

## Ringkasan bukti

| area | unit | passed | failed | skipped | blocked | status |
| --- | --- | --- | --- | --- | --- | --- |
| 02_vad | controlled cases | 10 | 0 | 0 | 0 | PASSED |
| 03_eye_tracking | controlled cases | 40 | 0 | 0 | 0 | PASSED |
| 05_pronunciation | controlled cases | 24 | 1 | 0 | 0 | FAILED |
| 06_fluency | controlled cases | 10 | 0 | 0 | 0 | PASSED |
| 07_multimodal_fusion | controlled cases | 118 | 0 | 0 | 0 | PASSED |
| 01_whitebox | independent paths (overlap controlled cases) | 24 | 0 | 0 | 0 | PASSED |
| 02_vad BAHANA sample | existing-audio regression cases | 6 | 0 | 0 | 0 | PASSED |
| 04_speech_recognition | inference/fallback/corrupt scenarios | 4 | 0 | 0 | 1 | BLOCKED |
| 06_fluency BAHANA | aggregate formula checks over existing artifacts | 5 | 0 | 0 | 0 | PASSED |
| 09_integration backend | unique pytest cases, final runs | 128 | 8 | 6 | 0 | FAILED |
| 08_nonfunctional UI browser | technical checks | 89 | 0 | 0 | 0 | PASSED |
| 08_nonfunctional frontend | Jest tests | 16 | 0 | 0 | 0 | PASSED |
| Human validation | ground truth/SUS/live webcam | 0 | 0 | 0 | 0 | MANUAL REQUIRED |
| Whisper vs Vosk accuracy chart | valid comparative experiment | 0 | 0 | 0 | 0 | NOT APPLICABLE |


Unit antarbaris berbeda dan beberapa bukti beririsan; **jangan menjumlahkan seluruh baris sebagai jumlah tes unik**. Keluarga bukti utama: 203 kasus algoritma langsung (202 lulus, 1 gagal); 142 tes pytest backend akhir (128 lulus, 8 gagal, 6 dilewati); 16 tes frontend lulus; 89 pemeriksaan browser lulus. Enam audio BAHANA dan lima audit formula agregat adalah bukti tambahan yang terpisah.

## Temuan utama

- CFG I-DT V=5, klasifikasi quality final V=3, fusion statement-level V=16; basis independen 5/5, 3/3, 16/16 teramati. Batas abstraksi dijelaskan dalam laporan white-box.
- Statement coverage 81.78% dan branch coverage 73.16% pada lima modul yang diinstrumentasi; bukan coverage keseluruhan aplikasi.
- Vosk pada satu fixture publik: WER/CER 0%. Whisper belum tersedia. Tidak ada klaim perbandingan model ASR yang belum dijalankan.
- VAD enam sampel BAHANA konsisten dengan hasil otomatis sebelumnya. Tidak tersedia ground truth temporal independen sehingga Precision/Recall/F1 manusia tidak dihitung.
- Seluruh 10 kasus formula fluency lulus. Lima audit aritmetika artefak BAHANA memiliki nol mismatch pada toleransi 2e-6.
- Satu tes biaya l/r gagal terhadap komentar metode (expected 0,4, actual 0,6). Delapan tes integrasi gagal terkait engine TTS/dependensi antar-tes. Tidak ada perbaikan produksi otomatis.
- Tiga integrasi mandiri lulus: ownership sesi/PDF/review, audio–gaze–fluency–database–review–PDF, dan benchmark HTTP lengkap.

## Hasil penelitian terdahulu yang digunakan kembali

Pipeline dan 211 file sumber ETDD70 masih cocok hash-nya dengan eksperimen lama. Tidak ada alasan material untuk training ulang. ETDD70 adalah eksperimen klasifikasi LR/RF 210 rekaman/70 peserta/16 fitur dengan fold peserta; BAHANA mendukung definisi fluency; TURead mendukung eksperimen regresi eksploratif. Ketiganya tidak dilatih bersama dan tidak menjadi classifier klinis pada sesi webcam.

| model | unit | n | accuracy | precision_macro | recall_macro | macro_f1 | roc_auc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Logistic Regression | recording | 210 | 77.14 | 77.63 | 77.14 | 77.04 | 0.8600 |
| Most frequent | recording | 210 | 50.00 | 25.00 | 50.00 | 33.33 | 0.5000 |
| Random Forest | recording | 210 | 78.10 | 78.11 | 78.10 | 78.09 | 0.8648 |
| Logistic Regression | participant | 70 | 84.29 | 85.00 | 84.29 | 84.21 | 0.9216 |
| Most frequent | participant | 70 | 50.00 | 25.00 | 50.00 | 33.33 | 0.5000 |
| Random Forest | participant | 70 | 81.43 | 81.66 | 81.43 | 81.39 | 0.9290 |


Accuracy/Precision/Recall/F1 dalam persen; AUC dalam [0,1]. RF terbaik per rekaman (Macro F1 78,09%), LR terbaik per peserta (84,21%). Perbedaan kecil pada satu dataset/fold tetap tidak membuktikan superioritas umum.

| model | mae | rmse | r2 |
| --- | --- | --- | --- |
| median_baseline | 14.3615 | 18.2369 | -0.0015 |
| eye_only | 13.4412 | 17.1320 | 0.1162 |
| speech_only | 13.6638 | 17.4066 | 0.0877 |
| multimodal | 13.3309 | 16.9673 | 0.1331 |


TURead memakai 16.087 observasi oral yang dipilih dari 37.416 observasi terolah, 196 peserta, target WPM, 5-fold GroupKFold berdasarkan peserta. Multimodal MAE 13,3309 dibanding eye-only 13,4412 dan speech-only 13,6638; ini eksperimen terpisah, bukan validasi fusi runtime atau klasifikasi disleksia.

## Pemakaian bukti

Laporan per bagian terdapat pada folder 01–09. Folder 10–11 memuat salinan artefak agregat yang relevan beserta provenance. `REPORT_READY_CONTENT.md` adalah bahan BAB IV ringkas; `REPORT_FIGURE_INDEX.md` memilih grafik; `MANUAL_TESTING_REQUIRED.md` menyediakan ruang pengisian. Perintah reproduksi tersedia pada script pengujian di folder ini. Jalankan hanya terhadap lingkungan uji yang ditentukan; script `run_verification.py` memakai mongod sementara dan mempertahankan assertions suite lama.

Belum semua validasi penelitian selesai: anotasi manusia, uji webcam manusia, pemulihan TTS, bobot Whisper, dan studi usability masih diperlukan. ZIP bukti tidak menyertakan audio mentah, dataset baris peserta, model, database, credentials, environment, atau dependensi uji.
