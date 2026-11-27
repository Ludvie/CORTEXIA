# Redesign Results CORTEXIA

Tanggal pelaksanaan: 27 November 2026 (Asia/Jakarta).

## Hasil implementasi

Halaman Results sekarang mengutamakan profil sesi, tiga metrik utama, kontribusi suara dan tatapan, kata latihan, kelancaran ujaran, serta langkah latihan. Detail teknis berada dalam accordion dan tab. Warna oranye, navy, lavender, serta font DM Sans/Nunito aplikasi dipertahankan. Oranye tombol digelapkan agar teks putih lebih terbaca.

- Header ringkas: nama peserta, bacaan, tanggal, kualitas, PDF, dan kembali ke dashboard sesuai peran.
- Profil berasal dari backend; uraian singkat memakai `multimodal.signals` yang sudah disediakan backend. Tidak menghitung ulang threshold.
- KPI mempunyai angka besar, satuan, interpretasi singkat, dan penjelasan yang dapat dibuka. Hanya metrik persentase memakai bar; WPM tidak mempunyai progress bar.
- Dua panel modalitas terhubung ke temuan gabungan hanya jika `speech_reliable`, `gaze_usable`, dan `multimodal_complete` semuanya bernilai `true`.
- Kata latihan dikelompokkan menurut alignment suara, daftar tatapan terlama, dan `agreement_words`. Kelompok boleh beririsan. Daftar tatapan terlama **bukan** penghitungan baru kata sulit; UI menjelaskan bahwa tatapan lama belum membuktikan kesulitan.
- Lima fitur fluency ditampilkan dengan satuan API dan definisi dalam expandable detail. `null`, field hilang, NaN, dan Infinity tidak ditampilkan sebagai angka; nol yang valid tetap ditampilkan.
- WPM rekaman (`metrics.wpm`) dibedakan dari WPM rentang ujaran (`metrics.fluency.wpm`). Fluency tetap memakai transkrip ASR asli setelah koreksi manual.
- Rekomendasi berupa kartu dengan tujuan, instruksi backend, dan tindakan menuju fitur yang ada. Langkah tambahan dapat dibuka. Satu CTA utama berada pada ringkasan.
- Tab mendukung ArrowLeft, ArrowRight, Home, End, `aria-selected`, relasi tab/panel, dan fokus yang terlihat. Di mobile tab menjadi dua baris.
- Koreksi transkripsi guru, riwayat koreksi, informasi pelafalan, replay/heatmap, pengamatan per kata, detail sesi, serta glossary tetap tersedia.
- Loading, empty response, API error dengan retry, data lama, audio-only, gaze-only, dan data tidak memadai ditangani.

## File aplikasi

| File | Perubahan |
| --- | --- |
| `frontend/src/pages/Results.jsx` | Refactor halaman, header/profil, request lifecycle, tab aksesibel, integrasi komponen; endpoint PDF dan review tetap sama. |
| `frontend/src/pages/Results.css` | Baru: style khusus Results, responsive grid, typography, kontras dan focus states. |
| `frontend/src/components/results/AssessmentOverview.jsx` | Baru: `MetricCard`, `KeyMetrics`, `ReadingStat`, `MultimodalAnalysis`, `PracticeWords`, `FluencyDetails`, `PracticeCard`, `Recommendations`, `Methodology`. |
| `frontend/src/components/results/ResultsDetails.jsx` | Baru: memindahkan fungsi tab transkripsi, tatapan, dan sesi dari halaman lama; menambah fallback field lama dan memperjelas label keyakinan akustik. |
| `frontend/src/components/results/resultPresentation.js` | Baru: format angka, pemeriksaan flag kualitas API, pemilihan tautan latihan, uraian profil, dan definisi/satuan fluency. |
| `frontend/src/pages/Results.test.jsx` | Baru: 16 pengujian frontend. |

Tidak ada perubahan backend, algoritma, threshold, model, dataset, autentikasi, database, atau format PDF pada pekerjaan ini. Perubahan `scripts/run-backend.cmd` dan folder `test_reports/ml_comparison/` sudah ada sebelum pekerjaan UI ini.

## Hasil verifikasi

| Pemeriksaan | Hasil akhir | Bukti |
| --- | --- | --- |
| Production build | Berhasil, exit 0 | `build.log` |
| Jest frontend | 16 lulus, 0 gagal | `frontend_tests.json` |
| Edge headless, production build | 89 pemeriksaan lulus | `browser_results.json` |
| Ukuran viewport | 1920×1080, 1366×768, 768×1024, 390×844 | Screenshot dan hasil browser |
| Overflow horizontal | Tidak ditemukan pada keempat tab di empat ukuran viewport | Hasil browser |
| Kontras teks terlihat | Tidak ditemukan kegagalan pada teks Results yang diperiksa di seluruh tab | Bagian `contrast` hasil browser |
| Exception JavaScript aplikasi | 0 pada skenario browser yang diuji | `runtime_errors: []` |
| Whitespace diff | `git diff --check` lulus | Pemeriksaan lokal |

Jest memeriksa quality gates meskipun payload memuat fusion lama, tiga kata bersama, pemisahan WPM, null versus nol, field hilang, loading/error/retry, empty response, navigasi keyboard, review transkripsi, peran siswa, kontrak PDF, komponen replay, rekomendasi tambahan, dan angka non-finite.

Browser memakai routing dan komponen asli dari production build, dengan API sintetis melalui harness. Browser memeriksa layout, tab keyboard, pemanggilan review/PDF, fluency asli setelah review, larangan tombol koreksi untuk siswa, serta mode parsial/legacy/loading/error/empty. Skenario memakai **data uji buatan**, bukan data peserta.

Pemeriksaan kontras menghitung rasio warna teks dan permukaan solid dari computed style: minimal 4,5:1 untuk teks normal dan 3:1 untuk teks besar. Ini mencakup teks yang tampil, termasuk bagian halaman di bawah viewport; konten accordion yang tertutup tidak termasuk. Pemeriksaan ini **bukan sertifikasi WCAG lengkap** atau uji pembaca layar.

### Temuan selama pengujian

1. Resolver Jest bawaan CRA belum membaca exports map React Router 7. Mock router diberi `virtual: true` khusus unit test. Routing nyata tetap diuji di browser; dependensi aplikasi tidak diubah.
2. Harness awal memilih background extension Edge, sehingga pemeriksaan menemukan halaman kosong. Pemilihan target diperbaiki menjadi tab `page` dengan URL `about:blank`.
3. Pemeriksaan kontras pada tab transkripsi menemukan rasio sekitar 2,96 dan 3,16 pada teks anotasi lama. Warna anotasi digelapkan; warna heading tabel dan tab replay juga disesuaikan. Pemeriksaan akhir seluruh tab lulus.
4. Build memunculkan peringatan Node `DEP0176` tentang `fs.F_OK`; build tetap berhasil. Ini berasal dari toolchain yang ada.
5. Koneksi HTTP harness sempat terputus saat Edge ditutup (WinError 10054). Penanganan shutdown harness diperbaiki. Tidak terjadi exception aplikasi.

## Screenshot

- [Desktop 1920](results-1920.png)
- [Laptop 1366](results-1366.png)
- [Tablet 768](results-768.png)
- [Mobile 390](results-390.png)
- [Analisis gabungan laptop](analysis-1366.png)
- [Analisis mobile](analysis-390.png)
- [Fluency dan rekomendasi laptop](fluency-1366.png)
- [Fluency mobile](fluency-390.png)

## Menjalankan kembali

Dari root repository, PowerShell:

```powershell
cd frontend
$env:CI = 'true'
npm.cmd test -- --watchAll=false --runInBand
npm.cmd run build
cd ..
backend\.venv\Scripts\python.exe test_reports\results_ui\browser_check.py
```

Harness browser memerlukan Edge, Python, `requests`, dan `websockets` (tersedia pada environment yang dipakai). Harness menjalankan static server sementara di loopback dan menutupnya setelah pengujian; backend dan database tidak diperlukan. File screenshot dan `browser_results.json` diperbarui saat harness dijalankan kembali. `source_hashes.json` mencatat SHA-256 source aplikasi yang dipakai saat build akhir.

Untuk melihat dengan sesi asli, jalankan frontend/backend melalui skrip lokal proyek dan buka halaman Results sesi yang sudah ada. Halaman memakai konfigurasi API proyek yang sama.

## Keterbatasan dan pekerjaan lanjutan

- Uji browser ini menggunakan response API sintetis; tidak memvalidasi ulang akurasi ASR, kamera, model, maupun persistensi MongoDB.
- Uji PDF memastikan URL dan mekanisme blob download, bukan isi PDF backend nyata. PDF masih memakai format backend yang sudah ada; redesign HTML tidak otomatis mengubah PDF.
- Fluency kosong tetap “Belum tersedia”. Tidak ada imputasi atau angka dummy pada aplikasi produksi. Perkiraan suku kata Indonesia tetap memiliki keterbatasan yang dijelaskan UI.
- Penanda suara sebelum review dapat mencampur salah baca dan salah dengar ASR. Keyakinan akustik bukan skor fonem atau probabilitas klinis.
- Fusion tetap observasional dan tidak menghasilkan skor baru. ETDD70/TURead tidak ditampilkan sebagai prediksi individual.
- Respons API belum menyediakan kategori terstruktur untuk tindakan rekomendasi; UI mencocokkan kata dalam rekomendasi untuk memilih tautan fitur yang sudah tersedia. Isi rekomendasi dan profil tetap dari backend.
- Pengujian manual dengan pengguna, pembaca layar, Firefox/Safari, kamera, mikrofon, dan sesi riil tetap diperlukan sebelum menyatakan seluruh sistem tervalidasi.
