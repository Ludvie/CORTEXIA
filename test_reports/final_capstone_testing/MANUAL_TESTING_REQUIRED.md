# Pengujian manual yang masih diperlukan

| Aktivitas | Status | Isian hasil yang belum tersedia |
| --- | --- | --- |
| Anotasi suara/hening dan batas segmen BAHANA oleh penilai independen | MANUAL REQUIRED | Jumlah audio: ___; penilai: ___; kesepakatan: ___; toleransi: ___ ms; Precision/Recall/F1: ___ |
| Transkripsi manual ujaran aktual untuk benchmark ASR multi-audio | MANUAL REQUIRED | Protokol normalisasi: ___; N ujaran: ___; WER/CER per model: ___ |
| Menyediakan bobot Whisper lokal (tanpa unduhan otomatis) | BLOCKED | Versi/checksum: ___; tanggal pemasangan: ___ |
| Memulihkan engine TTS/Piper lokal | BLOCKED | Engine/checksum: ___; hasil delapan tes setelah pemulihan: ___ |
| Validasi webcam terhadap titik referensi/eye tracker independen | MANUAL REQUIRED | Peserta anonim: ___; perangkat: ___; galat/presisi: ___; variasi viewport/cahaya/kacamata: ___ |
| Penilaian pelafalan oleh manusia | MANUAL REQUIRED | Rubrik: ___; N kata: ___; reliabilitas antarpenilai: ___; korelasi/kesesuaian: ___ |
| Evaluasi fusion terhadap anotasi pendamping/ahli pada sesi audio–gaze berpasangan | MANUAL REQUIRED | Target: ___; data uji terpisah: ___; eye-only/speech-only/fusion: ___ |
| Usability orang tua/guru/anak; SUS jika sesuai protokol | MANUAL REQUIRED | N responden: ___; persetujuan: ___; skor/temuan: ___ |
| Sesi nyata dari login, consent, kalibrasi, membaca, Results, review sampai PDF | MANUAL REQUIRED | Browser/perangkat: ___; hasil: ___; masalah: ___ |

Jangan mengisi kolom kosong dengan prediksi algoritma. Jangan memakai teks stimulus sebagai transkripsi manusia tanpa pemeriksaan ujaran. Template VAD tersedia di `02_vad/manual_validation_template.csv`. Browser harness hanya memakai data sintetis dan bukan studi pengguna.
