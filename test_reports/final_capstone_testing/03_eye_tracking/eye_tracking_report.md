# Eye Tracking dan I-DT

Empat puluh kasus terkontrol lulus; pengujian yang sudah tersedia pada pytest memberikan dukungan tambahan. Source utama: backend/analytics.py:160–174 (_idt), backend/analytics.py:222–304 (gaze_metrics). Parameter: dispersi (max x−min x)+(max y−min y) ≤80 px, minimum 120 ms, gap antar-sampel ≤0,5 s. Koordinat area teks dinormalisasi lalu dikonversi menggunakan ukuran layout yang aktif.

Kalibrasi frontend (`frontend/src/components/Calibration.jsx:15–20`) menggunakan lima titik inti dan titik validasi terpisah, batas median error 0,16 dan minimal 15 sampel. Backend juga memerlukan flag passed=True. `frontend/src/pages/Reading.jsx:29` membatalkan validitas kalibrasi pada resize. WebGazer dan MediaPipe berasal dari loader lokal di `frontend/src/lib/media.js`; hasil uji ini tidak mengukur galat webcam manusia.

Uji mencakup koordinat NaN, waktu negatif/duplikat/di luar durasi, cakupan 30%, 19/20 sampel, 119/120 ms, dispersi 80/81 px, gap 500/501 ms, pemetaan kata terdekat, progression, regression, revisit, skipped words. Fixture lintasan kata [0,2,0] menghasilkan satu progression, satu regression dalam baris, satu kata dikunjungi ulang, dan skipped words 33,3%. Jitter relatif 0,05 menghasilkan satu fiksasi pada lebar 800 px dan nol pada 2000 px; ambang piksel membuat hasil sensitif pada ukuran tampilan.

`idt_test_cases.csv` dan `eye_tracking_metrics.csv` menyimpan input/expected/actual. Grafik fiksasi dan pemetaan adalah **sintetis**, bukan eye-tracker ground truth. Pengujian manusia, variasi pencahayaan, posisi kepala, kacamata, dan validasi terhadap alat referensi tetap MANUAL REQUIRED.
