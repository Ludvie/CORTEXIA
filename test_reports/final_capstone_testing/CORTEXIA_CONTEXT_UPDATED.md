# Konteks CORTEXIA setelah pengujian akhir

Tanggal lokal: 2026-11-27T17:30:08.226544+07:00. HEAD: 1074c7d8ed80db550c495483c5e2cbdc065f164d. File ini melengkapi `CORTEXIA_CONTEXT.md` lama tanpa menimpanya. Source belum di-commit ikut diaudit.

Arsitektur: React Results/Reading/Calibration → FastAPI sessions/analytics/pronunciation/fluency → MongoDB. WebGazer/MediaPipe memproses wajah di browser; I-DT dan word mapping di backend. Audio didekode PCM16 mono 16 kHz satu kali, memakai Whisper bila bobot lokal valid, dengan fallback Vosk-ID. WebRTC VAD mode 2 mengisi lima fitur fluency. Fusi memakai aturan per kata, bukan LR/RF untuk inferensi pengguna.

ETDD70: eksperimen LR/RF, 70 peserta/210 rekaman/16 fitur, grouped out-of-fold; hasil lama masih relevan berdasarkan hash. RF unggul Macro F1 per rekaman, LR per peserta. TURead: regresi eksploratif WPM, 16.087 oral/196 peserta; model eksperimen tidak menjadi skor klinis runtime. BAHANA: 140 audio mendukung metodologi fluency Inggris; runtime Indonesia memakai perkiraan suku kata ortografis.

Results terbaru mempertahankan lima fitur, membedakan dua WPM, menjaga fluency ASR asli saat review, dan menampilkan fusion hanya bila kedua modalitas valid. 89 pemeriksaan browser dan 16 frontend tests lulus; data browser sintetis.

Hasil akhir: 203 kasus algoritma (202 lulus, 1 gagal); backend pytest 142 kasus unik (128 lulus, 8 gagal, 6 skipped); statement coverage 81.78% dan branch coverage 73.16% pada lima modul, bukan seluruh aplikasi. CFG basis lengkap pada abstraksi yang dijelaskan laporan white-box.

Bug/limit: komentar biaya l/r 0,4 versus hasil 0,6; TTS/Piper tidak tersedia; Whisper tidak tersedia; validasi manusia belum ada. Vosk WER/CER 0% hanya satu fixture publik. Enam sampel VAD BAHANA cocok artefak lama; bukan akurasi terhadap label manusia. Tiga integrasi mandiri audio/gaze/DB/review/PDF lulus. Tidak ada perubahan aplikasi/model selama audit. Lihat `FINAL_CAPSTONE_TEST_REPORT.md`, `BUGS_AND_LIMITATIONS.md`, `MANUAL_TESTING_REQUIRED.md`, dan `source_catalog.csv` untuk bukti rinci.
