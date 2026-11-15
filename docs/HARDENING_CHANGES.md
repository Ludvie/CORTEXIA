# CORTEXIA — Catatan Implementasi Hardening

Lanjutan dari `SYSTEM_HARDENING_REPORT.md`. Dikerjakan dalam dua tahap:
- **Tahap 1:** perbaikan P0/P1 di backend.
- **Tahap 2:** catatan frontend, risiko yang bisa ditutup dengan kode, dan P2.

Threshold analisis tidak diubah. Model ETDD70 tidak dihubungkan ke analisis webcam. Tidak ada dependensi runtime baru.
Laporan audit asal: `docs/SYSTEM_HARDENING_REPORT.md`.

## Status akhir

- **116 uji lulus, 0 gagal** (`pytest tests`, `-n 2` dari `pytest.ini`, server lokal 127.0.0.1:8001).
- Baseline sebelum hardening: 35 uji (7 unit + 28 integrasi).
- Build frontend sukses. Halaman Hasil dan Dashboard sudah dicek di browser tanpa error konsol.

## File yang diubah

### Backend
| File | Perubahan |
|---|---|
| `analytics.py` | Validasi PCM dan timestamp ASR; edge case WER; `wer_source`, `reading_error_rate`, `asr_wer`; pembersihan gaze (duplikat, urutan, rentang) dan statistik interval; I-DT 120 ms tanpa toleransi; gate kalibrasi `passed`; ukuran piksel per layout; fusi baru (suara harus andal, WER/WPM terpisah, concordance ≥ 40%); kualitas per modalitas; `profile_reason`; alasan pengecualian suara sesuai penyebab; sanitasi NaN/Infinity; isolasi kegagalan analisis tatapan |
| `sessions.py` | Menyimpan `asr_transcript`/`client_duration`; ASR WER saat koreksi; `client_request_id` + penanganan `DuplicateKeyError`; peringatan saat Vosk gagal |
| `pronunciation.py` | Validasi audio kosong/hening; **pesaing fonetik** (G2P EYD + Levenshtein berbobot fitur artikulasi); pilihan-paksa dilewati tanpa pesaing; confidence dan skor dijepit; `score_method`; `coverage_percent` |
| `server.py` | Unique index parsial `idempotency` (owner_id, client_request_id); indeks `training_jobs`; job terputus ditandai gagal saat startup |
| `research.py` | Status job pelatihan disimpan di MongoDB (`training_jobs`) dengan klaim atomik, bukan lagi dict di memori |
| `content.py` | Rerata ketepatan hanya dari sesi `speech_reliable`; `accuracy_sessions`, `accuracy_sessions_excluded` |
| `ml_pipeline.py` | Precision/recall; **evaluasi per peserta** (`participant_level`); `reproducibility` (versi library, `dataset_sha256`, `model_sha256`, versi fitur, CV) |
| `threshold_validation.py` (baru) | Alat validasi ambang terhadap label ahli (sensitivitas, spesifisitas, Youden, sweep ambang) |
| `requirements-dev.txt` (baru) | pytest, pytest-xdist, requests |

### Frontend
| File | Perubahan |
|---|---|
| `pages/Dashboard.jsx` | Grafik tren hanya memakai sesi dengan `speech_reliable !== false`; teks kosong disesuaikan |
| `pages/Reading.jsx` | Mengirim `client_request_id` (sekali per sesi, dipakai ulang saat retry) |
| `pages/Results.jsx` | Menampilkan `profile_reason`, `analysis_warnings`, sumber WER, galat membaca vs ASR WER, cakupan pelafalan, sampling tatapan aktual; entri glosarium baru |

### Uji dan dokumen
- Uji baru: `test_speech_unit`, `test_gaze_unit`, `test_pronunciation_unit`, `test_fusion_unit`, `test_integration_unit`, `test_real_audio_unit`, `test_threshold_validation_unit`, `test_hardening_integration`.
- `tests/fixtures/bookbot_sample.wav`: rekaman suara nyata Bahasa Indonesia dari bookbot-sr, Apache-2.0, 3,7 detik.
- `memory/PRD.md`: kalibrasi (5 titik inti + titik adaptif + 3 validasi), TTS Piper, I-DT, dan status job diselaraskan dengan kode; bagian Hardening 2026-11 ditambahkan.
- `README.md`: cara menjalankan uji dan alat validasi ambang.

## Hasil ETDD70 (logistic)

| Unit evaluasi | Accuracy | Macro-F1 | Precision macro | Recall macro | Baseline acc / F1 |
|---|---|---|---|---|---|
| Per rekaman (210) | 0,7714 | 0,7704 | 0,7763 | 0,7714 | 0,50 / 0,33 |
| Per peserta (70, rerata probabilitas OOF) | 0,8429 | 0,8421 | 0,8500 | 0,8429 | 0,50 / 0,33 |

Angka per rekaman sama dengan artefak audit, jadi tidak ada regresi.

## Perubahan perilaku yang perlu diketahui

1. `gaze_usable` mensyaratkan `calibration.passed`.
2. Minimum fiksasi 120 ms ditegakkan tanpa toleransi (dulu efektif 72 ms).
3. Kualitas dihitung dari modalitas yang lolos gate. Suara yang cukup panjang tetapi tidak andal, tanpa tatapan layak, kini `tidak_cukup`.
4. Keyakinan ASR yang tidak diketahui dianggap belum andal sampai ditinjau.
5. Suara yang tidak andal tidak masuk fusi atau profil. Ada pola baru untuk "salah ucap + alur visual tidak teratur (belum pada kata yang sama)" dan untuk "bacaan lambat".
6. Pesaing pelafalan kini dipilih secara fonetik, jadi skor pilihan-paksa bisa berbeda dari sebelumnya.
7. Sesi lama tidak dihitung ulang, kecuali transkripnya dikoreksi.

## Risiko yang tidak bisa ditutup dengan kode

- **Validasi threshold:** belum ada data anak Indonesia berlabel ahli di proyek. Alat `threshold_validation.py` siap dipakai. Ambang baru boleh dipertimbangkan untuk diubah bila ada ≥ 30 sesi berlabel per kriteria.
- **Rekaman anak:** yang tersedia hanya 1 rekaman suara nyata (3,7 detik). Whisper dan Vosk sama-sama mendapat WER 0% pada rekaman ini. Satu rekaman belum mewakili variasi ucapan anak, dan klip di bawah 5 detik memang dinilai "terlalu pendek".
- **Pesaing fonetik** memakai aturan G2P dan bobot fitur yang disusun manual. Hasilnya lebih dekat ke bunyi daripada ejaan, tetapi bukan penilaian fonem tervalidasi.
- Idempotensi otomatis hanya untuk klien yang mengirim `client_request_id` (frontend sudah mengirimnya).
