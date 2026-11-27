# Verifikasi Teknis Integrasi

Suite utama: 139 tes, 125 PASSED, 8 FAILED, 6 SKIPPED, 2 warnings. Suite mandiri tambahan: 3 PASSED, 0 FAILED. Total tes backend unik pada run akhir: **142**, dengan **128 PASSED, 8 FAILED, 6 SKIPPED**. Tidak ada error setup/teardown pada dua run akhir tersebut.

| test | status | reason |
| --- | --- | --- |
| tests.test_api_integration::test_speech_synthesis_returns_wav | FAILED | assert 503 == 200  +  where 503 = <Response [503]>.status_code |
| tests.test_api_integration::test_create_session_with_generated_audio_and_review | FAILED | assert 503 == 200  +  where 503 = <Response [503]>.status_code |
| tests.test_revisions::test_health_reports_local_models | FAILED | AssertionError: assert False  +  where False = <built-in method startswith of str object at 0x000002BF2B01C7F0>('piper')  +    where <built-in method startswith of str object at 0x000002BF2B01C7F0> = 'browser-fallback'.startswith |
| tests.test_revisions::test_tts_uses_piper | FAILED | assert 503 == 200  +  where 503 = <Response [503]>.status_code |
| tests.test_revisions::test_pronunciation_correct_word_scores_higher_than_wrong_word | FAILED | AssertionError: {"detail":"Contoh suara lokal belum tersedia."} assert (503 == 200)  +  where 503 = <Response [503]>.status_code |
| tests.test_revisions::test_pronunciation_reduplicated_word_uses_competitors | FAILED | AssertionError: {"detail":"Contoh suara lokal belum tersedia."} assert (503 == 200)  +  where 503 = <Response [503]>.status_code |
| tests.test_revisions::test_reading_session_audio_gets_pronunciation_clarity | FAILED | AssertionError: {"detail":"Contoh suara lokal belum tersedia."} assert (503 == 200)  +  where 503 = <Response [503]>.status_code |
| tests.test_revisions::test_gaze_game_levels_finish_and_dashboard_practices | FAILED | AssertionError: assert ('gaze_game' in {'gaze_game'} and 'pronunciation' in {'gaze_game'}) |


Tujuh kegagalan langsung bergantung pada TTS/Piper yang tidak tersedia atau asumsi bahwa engine tersebut ready; satu kegagalan daftar practice game mengikuti kegagalan tes pelafalan sebelumnya karena tidak terbentuk catatan pronunciation. Assertion asli tidak diubah agar lulus. Status eksekusinya tetap FAILED; penyebab lingkungan/dependensi dilaporkan terpisah.

Empat tes riset/import ditandai SKIPPED agar tidak melatih ulang, menulis dataset, atau membuka detail peserta. Satu tes Whisper SKIPPED karena bobot tidak tersedia. Satu tes cross-session lama SKIPPED karena fixture sesi berbasis TTS gagal dibuat; isolasi sesi/PDF/review kemudian diuji oleh suite mandiri tambahan dan lulus.

Suite mandiri menggunakan audio publik berulang >5 detik, kalibrasi dan gaze sintetis, serta MongoDB terpisah. Ini memverifikasi audio→ASR→VAD→fluency, gaze→fitur, fusion→database, fetch hasil, review→metrik baru sambil mempertahankan fluency/gaze asli, serta PDF. Halaman Results diverifikasi terpisah dengan kontrak API sintetis pada browser. Belum ada satu sesi kamera/mikrofon manusia yang dijalankan melalui seluruh UI hingga database.

Percobaan awal disimpan dalam `attempt_1`: 116 passed, 10 failed, 6 skipped, 8 error reports termasuk teardown; MongoDB awal berhenti merespons. Run akhir memakai proses mongod tersendiri, cache 0,25 GB, path data khusus dan port acak. Penyebab berhentinya server awal tidak dipastikan. Percobaan awal suite mandiri ditolak validasi domain email `.invalid`; fixture diperbaiki ke domain contoh yang diterima dan dijalankan ulang, tanpa mengubah validasi produksi.

Tidak ada subbab atau hasil formal Black-Box Testing. Endpoint checks di sini merupakan verifikasi integrasi dan security yang diarahkan source code.
