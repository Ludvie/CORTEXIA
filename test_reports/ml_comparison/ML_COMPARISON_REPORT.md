# Perbandingan Logistic Regression dan Random Forest CORTEXIA

Eksperimen dijalankan langsung pada dataset ETDD70 v2 melalui fungsi backend/ml_pipeline.py train.
Tanggal mulai UTC 2026-11-27T04:46:04.599177+00:00. HEAD 1074c7d8ed80db550c495483c5e2cbdc065f164d.

## Metode

Dataset terdiri atas 210 rekaman, 70 peserta, dan 16 fitur aktual pipeline. Tiap peserta mempunyai tiga rekaman.
Labels pada tingkat rekaman berimbang 105/105. Label 1 adalah kelas dyslexic pada dataset.
Pembagian StratifiedGroupKFold lima fold, shuffle=True, random_state=42, dan group subject_id dipakai identik
untuk LR, RF, serta baseline. Setiap rekaman masuk test tepat sekali. Seluruh fold memiliki overlap peserta nol.
Imputasi median dan StandardScaler berada di dalam pipeline yang di-clone dan di-fit hanya pada training fold.
Tidak ada cleaning tambahan atau pencarian hyperparameter.

Script memanggil train dua kali. Wrapper in-memory memverifikasi fold yang diberikan pipeline dan menangkap
keluaran cross_val_predict pada presisi penuh sebelum JSON aplikasi membulatkan probabilitas.
Kode aplikasi tetap identik menurut SHA256. Dataset dan artefak riset sebelumnya juga diperiksa hash-nya
sebelum dan setelah eksperimen. File baru disimpan dalam folder eksperimen ini.
Laporan model baru mempertahankan metrik agregat. OOF terpisah memakai alias peserta P001 dan seterusnya.

LR memakai C=0.1, max_iter=3000, class_weight=balanced, random_state=42.
RF memakai 160 pohon, max_depth=5, min_samples_leaf=3, n_jobs=2, class_weight=balanced, random_state=42.
Parameter lengkap termasuk default versi terpasang tercantum di experiment_config.json.
Baseline adalah DummyClassifier most_frequent yang di-fit pada training fold.

## Evaluasi per rekaman

| Model | Accuracy | Precision macro | Recall macro | Macro F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.771429 | 0.776341 | 0.771429 | 0.770408 | 0.860045 |
| Most frequent | 0.500000 | 0.250000 | 0.500000 | 0.333333 | 0.500000 |
| Random Forest | 0.780952 | 0.781054 | 0.780952 | 0.780933 | 0.864762 |

## Evaluasi per peserta

Probabilitas OOF tiga rekaman dirata-ratakan per peserta, lalu kelas ditentukan pada ambang >=0.5.
Precision dan recall tabel memakai macro average dengan zero_division=0. ROC-AUC memakai probabilitas kelas 1.
Probabilitas baseline berasal dari training fold, termasuk pada agregasi peserta.

| Model | Accuracy | Precision macro | Recall macro | Macro F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.842857 | 0.850000 | 0.842857 | 0.842051 | 0.921633 |
| Most frequent | 0.500000 | 0.250000 | 0.500000 | 0.333333 | 0.500000 |
| Random Forest | 0.814286 | 0.816612 | 0.814286 | 0.813944 | 0.928980 |

## Model dengan Macro F1 tertinggi

Per rekaman, Random Forest memperoleh Macro F1 0.780933,
selisih 0.010524 terhadap model pembanding.
Per peserta, Logistic Regression memperoleh Macro F1 0.842051,
selisih 0.028107.
Penetapan pemenang ini berlaku untuk pembagian fold dan dataset eksperimen ini.
Selisih terhadap baseline untuk masing-masing unit disimpan di baseline_comparison.csv.

## Grafik dan tabel

- comparison_metrics.csv berisi pooled OOF per rekaman.
- participant_metrics.csv berisi pooled OOF per peserta.
- fold_metrics.csv memuat kedua unit, jumlah training/testing, overlap, dan hash indeks fold.
- leakage_audit.csv serta fold_assignments.csv memungkinkan pemeriksaan pemisahan peserta.
- confusion_matrices_recording.png dan confusion_matrices_participant.png memuat matriks LR/RF.
- comparison_recording.png dan comparison_participant.png membandingkan lima metrik.
- roc_curve_recording.png dan roc_curve_participant.png memuat kurva OOF dan baseline.
- feature_importance_rf.png berisi impurity-based importance dari fit akhir seluruh data.
- coefficients_lr.png berisi koefisien bertanda, pada fitur yang distandardisasi, menuju kelas 1.
- Semua grafik juga diekspor ke PDF; nilai numerik matriks dan fitur disimpan dalam CSV.

Grafik fitur menjelaskan model akhir yang dilatih pipeline setelah CV. Seluruh angka performa dan kurva ROC
dihitung dari OOF. Magnitudo koefisien bergantung pada standardisasi dan korelasi fitur. Importance RF dapat
bias pada karakteristik fitur; kedua grafik belum menunjukkan hubungan sebab-akibat.

## Keterbatasan dan leakage

Pemeriksaan ini membuktikan tidak ada overlap peserta dalam train/test pada data yang diberikan, fitur identitas
tidak masuk X, dan preprocessing dipelajari di dalam CV. Pemeriksaan tidak dapat menyingkirkan seluruh bias
pada proses pengumpulan sumber atau ketergantungan fitur terhadap target secara substantif.
Peserta uji berbeda, tetapi stimulus/tugas dapat berulang antar peserta.
Tiga rekaman satu peserta saling berkaitan, sehingga metrik peserta perlu dilaporkan bersama metrik rekaman.
Tidak dilakukan uji signifikansi, confidence interval, tuning, external test, atau validasi webcam Indonesia.
Memilih model terbaik dari CV yang sama belum memberikan estimasi generalisasi independen setelah seleksi.
Eksperimen tidak mengubah model yang dipakai assessment dan tidak menghasilkan probabilitas klinis pengguna.

## Reproduksi dan error

Library aktual, konfigurasi lengkap, hash setiap file dataset, hash agregat, hash pipeline, dan hash evaluator
ada di experiment_config.json. Execution.log mencatat eksekusi dan warning. ERRORS.md mencatat error persiapan.
Jalankan dari root dengan backend/.venv/Scripts/python test_reports/ml_comparison/run_comparison.py.
Script menolak overwrite ketika RUN_STARTED.json sudah ada; gunakan folder baru untuk eksperimen berikutnya.
Diperlukan dependensi backend serta matplotlib. Durasi total 30.47 detik.

## Verifikasi akhir

Metrik pada kedua tabel dihitung ulang secara independen dari CSV OOF dan cocok dalam toleransi 1e-12.
Matriks konfusi cocok dengan prediksi CSV. Agregasi peserta cocok dengan rerata OOF per rekaman.
Delapan PNG dapat dibaca dan delapan PDF tersedia. Rincian ada di verification.json.

Matplotlib belum tersedia pada pemeriksaan awal dan kemudian dipasang ke virtual environment.
Peringatan izin cache font terjadi saat inisialisasi, namun ekspor grafik selesai. ERRORS.md memuat
catatan error dan pemulihan. Source aplikasi dan model produksi tidak disunting dalam eksperimen ini.
Perubahan scripts/run-backend.cmd sudah ada sebelum eksperimen.

ROC-AUC RF pada tingkat peserta lebih tinggi daripada LR, meskipun Macro F1 LR lebih tinggi pada
ambang 0,5. AUC mengukur pengurutan skor lintas ambang, sedangkan Macro F1 di sini mengevaluasi
keputusan pada satu ambang. Oleh sebab itu kesimpulan pemilihan model perlu menyebut metrik
utama dan unit evaluasinya. Untuk mempertahankan unit evaluasi pipeline asli per rekaman,
RF adalah pemenang berdasarkan Macro F1 pada run ini. Untuk agregasi per peserta, LR unggul.
