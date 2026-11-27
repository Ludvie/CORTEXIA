# Pengujian Nonfungsional

## Performance

| operation | n | mean_ms | median_ms | p95_ms |
| --- | --- | --- | --- | --- |
| Vosk-ID_warm_recognition | 5 | 396.73900000052527 | 379.34990000212565 | 470.31902000017 |
| gaze_analysis_240_points | 30 | 3.3912599998681494 | 3.2033000024966896 | 4.516029993828851 |
| rule_fusion | 100 | 0.07747999930870719 | 0.07234999793581665 | 0.11138000263599677 |
| audio_decode_asr_vad_fluency | 5 | 329.1389199963305 | 311.51289999252185 | 387.9459399933694 |
| inprocess_session_excluding_http_database | 5 | 648.9460799988592 | 626.0928999981843 | 796.3575799978571 |
| HTTP upload + decode + ASR + VAD + gaze + fusion + MongoDB save | 5 | 581.5215400012676 | 593.6193999950774 | 625.6924800080014 |


Percobaan hangat dilakukan berurutan: Vosk/audio/session 5 kali, gaze 30 kali, fusion 100 kali. End-to-end HTTP mencakup upload fixture publik yang diulang menjadi 7,427 s, decode, ASR, VAD, analisis gaze, fusion, dan penyimpanan pada MongoDB khusus pengujian; bukan uji beban banyak pengguna. Median HTTP 593.62 ms dan p95 625.69 ms. Endpoint end-to-end memakai fixture berbeda durasi dari benchmark audio 3,7135 s sehingga tidak boleh dibandingkan langsung sebagai overhead murni.

Spesifikasi perangkat berada di `device.json`. CPU dilaporkan sebagai waktu CPU proses, bukan persentase utilisasi sistem. Nilai 0 ms untuk operasi sangat pendek dapat berasal dari resolusi penghitung CPU Windows. RSS disampling setiap 20 ms dan bukan peak absolut atau alokasi khusus model. Mesin memiliki RAM terbatas; hasil adalah satu run lokal, bukan jaminan SLA produksi.

## Security dan isolasi

28 pemeriksaan terpilih tersedia pada `security_test_results.csv`. Pengujian source-directed memeriksa guard autentikasi, role guru/siswa, filter owner pada sesi/materi/peserta dan PDF/review, consent, input invalid, upload 25 MB+1, audio rusak, dan unlink file temporer pada jalur berhasil/gagal. Database dan server berjalan pada loopback khusus tes. Ini bukan penetration test komprehensif.

## Usability teknis

89 pemeriksaan browser lulus dan 16 frontend unit tests lulus. Empat viewport (1920,1366,768,390), tab keyboard, keterbacaan, kontras teks terlihat, empty/error/partial states, review/PDF routing, dan role siswa diuji. Source manifest cocok dengan build yang diperiksa. Tidak ada data peserta atau kamera/mikrofon manusia pada browser harness. Pemeriksaan ini adalah verifikasi teknis pendukung, **bukan subbab Black-Box Testing**, sertifikasi WCAG penuh, SUS, atau penelitian kepuasan pengguna.
