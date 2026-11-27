# Speech Recognition

| model | status | wer_percent | cer_percent | substitutions | deletions | insertions | timestamps_valid | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Vosk-ID | PASSED | 0.0 | 0.0 | 0 | 0 | 0 | True |  |
| Whisper | BLOCKED |  |  |  |  |  |  | Local model weights unavailable; no download |
| fallback_no_whisper | PASSED |  |  |  |  |  |  | Actual Vosk; mocked Whisper readiness/failure only |
| fallback_failed_whisper | PASSED |  |  |  |  |  |  | Actual Vosk; mocked Whisper readiness/failure only |
| corrupt_audio | PASSED |  |  |  |  |  |  | Expected HTTPException 422 |


Fixture publik `backend/tests/fixtures/bookbot_sample.wav`, durasi 3,7135 s, mempunyai teks ujaran yang didokumentasikan pada README fixture. Vosk-ID menghasilkan lima kata, WER=0%, CER=0%, S=D=I=0 pada rekaman tersebut. Ini bukan estimasi akurasi populasi, bukan penilaian disleksia, dan bukan hasil 140 audio BAHANA. Tidak ada transkripsi manusia multi-penilai baru yang dibuat.

WER=(S+D+I)/N; CER menggunakan operasi edit pada karakter teks ternormalisasi. Referensi fixture adalah ujaran yang didokumentasikan, sedangkan WER BAHANA yang sudah tersedia membandingkan ASR dengan teks stimulus dan tidak digunakan sebagai ground truth ASR. `reading_error_rate`/`asr_wer` setelah review memiliki referensi berbeda sesuai `speech_metrics`.

Whisper BLOCKED karena direktori bobot valid tidak ditemukan; model besar tidak diunduh. Perbandingan Vosk versus Whisper dan `asr_comparison.png` berstatus NOT APPLICABLE untuk run ini. Fallback readiness=False dan kegagalan Whisper sengaja disimulasikan, lalu Vosk asli dijalankan; keduanya berhasil. Audio rusak menghasilkan 422. Waktu inference dingin dan hangat dicatat terpisah pada CSV speech/performance. Timestamp diperiksa struktur/urutan/rentangnya, bukan akurasi alignment fonetik terhadap manusia.
