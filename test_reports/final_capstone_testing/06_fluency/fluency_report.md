# Fluency Analysis

Sepuluh skenario formula/boundary terkontrol lulus. Untuk span ujaran U, durasi aktif A, jumlah kata W, perkiraan suku kata S, jumlah pause internal J, total pause D, dan run R=J+1:

- WPM ujaran = 60W/U; WPM legacy = 60W/durasi rekaman.
- Articulation Rate = S/A (suku kata/detik).
- Mean Length of Run = S/R (suku kata/rangkaian).
- Pause Frequency = 60J/U (jeda/menit).
- Mean Pause Duration = D/J detik bila J>0; null bila J=0.

Contoh terkontrol: dua kata `saya baca`, empat suku kata ortografis, A=1 s, U=1,5 s, J=1 dan D=0,5 s menghasilkan 80 kata/menit, 4 suku kata/detik, 2 suku kata/run, 40 jeda/menit, dan 0,5 s. Dengan rekaman 3 s, WPM legacy menjadi 40. Uji tambahan meliputi jeda 240/250/499/500 ms, timestamp nol/di luar durasi, teks dan timestamp berbeda, dan audio tanpa jeda.

Hasil 140 audio BAHANA dibaca kembali tanpa ekstraksi ulang. Pemeriksaan aritmetika dilakukan terhadap nilai intermediate yang sudah tersimpan (bukan validasi independen kualitas ASR/VAD):

| metric | checked | mismatches | max_absolute_error | tolerance | status |
| --- | --- | --- | --- | --- | --- |
| wpm | 139 | 0 | 4.943820357539153e-07 | 2e-06 | PASSED |
| articulation_rate_syllables_per_sec | 122 | 0 | 5.00000000069889e-07 | 2e-06 | PASSED |
| mlr_syllables_per_run | 122 | 0 | 3.33333333379926e-07 | 2e-06 | PASSED |
| pause_frequency_per_min | 140 | 0 | 4.489795912832051e-07 | 2e-06 | PASSED |
| mean_pause_duration_sec | 43 | 0 | 1.1102230246251565e-16 | 2e-06 | PASSED |


Ketersediaan metrik: WPM 139/140, articulation rate 122/140, MLR 122/140, pause frequency 140/140, mean pause duration 43/140. Null tidak disamakan dengan nol. QC lama memuat 55 PASS dan 85 REVIEW; ini status otomatis, bukan label manusia.

Penelitian BAHANA menggunakan CMUdict Inggris versi 1.1.3, pronunciation pertama, serta jumlah fonem bernomor stress untuk suku kata; OOV tidak ditebak. Runtime Indonesia menghitung huruf vokal a/i/u/e/o sebagai proxy ortografis. Diftong, singkatan, kata serapan, dan ketidakcocokan ASR dapat menimbulkan perbedaan; kedua metode tidak boleh dianggap ekuivalen. Review manual mempertahankan fluency transkrip asli agar jumlah kata koreksi tidak dipasangkan dengan timestamp lama.
