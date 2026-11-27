# Pengujian VAD

Source: backend/fluency.py:23–39 (segments) dan backend/fluency.py:46–99 (measure). Konfigurasi aktual: WebRTC mode 2, mono PCM16 little endian, 16.000 Hz, frame 20 ms/640 byte, gap fill ≤100 ms, minimum segmen 60 ms, pause internal ≥250 ms dan long pause ≥500 ms. Objek VAD baru dibuat setiap pemanggilan. Frame akhir yang tidak lengkap tidak diklasifikasi.

Sepuluh pengujian terkontrol lulus. Mask keputusan VAD yang diketahui dipakai khusus untuk memverifikasi smoothing, batas durasi, frame rate, dan reset objek; ini bukan evaluasi classifier akustik. Silence digital dan noise diuji menggunakan WebRTC sebenarnya. Noise tidak otomatis dianggap silence/ucapan benar karena tidak mempunyai anotasi independen.

Audio BAHANA tidak ada di dalam ZIP, tetapi seluruh 140 path audio preprocessing pada CSV tersedia lokal. Enam audio dipilih deterministik: durasi minimum, median, maksimum dari strata QC PASS dan REVIEW yang sudah tersedia. Tidak dilakukan resampling, cleaning, training, atau pengolahan ulang keseluruhan dataset. Keenam file telah 16 kHz mono PCM16.

| case_id | existing_qc | duration_sec | active_sec | prior_active_sec | active_delta_sec | segments | pauses | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BAHANA_SAMPLE_1 | PASS | 1.8 | 1.5 | 1.5 | 0.0 | 2 | 1 | PASSED |
| BAHANA_SAMPLE_2 | PASS | 3.66 | 2.86 | 2.86 | 0.0 | 2 | 0 | PASSED |
| BAHANA_SAMPLE_3 | PASS | 8.94 | 7.780000000000001 | 7.78 | 8.881784197001252e-16 | 6 | 1 | PASSED |
| BAHANA_SAMPLE_4 | REVIEW | 0.78 | 0.36000000000000004 | 0.36 | 5.551115123125783e-17 | 2 | 1 | PASSED |
| BAHANA_SAMPLE_5 | REVIEW | 3.36 | 2.56 | 2.56 | 0.0 | 2 | 1 | PASSED |
| BAHANA_SAMPLE_6 | REVIEW | 7.56 | 7.02 | 7.02 | 0.0 | 1 | 0 | PASSED |


Enam hasil durasi aktif cocok dengan artefak VAD sebelumnya. Ini uji regresi konsistensi, **bukan akurasi terhadap manusia**. Metadata validasi yang ditemukan memuat `validation_status`, flags, dan speech ratio; segmen bertipe `SMOOTHED_VAD` adalah keluaran algoritma, bukan ground truth. Oleh sebab itu Precision, Recall, F1, dan kesalahan batas terhadap manusia dibiarkan kosong/NOT APPLICABLE.

`vad_waveform.png` memperlihatkan fixture publik dengan hening tambahan; `bahana_vad_waveforms.png` memperlihatkan sampel BAHANA tanpa nama peserta. Arsiran adalah prediksi. Distribusi jeda deskriptif tersedia untuk kedua sumber. Template manual perlu diisi oleh anotator independen dengan toleransi yang disepakati terlebih dahulu, misalnya 20 ms sebagai resolusi frame; jangan menganggap toleransi itu sebagai hasil terukur.
