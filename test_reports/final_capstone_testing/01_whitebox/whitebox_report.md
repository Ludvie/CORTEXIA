# White-Box Testing

Tiga prioritas diuji dari source terbaru, termasuk perubahan yang belum di-commit. Bukti kode asli dan nomor baris tersedia pada `*_source.txt`, `*_actual_source.txt`, dan `source_catalog.csv`.

## Konvensi CFG dan ruang lingkup

CFG I-DT dan fusion dibentuk dari AST fungsi aktual `backend/analytics.py:160–174 (_idt)` dan `backend/analytics.py:367–437 (fuse)`. Setiap statement merupakan node; `if`, `while`, dan `for` masing-masing merupakan satu predicate biner. Compound boolean dianggap atomik. Isi comprehension, conditional expression/ternary, called function, dan nested function dianggap operasi atomik pada tingkat ini. Angka ini **bukan kompleksitas penuh seluruh ekspresi Python**, bukan nilai Radon, dan bukan jumlah condition/MC/DC.

Quality Gate tersebar pada `backend/analytics.py:112–116 (calibration_ok)`, `backend/analytics.py:222–304 (gaze_metrics)`, `backend/analytics.py:471–492 (speech_metrics)`, serta `backend/analytics.py:494–549 (analyze)`. Grafik `quality_gate_classification` hanya menggambarkan seleksi akhir `quality` dari dua flag validitas: `layak if len(passed)==2 else parsial if passed else tidak_cukup`. Ternary diturunkan menjadi dua keputusan if yang ekuivalen dalam **script pengujian**. Label baris pada grafik ini merujuk `quality_gate_fragment.py`; source asli dan validasi upstream dicantumkan terpisah. Kompleksitas 3 tidak boleh dilaporkan sebagai kompleksitas seluruh fungsi `analyze` atau seluruh validator.

`P=1` adalah jumlah komponen terhubung, bukan jumlah predicate. Untuk setiap graph, V(G)=E−N+2P dan predicate+1 diverifikasi otomatis.

| function | nodes | edges | predicate_nodes | P | cyclomatic_complexity | observed_independent_paths | basis_complete |
| --- | --- | --- | --- | --- | --- | --- | --- |
| _idt | 20 | 23 | 4 | 1 | 5 | 5 | True |
| quality_gate_classification | 9 | 10 | 2 | 1 | 3 | 3 | True |
| fuse | 66 | 80 | 15 | 1 | 16 | 16 | True |


## Basis Path Testing

`basis_path_testing.csv` menghubungkan setiap test ID, input, expected output, actual output, status, dan urutan node yang benar-benar dilewati. Baris `independent=True` merupakan basis terpilih. Independensi diverifikasi dengan eliminasi Gauss atas GF(2) pada vektor paritas edge. Loop nol/satu/beberapa iterasi diwakili. Jumlah jalur independen yang teramati sama dengan V(G) pada ketiga graph dengan konvensi di atas; ini tidak menyatakan seluruh kombinasi input atau seluruh path loop telah diuji.

Instrumentasi berjalan pada salinan AST di memori. Setiap hasil salinan dibandingkan dengan fungsi produksi asli untuk memastikan perilaku tidak berubah. Untuk quality classification, empat kombinasi validitas juga dibandingkan terhadap hasil `analyze` produksi. Tidak ada source aplikasi yang ditulis ulang.

I-DT mencakup kosong, satu titik, 119/120 ms, dispersi 80/81 px, gap 500/501 ms, perluasan window, dan dua fiksasi. Gate mencakup passed, median error 0,159/0,16/0,161, 14/15 sampel validasi, 19/20 titik gaze, cakupan 30%, durasi suara 4,99/5 s dan keyakinan transkripsi 59,9/60%. Fusion mencakup kombinasi validitas, pola berbeda, pembagi nol, aturan dwell/revisit, serta concordance 39,9/40/40,1%.

## Coverage aktual

Statement coverage = 817/999 = **81.78%**. Branch coverage = 278/380 = **73.16%**. Angka tampilan gabungan coverage.py adalah 79.41%. Jumlah tes lulus tidak dipakai sebagai persentase coverage.

| file | covered_statements | statements | statement_percent | covered_branches | branches | branch_percent |
| --- | --- | --- | --- | --- | --- | --- |
| analytics.py | 399 | 434 | 91.94 | 145 | 170 | 85.29 |
| core.py | 26 | 37 | 70.27 | 2 | 12 | 16.67 |
| fluency.py | 73 | 77 | 94.81 | 27 | 30 | 90.0 |
| pronunciation.py | 215 | 219 | 98.17 | 92 | 96 | 95.83 |
| sessions.py | 104 | 232 | 44.83 | 12 | 72 | 16.67 |


Coverage hanya mencakup modul yang diimpor oleh proses pytest/worker. Server API yang berjalan terpisah tidak diinstrumentasi; oleh karena itu keberhasilan integrasi HTTP tidak otomatis meningkatkan coverage `sessions`, `auth`, atau `content`. Whisper yang belum tersedia, cabang exception, dan beberapa rekomendasi belum tercakup. Lihat JSON coverage untuk baris dan branch yang belum dijalankan. Fitur tidak dianggap benar hanya karena cakupannya tinggi.
