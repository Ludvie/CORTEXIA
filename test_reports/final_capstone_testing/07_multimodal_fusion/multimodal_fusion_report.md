# Rule-Based Multimodal Fusion

118 skenario gate/fusion/concordance terkontrol lulus. Sistem memakai aturan pada `backend/analytics.py:367–437 (fuse)`, bukan model hasil pelatihan bersama ETDD70, BAHANA, dan TURead.

Suara dipakai jika reliable; tatapan dipakai jika gaze_usable dan detail kata tersedia. Kata suara ditandai dari alignment substitution/deletion. Kata tatapan ditandai bila dwell ≥1,5×median atau visits≥2. Concordance=100×|kata salah suara ∩ kata sulit tatapan|/|kata salah suara|. Jika pembagi nol atau satu modalitas tidak layak, concordance null. Tambahan kata dengan confidence akustik rendah disimpan terpisah dan tidak mengganti rumus concordance tersebut.

Dengan 1.000 kata salah dan 399/400/401 kata bersama, hasil aktual 39,9/40/40,1% dengan concordant False/True/True. WER=20% tidak melewati aturan >20%; WPM=60 tidak memenuhi aturan <60. Skenario no modality, speech-only, gaze-only, kedua valid, zero median, tanpa error, dwell, revisit, serta skipped/on-text diuji. Pengujian pytest yang tersedia turut memeriksa word observations, timestamp invalid, urutan kata berulang, dan koreksi transkrip.

`quality_gate_test_cases.csv`, `concordance_validation.csv`, `fusion_test_cases.csv` memuat expected/actual. Grafik menghitung skenario tes, bukan akurasi asesmen. Tanpa ground truth ahli, peningkatan akurasi multimodal terhadap unimodal tidak dihitung. Hasil TURead terdahulu tetap eksperimen terpisah pada target regresi WPM; tidak membuktikan fusi webcam runtime lebih akurat atau diagnostik.
