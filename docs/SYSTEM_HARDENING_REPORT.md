# CORTEXIA --- SYSTEM HARDENING AUDIT REPORT

**Tanggal audit:** 12 November 2026\
**Sumber:** `CORTEXIA-main.zip` dan master prompt CORTEXIA\
**Mode pengerjaan:** Audit read-only. Tidak ada kode, UI, database,
threshold, model, atau konfigurasi yang diubah.

## 1. Ringkasan eksekutif

Repository CORTEXIA sudah memiliki alur multimodal yang cukup lengkap:
Faster-Whisper untuk transkripsi, Vosk untuk penilaian pelafalan,
WebGazer untuk pengambilan tatapan, I-DT untuk deteksi fixation,
rule-based multimodal fusion, FastAPI untuk penyimpanan sesi, dan
eksperimen ETDD70 yang terpisah.

Fondasi machine learning ETDD70 menunjukkan praktik validasi yang baik:
5-fold `StratifiedGroupKFold`, pemisahan berdasarkan peserta, serta
imputation dan scaling di dalam pipeline. Artefak model yang tersedia
menunjukkan tidak ada overlap peserta pada kelima fold.

Namun, terdapat beberapa temuan algoritmik yang perlu diselesaikan
sebelum hasil sesi CORTEXIA dipakai dalam pengujian formal. Temuan
paling penting adalah:

1.  `speech_reliable` belum benar-benar menjadi quality gate bagi fusion
    dan rekomendasi.
2.  WER otomatis masih mencampur kesalahan ASR dengan kesalahan membaca.
3.  Logika fusion dapat menyatakan dua modalitas mendukung kesulitan
    kata yang sama tanpa concordance kata yang cukup.
4.  Implementasi minimum fixation I-DT tidak konsisten dengan keterangan
    120 ms.
5.  Timestamp gaze duplikat dan timestamp di luar durasi sesi masih
    dapat memengaruhi coverage.
6.  Status `calibration.passed` tidak diperiksa oleh backend.
7.  Automated tests belum cukup untuk membuktikan perhitungan matematis
    algoritma.

**Kesimpulan audit:** jangan langsung melakukan pengujian formal
algoritma pada kondisi kode saat ini sebelum temuan P0 diperbaiki dan
diuji secara deterministik.

## 2. Ruang lingkup dan metode audit

Pemeriksaan mencakup:

-   `backend/analytics.py`
-   `backend/pronunciation.py`
-   `backend/ml_pipeline.py`
-   `backend/research.py`
-   `backend/sessions.py`
-   `backend/server.py`
-   `backend/core.py`
-   `backend/auth.py`
-   `backend/content.py`
-   `backend/tests/`
-   Frontend `Reading.jsx`, `media.js`, `Calibration.jsx`,
    `Results.jsx`, `GazeReplay.jsx`, dan `Dashboard.jsx`
-   Dataset ETDD70, metadata model, test reports, README, dan PRD.

Pemeriksaan dilakukan melalui pembacaan source code, penelusuran alur
data, pemeriksaan artefak evaluasi, pemeriksaan daftar test, dan parsing
sintaks statis untuk 18 file Python.

### Batasan verifikasi

-   Tidak ada test suite yang dijalankan terhadap server CORTEXIA pada
    audit ini.
-   Runtime audit tidak menyediakan sejumlah dependensi backend yang
    dibutuhkan, termasuk `faster-whisper`, `jiwer`, `motor`, `vosk`, dan
    `pytest-xdist`.
-   `pytest.ini` mengharuskan `pytest-xdist`, sedangkan dependensi
    tersebut tidak tercantum dalam `backend/requirements.txt`.
-   Pemeriksaan sintaks statis berhasil untuk 18 file Python, tetapi hal
    ini bukan bukti bahwa algoritma berjalan benar.
-   Hasil 18/18 test pada `test_reports/pytest/pytest_results.xml`
    merupakan hasil historis bertanggal 1 Oktober 2026 dan hanya
    mencakup `test_api_integration.py`.

## 3. Arsitektur dan alur data yang ditemukan

### 3.1 Alur suara

1.  Frontend merekam audio menggunakan `MediaRecorder`.
2.  Audio dikirim melalui multipart request ke `POST /api/sessions`.
3.  Backend menyimpan audio sementara.
4.  `decode_pcm()` mengubah audio menjadi PCM 16 kHz mono.
5.  Faster-Whisper base melakukan transkripsi bahasa Indonesia dan
    menghasilkan word timestamps.
6.  `normalize()` menormalkan teks.
7.  `align()` membandingkan teks referensi dengan transkrip.
8.  Backend menghitung WER, accuracy turunan, WPM, pause, dan confidence
    transkripsi.
9.  Jika tersedia, Vosk menghasilkan kepercayaan akustik per kata.

### 3.2 Alur gaze

1.  WebGazer menghasilkan koordinat tatapan di browser.
2.  Frontend mengubah koordinat ke sistem relatif terhadap area bacaan.
3.  Frontend menyimpan titik `(x, y, t)` dan snapshot layout kata.
4.  Backend memvalidasi tipe dan batas dasar input menggunakan Pydantic.
5.  `gaze_metrics()` menyaring nilai non-finite dan mengurutkan titik
    berdasarkan timestamp.
6.  `fixations_idt()` mendeteksi fixation.
7.  `assign_word()` memetakan fixation ke baris dan kata terdekat.
8.  Backend menghitung dwell, revisit, regression, return sweep, skipped
    words, dan reading order.

### 3.3 Alur multimodal

1.  Metrik suara dan gaze dihitung secara terpisah.
2.  `fuse()` membandingkan kata yang salah menurut alignment dengan kata
    yang memiliki dwell panjang atau revisit.
3.  Sistem menghasilkan basis modalitas, concordance, pola
    observasional, dan penjelasan.
4.  `analyze()` menghasilkan quality, profile, quality reasons, dan
    recommendations.
5.  Hasil disimpan ke MongoDB melalui endpoint sesi.

### 3.4 Alur ETDD70

ETDD70 diproses melalui `dataset_frame()` dan `train()`. Dataset
penelitian tetap terpisah dari sesi webcam CORTEXIA. Tidak ditemukan
pemanggilan model Logistic Regression atau Random Forest di dalam
`analytics.analyze()`.

## 4. Temuan audit algoritma

## 4.1 Speech processing

### Faster-Whisper

Implementasi menggunakan model `base`, CPU `int8`, bahasa `id`,
`beam_size=5`, `word_timestamps=True`, `vad_filter=True`, dan
`condition_on_previous_text=False`.

Temuan:

-   `transcribe()` mengabaikan segmen dengan `no_speech_prob > 0.7`.
-   Word timestamps dan probability disimpan, tetapi belum divalidasi
    untuk nilai finite, negatif, atau urutan waktu.
-   Audio kosong setelah decoding belum ditangani melalui validasi PCM
    eksplisit.
-   `asr_confidence()` menghitung rata-rata probability kata Whisper.
    Nilai ini merupakan indikator confidence model, bukan akurasi
    transkripsi.
-   Jika confidence tidak tersedia (`None`), `speech_reliable` tetap
    dapat bernilai true selama syarat durasi dan jumlah kata terpenuhi.
    Kondisi confidence tidak diketahui sebaiknya dibedakan dari
    confidence yang memadai.

### WER dan alignment

`normalize()` mengubah teks menjadi huruf kecil dan menghilangkan tanda
baca, dengan tanda hubung di antara kata tetap dipertahankan. `align()`
menggunakan `jiwer.process_words()` dan mengeluarkan substitution,
deletion, insertion, hits, WER, serta accuracy turunan.

Temuan utama:

-   Pada sesi awal, WER membandingkan teks referensi dengan transkrip
    otomatis. Karena itu, WER tersebut mencampur kesalahan Whisper dan
    kesalahan membaca anak.
-   Endpoint koreksi transkrip menghitung ulang WER terhadap teks
    referensi menggunakan transkrip manual, tetapi tidak menyimpan ASR
    WER sebagai metrik terpisah.
-   Tidak tersedia pasangan metrik `ASR WER` dan `Reading Error Rate`.
-   `align()` mengembalikan dictionary kosong jika teks referensi
    kosong. Kondisi ini tidak memiliki penanganan eksplisit pada
    `analyze()`.
-   Belum ada unit test yang membuktikan WER 0%, substitution, deletion,
    insertion, teks kosong, dan normalisasi tanda baca.

**Rekomendasi:** pertahankan field lama untuk kompatibilitas API, tetapi
tambahkan pemisahan metrik yang jelas. ASR WER dihitung antara transkrip
otomatis dan transkrip manual; Reading Error Rate dihitung antara
transkrip manual dan teks referensi. Jangan mengarang ground truth
ketika koreksi manual belum tersedia.

### WPM dan pause

WPM dihitung dari jumlah token transkrip yang dinormalisasi dibagi
durasi audio dikali 60. Pembagian dengan nol sudah dicegah dengan
pemeriksaan `duration > 0`.

Pause dihitung dari selisih timestamp kata berurutan yang minimal 0,5
detik.

Risiko yang belum ditutup:

-   Timestamp kata tidak divalidasi urutan dan rentangnya.
-   Pause dapat tidak akurat jika word timestamps tidak berurutan atau
    tidak lengkap.
-   WPM otomatis masih dapat dipakai untuk rekomendasi walaupun
    transkripsi belum andal.

## 4.2 Eye-tracking dan I-DT

### Sampling dan quality gate

Konfigurasi yang ditemukan:

-   `EXPECTED_HZ = 8`
-   Minimum gaze samples = 20
-   Minimum gaze coverage = 30%
-   Median calibration error maksimal = 0,16
-   Validation samples minimal = 15

Temuan:

-   Backend mengurutkan timestamp, sehingga urutan input yang salah
    tidak dilaporkan sebagai masalah.
-   Timestamp duplikat tidak dihapus atau dihitung secara khusus.
-   Timestamp yang lebih besar daripada durasi sesi tidak disaring.
-   Coverage menggunakan jumlah sampel dibagi estimasi sampel
    berdasarkan `EXPECTED_HZ`, bukan distribusi interval aktual.
-   Sampel duplikat dan sampel di luar durasi masih dapat menaikkan
    coverage.
-   Statistik interval aktual seperti median, p95, dan jumlah gap besar
    belum dikeluarkan.
-   Pemeriksaan `gaze_usable` menggunakan literal `20` dan `0.3`,
    sedangkan konstanta `MIN_GAZE_SAMPLES` dan `MIN_GAZE_COVERAGE` hanya
    digunakan dalam pesan alasan kualitas. Ini membuat konfigurasi tidak
    menjadi sumber kebenaran tunggal.
-   Coverage 30% dari target 8 Hz secara matematis dapat terpenuhi pada
    laju rata-rata sekitar 2,4 Hz. Karena itu, coverage 30% tidak sama
    dengan jaminan sampling aktual 8 Hz.

### I-DT

Konfigurasi:

-   Dispersion threshold = 80 px
-   `MIN_FIX_S = 0.12`
-   `MAX_GAP_S = 0.5`

Temuan:

-   Pemeriksaan durasi awal menggunakan `MIN_FIX_S * 0.6`, yaitu 0,072
    detik.
-   Dengan demikian, implementasi dapat menerima window fixation yang
    lebih pendek daripada 120 ms.
-   Keterangan frontend menyebut minimum fixation 120 ms, sehingga
    dokumentasi hasil dan perilaku kode belum konsisten.
-   Dimensi piksel untuk seluruh fixation diambil dari layout pertama.
    Jika dimensi area berubah pada layout berikutnya, skala dispersi
    tidak mengikuti perubahan tersebut.
-   Belum ada test khusus untuk batas durasi, dispersion, gap, timestamp
    duplikat, dan timestamp tidak berurutan.

**Rekomendasi:** jangan mengubah threshold 120 ms atau 80 px hanya untuk
memperbaiki hasil. Tentukan dahulu apakah toleransi 0,6 memang
disengaja. Setelah keputusan dibuat, uji dengan data sintetis pada batas
threshold dan dokumentasikan formula aktual.

### Gaze mapping dan regression

`assign_word()` memilih baris terdekat dan kemudian kata terdekat
berdasarkan jarak ke bounding box. `gaze_metrics()` memisahkan
regression dalam baris, regression antarbaris, progression, dan return
sweep.

Temuan:

-   Koordinat layout dinormalisasi oleh frontend, tetapi validasi
    `WordBox` backend masih mengizinkan rentang luas `-10` sampai `10`;
    lebar dan tinggi bahkan dapat bernilai nol.
-   Tidak ada validasi semantik bahwa index kata unik, box memiliki
    ukuran positif, atau posisi box berada dalam area viewport.
-   `layout_at()` mengasumsikan layout terurut berdasarkan waktu.
-   Belum ada pengujian return sweep, perpindahan beberapa baris,
    mapping gagal, dan perubahan layout.

## 4.3 Pronunciation assessment

Implementasi menggunakan Vosk/Kaldi untuk free decoding dan
forced-choice decoding. Similarity dihitung menggunakan
`SequenceMatcher`; ketika forced-choice tersedia, skor menggabungkan
similarity dan confidence dengan bobot 0,35 dan 0,65.

Threshold yang ditemukan:

-   Skor ≥ 85: `tepat`
-   Skor ≥ 60 dan \< 85: `hampir`
-   Skor \< 60: `latihan`

Temuan:

-   `competitors()` menggunakan Levenshtein distance pada ejaan kata.
    Ini bukan pengukuran fonetik atau fonologis.
-   Jika target ada di vocabulary tetapi tidak memiliki kata pesaing,
    forced-choice masih dapat berjalan dengan grammar yang hanya berisi
    target. Dalam kondisi ini, target dapat menang karena pilihan
    alternatif tidak tersedia.
-   Jika forced-choice tidak tersedia, skor memakai similarity saja.
    Formula yang berbeda ini tetap menggunakan threshold verdict yang
    sama.
-   `mean_confidence` pada `word_confidence()` dihitung hanya dari kata
    yang berhasil disejajarkan sebagai `equal`. Kata yang hilang atau
    salah tidak masuk ke denominator. Nilai rata-rata dapat terlihat
    tinggi walaupun coverage kata rendah.
-   `assess()` belum melakukan validasi eksplisit terhadap PCM kosong
    setelah decoding.
-   Segmentasi suku kata merupakan heuristik berbasis huruf vokal dan
    digraph, bukan syllabifier linguistik yang tervalidasi untuk seluruh
    kata bahasa Indonesia.
-   Belum ada test untuk skor tepat 85, tepat 60, di bawah 60, target
    tidak tersedia, pesaing kosong, PCM kosong, dan kasus suku kata
    khusus.

**Batas klaim:** skor tidak boleh disebut akurasi fonetik atau
diagnosis. Similarity ejaan dan confidence ASR bukan ukuran fonem yang
tervalidasi.

## 4.4 Multimodal fusion dan profiling

Temuan paling kritis:

1.  `has_speech` ditentukan dari `accuracy is not None`, bukan dari
    `speech_reliable`. Akibatnya, transkrip yang tidak andal masih
    dianggap modalitas suara tersedia untuk fusion.
2.  Parameter `speech_reliable` hanya menambahkan catatan pada
    penjelasan fusion; parameter tersebut tidak mencegah pemakaian data
    suara yang tidak andal.
3.  `analyze()` masih menggunakan WER untuk profil latihan ketepatan
    kata ketika `speech_reliable` false.
4.  Quality ditetapkan menjadi `parsial` jika `enough` true atau gaze
    usable. Jika speech tidak reliable dan gaze tidak usable tetapi
    durasi/kata memenuhi batas minimum, quality tetap menjadi `parsial`,
    padahal tidak ada modalitas yang lulus quality gate.
5.  `speech_poor` menggabungkan WER tinggi dan WPM rendah. Keduanya
    bukan bukti yang sama: WER berkaitan dengan ketepatan transkrip,
    sedangkan WPM berkaitan dengan kelancaran.
6.  Pola gabungan dipilih jika `concordant OR gaze_irregular`.
    Akibatnya, gaze irregular secara global dapat memicu label
    seolah-olah kesalahan suara dan kesulitan tatapan terjadi pada kata
    yang sama, meskipun concordance kata bernilai 0%.
7.  Jika WPM rendah tetapi WER 0%, sistem tetap dapat menyebut kesulitan
    pengenalan kata ketika gaze irregular, walaupun tidak ada kata salah
    ucap yang menjadi bukti.
8.  `skipped_words_percent > 50` dipakai sebagai threshold irregularity
    tambahan, tetapi threshold ini tidak termasuk daftar threshold utama
    dalam master prompt.

**Rekomendasi:** pisahkan sinyal akurasi kata dan kelancaran. Fusion
kata yang sama hanya boleh menyatakan concordance bila bukti kata-level
tersedia dan memenuhi threshold concordance. Gaze irregular global dapat
menjadi temuan paralel, tetapi tidak boleh dijelaskan sebagai kesalahan
pada kata yang sama tanpa overlap kata yang nyata.

## 4.5 Machine learning ETDD70

Temuan positif:

-   `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`
    digunakan.
-   Group menggunakan `subject_id`, sehingga seluruh rekaman satu
    peserta berada di fold yang sama.
-   Imputation dan scaling berada di dalam `make_pipeline()`.
-   Prediksi OOF digunakan untuk accuracy, macro-F1, dan confusion
    matrix.
-   Metadata model tersimpan menunjukkan overlap peserta 0 pada semua
    fold.
-   ETDD70 tetap terpisah dari profiling sesi webcam Indonesia.

Artefak yang tersedia:

  Model                   Accuracy   Macro-F1   Baseline accuracy   Baseline macro-F1
  --------------------- ---------- ---------- ------------------- -------------------
  Logistic Regression       0,7714     0,7704              0,5000              0,3333
  Random Forest             0,7810     0,7809              0,5000              0,3333

Dataset berisi 70 peserta Ceko usia 9--10 tahun, 35 per kelas, 3 tugas,
210 rekaman, dan eye-tracker 250 Hz. Tidak tersedia audio atau pasangan
gaze-speech bahasa Indonesia.

Kekurangan:

-   `precision` dan `recall` tidak dihitung/disimpan secara eksplisit
    dalam laporan.
-   Accuracy dihitung atas 210 rekaman/tugas, bukan 70 prediksi peserta
    yang sudah diagregasi.
-   Feature importance berasal dari model akhir yang di-fit pada seluruh
    data setelah evaluasi OOF. Hal ini perlu dijelaskan sebagai
    importance model final, bukan importance OOF.
-   Versi library, hash dataset, dan versi ekstraksi fitur belum dicatat
    secara lengkap untuk reproduksibilitas lintas lingkungan.

## 5. Integrasi backend dan data

### Hal yang sudah baik

-   Request sesi divalidasi dengan Pydantic.
-   Koordinat gaze menolak NaN dan Infinity pada input request.
-   Audio diproses melalui file sementara dan dihapus pada blok
    `finally`.
-   Kegagalan analisis suara selain ukuran file berlebih dapat disimpan
    sebagai sesi parsial agar hasil gaze tetap tersedia.
-   Data sesi memiliki TTL 30 hari.
-   Endpoint sesi menggunakan pemeriksaan kepemilikan pengguna.
-   Koreksi transkrip hanya dapat dilakukan oleh teacher pemilik sesi.
-   Response model `Document` mengizinkan field tambahan, membantu
    kompatibilitas API.

### Risiko yang perlu ditutup

-   Tidak ada idempotency key untuk `POST /sessions`. Jika server sudah
    menyimpan sesi tetapi respons hilang, retry frontend dapat membuat
    sesi duplikat.
-   Timestamp kata dari model AI tidak mendapat validasi finite/rentang
    seperti input gaze.
-   `GazePoint.t` tidak divalidasi terhadap `duration` sesi.
-   Layout tidak divalidasi urutannya dan tidak divalidasi konsistensi
    index kata.
-   Job training disimpan dalam dictionary proses (`jobs`), sehingga
    status tidak persisten ketika proses restart.
-   Dashboard menghitung rata-rata accuracy dan tren dari semua sesi
    yang memiliki accuracy, tanpa menyaring `speech_reliable`. Transkrip
    otomatis yang tidak andal dapat masuk ke agregasi perkembangan.
-   `memory/PRD.md` menyebut 9 titik kalibrasi dan espeak-ng, sedangkan
    implementasi sekarang memakai 5 titik inti, 3 titik validasi,
    refinement adaptif, dan Piper dengan fallback. Dokumentasi PRD perlu
    diselaraskan.

### Ketersediaan model lokal di ZIP

-   Bobot Faster-Whisper base tersedia di `backend/models/whisper`.
-   Direktori/bobot Vosk `backend/models/vosk-id` tidak terdapat dalam
    ZIP.
-   Bobot Piper `backend/models/piper` juga tidak terdapat dalam ZIP.
-   `setup_local_models.py` menyediakan proses unduh Vosk dan Piper saat
    setup. Jika setup tersebut belum dijalankan, `vosk_ready()` akan
    false dan TTS dapat memakai fallback yang tersedia.
-   URL unduhan Vosk mengacu ke branch `main`, sedangkan Piper mengacu
    ke `resolve/main`; versi/commit dan checksum tidak dipatok. Ini
    merupakan risiko reproduksibilitas deployment, bukan alasan untuk
    mengunduh model baru selama audit.

## 6. Kesiapan automated testing

File pengujian:

  File                                        Jumlah test function
  ----------------------------------------- ----------------------
  `backend/tests/test_analysis_unit.py`                          7
  `backend/tests/test_api_integration.py`                       18
  `backend/tests/test_revisions.py`                             10
  **Total**                                                 **35**

Catatan:

-   `test_analysis_unit.py` mencakup confidence transkrip, review,
    speech error, mapping index, dan dua skenario fusion.
-   Belum ada unit test langsung untuk WER
    substitution/deletion/insertion, I-DT boundary, timestamp
    validation, regression return sweep, dan fusion quality gate.
-   `test_api_integration.py` dan `test_revisions.py` menggunakan
    `REACT_APP_BACKEND_URL`, sehingga membutuhkan server yang sudah
    berjalan.
-   `pytest.ini` mewajibkan `pytest-xdist` dan menggunakan `-n 2`,
    tetapi plugin tersebut tidak tercantum dalam requirements.
-   `requests` dan pytest juga tidak tercantum dalam `requirements.txt`.
-   `scripts/smoke_test.py` merujuk `scripts/dev-test-account.txt`, yang
    tidak terdapat dalam ZIP.
-   `test_reports/pytest/pytest_results.xml` berisi 18 test yang lulus
    pada 1 Oktober 2026. Itu merupakan bukti historis untuk test API
    integration, bukan bukti seluruh 35 test telah dijalankan.

## 7. Prioritas perbaikan

### P0 --- sebelum pengujian algoritma formal

1.  Jadikan `speech_reliable` syarat penggunaan data suara pada fusion
    dan rekomendasi.
2.  Pisahkan ASR WER dan Reading Error Rate saat transkrip manual
    tersedia.
3.  Pisahkan logika WER dan WPM pada fusion.
4.  Jangan menyatakan concordance kata jika overlap kata-level tidak
    memenuhi threshold.
5.  Validasi timestamp gaze: duplikat, urutan, rentang terhadap durasi,
    dan interval aktual.
6.  Tegaskan definisi minimum fixation 120 ms dan selaraskan
    implementasi dengan dokumentasi.
7.  Pastikan quality gate memeriksa status calibration `passed`.

### P1 --- penting untuk validitas hasil

1.  Validasi layout dan koordinat kata.
2.  Uji mapping, regression, dan return sweep.
3.  Tambahkan coverage kata untuk confidence Vosk.
4.  Tangani forced-choice tanpa pesaing.
5.  Tambahkan precision dan recall pada laporan ETDD70.
6.  Pisahkan agregasi dashboard berdasarkan status keandalan.
7.  Tambahkan idempotency untuk pembuatan sesi.
8.  Lengkapi dependensi pengujian dan pisahkan unit test dari
    integration test.

### P2 --- jika waktu memungkinkan

1.  Pusatkan dan versioning threshold.
2.  Catat versi library dan hash dataset/model.
3.  Selaraskan PRD dan README dengan implementasi.
4.  Perbaiki logging dan status job training agar lebih tahan restart.

## 8. Rencana pengerjaan satu minggu

  -----------------------------------------------------------------------
  Hari                    Fokus                   Output yang harus
                                                  tersedia
  ----------------------- ----------------------- -----------------------
  1                       Speech quality gate dan Unit test WER, review,
                          pemisahan WER           confidence, dan WPM

  2                       Timestamp gaze dan I-DT Statistik interval,
                                                  duplicate/gap handling,
                                                  boundary tests

  3                       Gaze mapping dan fusion Test mapping kata,
                                                  regression,
                                                  concordance, partial
                                                  modality

  4                       Pronunciation dan ML    Boundary score tests,
                                                  competitor tests,
                                                  precision/recall

  5                       API dan penyimpanan     Contract tests, partial
                                                  failure, duplicate
                                                  retry

  6                       Regression testing      Unit suite dan
                                                  integration suite
                                                  dijalankan, hasil
                                                  dicatat

  7                       Dokumentasi Bab IV      Matrix hasil aktual,
                                                  bukti output, batasan
                                                  pengujian
  -----------------------------------------------------------------------

Threshold yang sudah ada tidak boleh diubah hanya untuk memperbaiki
angka hasil. Setiap perubahan threshold harus didahului alasan teknis,
data uji, dan perbandingan hasil.

## 9. Kesimpulan audit

CORTEXIA sudah memiliki arsitektur yang relevan untuk sistem
observasional multimodal dan eksperimen ETDD70 yang terpisah. Bagian ML
menunjukkan validasi peserta yang benar pada artefak yang tersedia.

Namun, bagian yang paling perlu diperkuat sebelum pengujian formal bukan
UI atau penambahan model baru, melainkan semantik kualitas data dan
konsistensi perhitungan: pemisahan kesalahan ASR dan membaca, quality
gate suara, validasi timestamp gaze, konsistensi I-DT, dan logika
concordance fusion.

**Status akhir audit:** - Audit source code: selesai untuk file dan alur
utama yang tercantum. - Perubahan kode: tidak ada. - Python syntax
parse: 18 file berhasil diparse. - Automated tests pada arsip saat ini:
belum dijalankan. - Hasil historis: 18/18 API integration tests tercatat
lulus pada 1 Oktober 2026. - Kesiapan pengujian algoritma formal: perlu
menyelesaikan P0 terlebih dahulu.
