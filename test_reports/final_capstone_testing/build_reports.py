"""Generate final reports from executed evidence, with explicit scope/limitations."""
from common import *
import ast,collections,importlib.metadata,platform,re,shutil,subprocess,xml.etree.ElementTree as ET,zipfile
from datetime import datetime,timezone,timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def readcsv(path):
    with (OUT/path).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def readjson(path):return json.loads((OUT/path).read_text(encoding='utf-8'))
def table(rows,keys):
    def cell(v):return str(v).replace('|','/').replace('\n',' ')
    return '| '+' | '.join(keys)+' |\n| '+' | '.join(['---']*len(keys))+' |\n'+'\n'.join('| '+' | '.join(cell(row.get(k,'')) for k in keys)+' |' for row in rows)+'\n'
def junit(path):
    root=ET.parse(OUT/path).getroot();rows=[]
    for case in root.iter('testcase'):
        state='FAILED' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None else 'SKIPPED' if case.find('skipped') is not None else 'PASSED'
        detail=next((case.find(k) for k in ['failure','error','skipped'] if case.find(k) is not None),None)
        message=detail.get('message','') if detail is not None else ''
        rows.append(dict(test=case.get('classname','')+'::'+case.get('name',''),status=state,time_sec=case.get('time',''),reason=message[:350]))
    return rows

def main():
    algorithms=readjson('algorithm_results.json');complexity=readcsv('01_whitebox/cyclomatic_complexity.csv')
    cases=junit('09_integration/pytest_results.xml');extra=junit('09_integration/supplemental/pytest_results.xml')
    counts=collections.Counter(r['status'] for r in cases+extra)
    browser=readjson('08_nonfunctional/ui/browser_results.json');front=readjson('08_nonfunctional/ui/frontend_tests.json')
    cov=readjson('01_whitebox/coverage.json');tot=cov['totals']
    coverage=[]
    for name,info in cov['files'].items():
        s=info['summary'];coverage.append(dict(file=name,covered_statements=s['covered_lines'],statements=s['num_statements'],statement_percent=round(100*s['covered_lines']/s['num_statements'],2),covered_branches=s['covered_branches'],branches=s['num_branches'],branch_percent=round(100*s['covered_branches']/s['num_branches'],2)))
    csvout('01_whitebox/coverage_by_file.csv',coverage)
    write('01_whitebox/coverage_summary.txt',f"Scope: existing pytest + internal security tests, imported modules only; separate live HTTP server is not instrumented. Direct algorithm harness/CFG clones are not included in this coverage.\nStatements: {tot['covered_lines']}/{tot['num_statements']} = {100*tot['covered_lines']/tot['num_statements']:.4f}%\nBranches: {tot['covered_branches']}/{tot['num_branches']} = {100*tot['covered_branches']/tot['num_branches']:.4f}%\nCombined coverage.py display: {tot['percent_covered']:.4f}% (not statement coverage alone).\n"+table(coverage,list(coverage[0])))
    shutil.copyfile(OUT/'09_integration/pytest_results.xml',OUT/'01_whitebox/pytest_results.xml')
    csvout('09_integration/test_results.csv',cases+extra)
    catalog=[]
    selections={'analytics.py':['_idt','calibration_ok','gaze_metrics','speech_metrics','quality_reasons','fuse','analyze','word_observations'], 'pronunciation.py':['substitution_cost','phonetic_distance','assess','word_confidence'], 'fluency.py':['segments','measure'], 'sessions.py':['reading_audio','audio_result','session_speech','create_session','review_session']}
    for name,functions in selections.items():
        text=(ROOT/'backend'/name).read_text(encoding='utf-8');lines=text.splitlines()
        for node in ast.parse(text).body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in functions:
                catalog.append(dict(file='backend/'+name,function=node.name,start_line=node.lineno,end_line=node.end_lineno))
                if name=='analytics.py' and node.name in ['calibration_ok','gaze_metrics','speech_metrics','analyze']:
                    write('01_whitebox/'+node.name+'_actual_source.txt','\n'.join(f'{i+1}: {lines[i]}' for i in range(node.lineno-1,node.end_lineno)))
    csvout('source_catalog.csv',catalog)
    ref=lambda f,n:next((f"{r['file']}:{r['start_line']}–{r['end_line']} ({n})" for r in catalog if r['file'].endswith(f) and r['function']==n),f'{f} ({n})')
    whitebox=f'''# White-Box Testing

Tiga prioritas diuji dari source terbaru, termasuk perubahan yang belum di-commit. Bukti kode asli dan nomor baris tersedia pada `*_source.txt`, `*_actual_source.txt`, dan `source_catalog.csv`.

## Konvensi CFG dan ruang lingkup

CFG I-DT dan fusion dibentuk dari AST fungsi aktual `{ref('analytics.py','_idt')}` dan `{ref('analytics.py','fuse')}`. Setiap statement merupakan node; `if`, `while`, dan `for` masing-masing merupakan satu predicate biner. Compound boolean dianggap atomik. Isi comprehension, conditional expression/ternary, called function, dan nested function dianggap operasi atomik pada tingkat ini. Angka ini **bukan kompleksitas penuh seluruh ekspresi Python**, bukan nilai Radon, dan bukan jumlah condition/MC/DC.

Quality Gate tersebar pada `{ref('analytics.py','calibration_ok')}`, `{ref('analytics.py','gaze_metrics')}`, `{ref('analytics.py','speech_metrics')}`, serta `{ref('analytics.py','analyze')}`. Grafik `quality_gate_classification` hanya menggambarkan seleksi akhir `quality` dari dua flag validitas: `layak if len(passed)==2 else parsial if passed else tidak_cukup`. Ternary diturunkan menjadi dua keputusan if yang ekuivalen dalam **script pengujian**. Label baris pada grafik ini merujuk `quality_gate_fragment.py`; source asli dan validasi upstream dicantumkan terpisah. Kompleksitas 3 tidak boleh dilaporkan sebagai kompleksitas seluruh fungsi `analyze` atau seluruh validator.

`P=1` adalah jumlah komponen terhubung, bukan jumlah predicate. Untuk setiap graph, V(G)=E−N+2P dan predicate+1 diverifikasi otomatis.

{table(complexity,['function','nodes','edges','predicate_nodes','P','cyclomatic_complexity','observed_independent_paths','basis_complete'])}

## Basis Path Testing

`basis_path_testing.csv` menghubungkan setiap test ID, input, expected output, actual output, status, dan urutan node yang benar-benar dilewati. Baris `independent=True` merupakan basis terpilih. Independensi diverifikasi dengan eliminasi Gauss atas GF(2) pada vektor paritas edge. Loop nol/satu/beberapa iterasi diwakili. Jumlah jalur independen yang teramati sama dengan V(G) pada ketiga graph dengan konvensi di atas; ini tidak menyatakan seluruh kombinasi input atau seluruh path loop telah diuji.

Instrumentasi berjalan pada salinan AST di memori. Setiap hasil salinan dibandingkan dengan fungsi produksi asli untuk memastikan perilaku tidak berubah. Untuk quality classification, empat kombinasi validitas juga dibandingkan terhadap hasil `analyze` produksi. Tidak ada source aplikasi yang ditulis ulang.

I-DT mencakup kosong, satu titik, 119/120 ms, dispersi 80/81 px, gap 500/501 ms, perluasan window, dan dua fiksasi. Gate mencakup passed, median error 0,159/0,16/0,161, 14/15 sampel validasi, 19/20 titik gaze, cakupan 30%, durasi suara 4,99/5 s dan keyakinan transkripsi 59,9/60%. Fusion mencakup kombinasi validitas, pola berbeda, pembagi nol, aturan dwell/revisit, serta concordance 39,9/40/40,1%.

## Coverage aktual

Statement coverage = {tot['covered_lines']}/{tot['num_statements']} = **{100*tot['covered_lines']/tot['num_statements']:.2f}%**. Branch coverage = {tot['covered_branches']}/{tot['num_branches']} = **{100*tot['covered_branches']/tot['num_branches']:.2f}%**. Angka tampilan gabungan coverage.py adalah {tot['percent_covered']:.2f}%. Jumlah tes lulus tidak dipakai sebagai persentase coverage.

{table(coverage,['file','covered_statements','statements','statement_percent','covered_branches','branches','branch_percent'])}

Coverage hanya mencakup modul yang diimpor oleh proses pytest/worker. Server API yang berjalan terpisah tidak diinstrumentasi; oleh karena itu keberhasilan integrasi HTTP tidak otomatis meningkatkan coverage `sessions`, `auth`, atau `content`. Whisper yang belum tersedia, cabang exception, dan beberapa rekomendasi belum tercakup. Lihat JSON coverage untuk baris dan branch yang belum dijalankan. Fitur tidak dianggap benar hanya karena cakupannya tinggi.
'''
    write('01_whitebox/whitebox_report.md',whitebox)
    # Preserve only aggregate research evidence; verify hashes without extracting dataset features.
    old=json.loads((ROOT/'test_reports/ml_comparison/experiment_config.json').read_text())
    dataset=ROOT/'assets/dataset/ETDD70_v2';source_files=[dataset/r['file'] for r in old['source_files']]
    individual=all(p.is_file() and sha(p)==r['sha256'] for p,r in zip(source_files,old['source_files']))
    h=hashlib.sha256()
    for p in sorted(source_files):h.update(p.name.encode());h.update(p.read_bytes())
    ml_check=dict(pipeline_unchanged=sha(ROOT/'backend/ml_pipeline.py')==old['pipeline_sha256'],source_files_unchanged=individual,source_file_count=len(source_files),dataset_sha256=h.hexdigest(),dataset_hash_matches=h.hexdigest()==old['dataset_sha256'],training_repeated=False)
    dump('10_existing_ml_results/relevance_check.json',ml_check)
    assert all(ml_check[k] for k in ['pipeline_unchanged','source_files_unchanged','dataset_hash_matches'])
    for name in ['comparison_recording.png','comparison_participant.png','confusion_matrices_recording.png']:
        shutil.copyfile(ROOT/'test_reports/ml_comparison'/name,OUT/'10_existing_ml_results'/name)
    bahana=readcsv('02_vad/bahana_runtime_regression.csv');ar=readcsv('06_fluency/bahana_formula_audit.csv');summary=readjson('06_fluency/bahana_existing_summary.json')
    write('02_vad/vad_report.md',f'''# Pengujian VAD

Source: {ref('fluency.py','segments')} dan {ref('fluency.py','measure')}. Konfigurasi aktual: WebRTC mode 2, mono PCM16 little endian, 16.000 Hz, frame 20 ms/640 byte, gap fill ≤100 ms, minimum segmen 60 ms, pause internal ≥250 ms dan long pause ≥500 ms. Objek VAD baru dibuat setiap pemanggilan. Frame akhir yang tidak lengkap tidak diklasifikasi.

Sepuluh pengujian terkontrol lulus. Mask keputusan VAD yang diketahui dipakai khusus untuk memverifikasi smoothing, batas durasi, frame rate, dan reset objek; ini bukan evaluasi classifier akustik. Silence digital dan noise diuji menggunakan WebRTC sebenarnya. Noise tidak otomatis dianggap silence/ucapan benar karena tidak mempunyai anotasi independen.

Audio BAHANA tidak ada di dalam ZIP, tetapi seluruh 140 path audio preprocessing pada CSV tersedia lokal. Enam audio dipilih deterministik: durasi minimum, median, maksimum dari strata QC PASS dan REVIEW yang sudah tersedia. Tidak dilakukan resampling, cleaning, training, atau pengolahan ulang keseluruhan dataset. Keenam file telah 16 kHz mono PCM16.

{table(bahana,['case_id','existing_qc','duration_sec','active_sec','prior_active_sec','active_delta_sec','segments','pauses','status'])}

Enam hasil durasi aktif cocok dengan artefak VAD sebelumnya. Ini uji regresi konsistensi, **bukan akurasi terhadap manusia**. Metadata validasi yang ditemukan memuat `validation_status`, flags, dan speech ratio; segmen bertipe `SMOOTHED_VAD` adalah keluaran algoritma, bukan ground truth. Oleh sebab itu Precision, Recall, F1, dan kesalahan batas terhadap manusia dibiarkan kosong/NOT APPLICABLE.

`vad_waveform.png` memperlihatkan fixture publik dengan hening tambahan; `bahana_vad_waveforms.png` memperlihatkan sampel BAHANA tanpa nama peserta. Arsiran adalah prediksi. Distribusi jeda deskriptif tersedia untuk kedua sumber. Template manual perlu diisi oleh anotator independen dengan toleransi yang disepakati terlebih dahulu, misalnya 20 ms sebagai resolusi frame; jangan menganggap toleransi itu sebagai hasil terukur.
''')
    write('03_eye_tracking/eye_tracking_report.md',f'''# Eye Tracking dan I-DT

Empat puluh kasus terkontrol lulus; pengujian yang sudah tersedia pada pytest memberikan dukungan tambahan. Source utama: {ref('analytics.py','_idt')}, {ref('analytics.py','gaze_metrics')}. Parameter: dispersi (max x−min x)+(max y−min y) ≤80 px, minimum 120 ms, gap antar-sampel ≤0,5 s. Koordinat area teks dinormalisasi lalu dikonversi menggunakan ukuran layout yang aktif.

Kalibrasi frontend (`frontend/src/components/Calibration.jsx:15–20`) menggunakan lima titik inti dan titik validasi terpisah, batas median error 0,16 dan minimal 15 sampel. Backend juga memerlukan flag passed=True. `frontend/src/pages/Reading.jsx:29` membatalkan validitas kalibrasi pada resize. WebGazer dan MediaPipe berasal dari loader lokal di `frontend/src/lib/media.js`; hasil uji ini tidak mengukur galat webcam manusia.

Uji mencakup koordinat NaN, waktu negatif/duplikat/di luar durasi, cakupan 30%, 19/20 sampel, 119/120 ms, dispersi 80/81 px, gap 500/501 ms, pemetaan kata terdekat, progression, regression, revisit, skipped words. Fixture lintasan kata [0,2,0] menghasilkan satu progression, satu regression dalam baris, satu kata dikunjungi ulang, dan skipped words 33,3%. Jitter relatif 0,05 menghasilkan satu fiksasi pada lebar 800 px dan nol pada 2000 px; ambang piksel membuat hasil sensitif pada ukuran tampilan.

`idt_test_cases.csv` dan `eye_tracking_metrics.csv` menyimpan input/expected/actual. Grafik fiksasi dan pemetaan adalah **sintetis**, bukan eye-tracker ground truth. Pengujian manusia, variasi pencahayaan, posisi kepala, kacamata, dan validasi terhadap alat referensi tetap MANUAL REQUIRED.
''')
    speech=readcsv('04_speech_recognition/speech_recognition_metrics.csv')
    write('04_speech_recognition/speech_recognition_report.md',f'''# Speech Recognition

{table(speech,['model','status','wer_percent','cer_percent','substitutions','deletions','insertions','timestamps_valid','reason'])}

Fixture publik `backend/tests/fixtures/bookbot_sample.wav`, durasi 3,7135 s, mempunyai teks ujaran yang didokumentasikan pada README fixture. Vosk-ID menghasilkan lima kata, WER=0%, CER=0%, S=D=I=0 pada rekaman tersebut. Ini bukan estimasi akurasi populasi, bukan penilaian disleksia, dan bukan hasil 140 audio BAHANA. Tidak ada transkripsi manusia multi-penilai baru yang dibuat.

WER=(S+D+I)/N; CER menggunakan operasi edit pada karakter teks ternormalisasi. Referensi fixture adalah ujaran yang didokumentasikan, sedangkan WER BAHANA yang sudah tersedia membandingkan ASR dengan teks stimulus dan tidak digunakan sebagai ground truth ASR. `reading_error_rate`/`asr_wer` setelah review memiliki referensi berbeda sesuai `speech_metrics`.

Whisper BLOCKED karena direktori bobot valid tidak ditemukan; model besar tidak diunduh. Perbandingan Vosk versus Whisper dan `asr_comparison.png` berstatus NOT APPLICABLE untuk run ini. Fallback readiness=False dan kegagalan Whisper sengaja disimulasikan, lalu Vosk asli dijalankan; keduanya berhasil. Audio rusak menghasilkan 422. Waktu inference dingin dan hangat dicatat terpisah pada CSV speech/performance. Timestamp diperiksa struktur/urutan/rentangnya, bukan akurasi alignment fonetik terhadap manusia.
''')
    pro=[r for r in algorithms if r['section']=='05_pronunciation'];fail=[r for r in pro if r['status']=='FAILED']
    write('05_pronunciation/pronunciation_report.md',f'''# Pronunciation Scoring

Hasil: 24 PASSED, 1 FAILED pada kasus terkontrol. Source: {ref('pronunciation.py','assess')}, {ref('pronunciation.py','phonetic_distance')}, {ref('pronunciation.py','substitution_cost')}.

Similarity aktual memakai `SequenceMatcher` atas ejaan tanpa spasi, bukan normalized Levenshtein. Jika forced-choice tersedia, skor = 0,35×similarity + 0,65×confidence target; komponen confidence bernilai nol bila pesaing menang. Jika target OOV/tidak ada pesaing, hanya similarity dipakai. Tanpa ucapan, skor null. Kategori tepat ≥85, hampir ≥60 dan <85, latihan <60; nama kode kategori terakhir adalah `latihan`, bukan `belum_tepat`.

Weighted phonetic distance adalah Levenshtein dengan biaya sisip/hapus 1 dan biaya substitusi dari fitur fonetik. Jarak ini digunakan untuk memilih pesaing, bukan langsung sebagai komponen formula skor 35/65. Kasus target `apel` yang cocok dan confidence 80% menghasilkan 87. Pesaing dengan similarity 75% menghasilkan 26,2. Perhitungan ini dihitung independen pada fixture dekoder terkontrol.

{table(fail,['case_id','expected','actual','status'])}

Temuan: komentar aturan cair l/r mengharapkan 0,4, tetapi kondisi `same_place` dievaluasi lebih dahulu dan menghasilkan 0,6 karena keduanya alveolar. Tes khusus memakai nilai yang dinyatakan komentar sebagai expected; ini ketidaksesuaian dokumentasi/intensi dengan prioritas cabang, bukan bukti bahwa 0,4 telah tervalidasi secara fonetik. Cabang 0,4 untuk pasangan l/r tidak tercapai. Tidak dilakukan perbaikan source otomatis.

Confidence per kata pada sesi membaca hanya berasal dari dekode bebas Vosk dan mempunyai cakupan kata cocok. Nilai tersebut berbeda dari skor latihan forced-choice. Tidak tersedia anotasi penilai manusia; kesesuaian skor terhadap pelafalan manusia adalah MANUAL REQUIRED. Grafik skor menampilkan fixture terkontrol, bukan validasi klinis.
''')
    write('06_fluency/fluency_report.md',f'''# Fluency Analysis

Sepuluh skenario formula/boundary terkontrol lulus. Untuk span ujaran U, durasi aktif A, jumlah kata W, perkiraan suku kata S, jumlah pause internal J, total pause D, dan run R=J+1:

- WPM ujaran = 60W/U; WPM legacy = 60W/durasi rekaman.
- Articulation Rate = S/A (suku kata/detik).
- Mean Length of Run = S/R (suku kata/rangkaian).
- Pause Frequency = 60J/U (jeda/menit).
- Mean Pause Duration = D/J detik bila J>0; null bila J=0.

Contoh terkontrol: dua kata `saya baca`, empat suku kata ortografis, A=1 s, U=1,5 s, J=1 dan D=0,5 s menghasilkan 80 kata/menit, 4 suku kata/detik, 2 suku kata/run, 40 jeda/menit, dan 0,5 s. Dengan rekaman 3 s, WPM legacy menjadi 40. Uji tambahan meliputi jeda 240/250/499/500 ms, timestamp nol/di luar durasi, teks dan timestamp berbeda, dan audio tanpa jeda.

Hasil 140 audio BAHANA dibaca kembali tanpa ekstraksi ulang. Pemeriksaan aritmetika dilakukan terhadap nilai intermediate yang sudah tersimpan (bukan validasi independen kualitas ASR/VAD):

{table(ar,['metric','checked','mismatches','max_absolute_error','tolerance','status'])}

Ketersediaan metrik: WPM {summary['metric_availability']['wpm']}/140, articulation rate {summary['metric_availability']['articulation_rate_syllables_per_sec']}/140, MLR {summary['metric_availability']['mlr_syllables_per_run']}/140, pause frequency 140/140, mean pause duration 43/140. Null tidak disamakan dengan nol. QC lama memuat 55 PASS dan 85 REVIEW; ini status otomatis, bukan label manusia.

Penelitian BAHANA menggunakan CMUdict Inggris versi 1.1.3, pronunciation pertama, serta jumlah fonem bernomor stress untuk suku kata; OOV tidak ditebak. Runtime Indonesia menghitung huruf vokal a/i/u/e/o sebagai proxy ortografis. Diftong, singkatan, kata serapan, dan ketidakcocokan ASR dapat menimbulkan perbedaan; kedua metode tidak boleh dianggap ekuivalen. Review manual mempertahankan fluency transkrip asli agar jumlah kata koreksi tidak dipasangkan dengan timestamp lama.
''')
    fusion=[r for r in algorithms if r['section']=='07_multimodal_fusion'];scenario=collections.Counter()
    for r in fusion:
        val=json.loads(r['actual'])
        if isinstance(val,dict) and 'basis' in val:scenario[val['basis']]+=1
    fig,ax=plt.subplots(figsize=(8,3));ax.bar(list(scenario),list(scenario.values()),color='#8173ba');ax.set(ylabel='Jumlah kasus sintetis',title='Skenario fusion yang benar-benar dijalankan');fig.tight_layout();fig.savefig(OUT/'07_multimodal_fusion/fusion_scenario_visualization.png',dpi=160);plt.close(fig)
    write('07_multimodal_fusion/multimodal_fusion_report.md',f'''# Rule-Based Multimodal Fusion

118 skenario gate/fusion/concordance terkontrol lulus. Sistem memakai aturan pada `{ref('analytics.py','fuse')}`, bukan model hasil pelatihan bersama ETDD70, BAHANA, dan TURead.

Suara dipakai jika reliable; tatapan dipakai jika gaze_usable dan detail kata tersedia. Kata suara ditandai dari alignment substitution/deletion. Kata tatapan ditandai bila dwell ≥1,5×median atau visits≥2. Concordance=100×|kata salah suara ∩ kata sulit tatapan|/|kata salah suara|. Jika pembagi nol atau satu modalitas tidak layak, concordance null. Tambahan kata dengan confidence akustik rendah disimpan terpisah dan tidak mengganti rumus concordance tersebut.

Dengan 1.000 kata salah dan 399/400/401 kata bersama, hasil aktual 39,9/40/40,1% dengan concordant False/True/True. WER=20% tidak melewati aturan >20%; WPM=60 tidak memenuhi aturan <60. Skenario no modality, speech-only, gaze-only, kedua valid, zero median, tanpa error, dwell, revisit, serta skipped/on-text diuji. Pengujian pytest yang tersedia turut memeriksa word observations, timestamp invalid, urutan kata berulang, dan koreksi transkrip.

`quality_gate_test_cases.csv`, `concordance_validation.csv`, `fusion_test_cases.csv` memuat expected/actual. Grafik menghitung skenario tes, bukan akurasi asesmen. Tanpa ground truth ahli, peningkatan akurasi multimodal terhadap unimodal tidak dihitung. Hasil TURead terdahulu tetap eksperimen terpisah pada target regresi WPM; tidak membuktikan fusi webcam runtime lebih akurat atau diagnostik.
''')
    security=[r for r in cases+extra if any(k in r['test'] for k in ['unauthorized','password','duplicate_email','student_role','cross_user','cross_owner','consent','invalid','upload_limits','temporary_audio_cleanup','corrupt_audio','schema_rejects'])]
    csvout('08_nonfunctional/security_test_results.csv',security)
    usability=[dict(check=r['name'],status='PASSED' if r['passed'] else 'FAILED',basis='Technical browser test with synthetic API responses') for r in browser['checks']]
    usability += [dict(check='SUS / kepuasan pengguna / anak dan pendamping nyata',status='MANUAL REQUIRED',basis='Tidak ada studi pengguna baru')]
    csvout('08_nonfunctional/usability_checklist.csv',usability)
    perf=readcsv('08_nonfunctional/performance_metrics.csv');e2e=readcsv('08_nonfunctional/end_to_end_performance.csv')
    write('08_nonfunctional/nonfunctional_report.md',f'''# Pengujian Nonfungsional

## Performance

{table(perf+e2e,['operation','n','mean_ms','median_ms','p95_ms'])}

Percobaan hangat dilakukan berurutan: Vosk/audio/session 5 kali, gaze 30 kali, fusion 100 kali. End-to-end HTTP mencakup upload fixture publik yang diulang menjadi 7,427 s, decode, ASR, VAD, analisis gaze, fusion, dan penyimpanan pada MongoDB khusus pengujian; bukan uji beban banyak pengguna. Median HTTP {float(e2e[0]['median_ms']):.2f} ms dan p95 {float(e2e[0]['p95_ms']):.2f} ms. Endpoint end-to-end memakai fixture berbeda durasi dari benchmark audio 3,7135 s sehingga tidak boleh dibandingkan langsung sebagai overhead murni.

Spesifikasi perangkat berada di `device.json`. CPU dilaporkan sebagai waktu CPU proses, bukan persentase utilisasi sistem. Nilai 0 ms untuk operasi sangat pendek dapat berasal dari resolusi penghitung CPU Windows. RSS disampling setiap 20 ms dan bukan peak absolut atau alokasi khusus model. Mesin memiliki RAM terbatas; hasil adalah satu run lokal, bukan jaminan SLA produksi.

## Security dan isolasi

{len(security)} pemeriksaan terpilih tersedia pada `security_test_results.csv`. Pengujian source-directed memeriksa guard autentikasi, role guru/siswa, filter owner pada sesi/materi/peserta dan PDF/review, consent, input invalid, upload 25 MB+1, audio rusak, dan unlink file temporer pada jalur berhasil/gagal. Database dan server berjalan pada loopback khusus tes. Ini bukan penetration test komprehensif.

## Usability teknis

{len(browser['checks'])} pemeriksaan browser lulus dan {front['numPassedTests']} frontend unit tests lulus. Empat viewport (1920,1366,768,390), tab keyboard, keterbacaan, kontras teks terlihat, empty/error/partial states, review/PDF routing, dan role siswa diuji. Source manifest cocok dengan build yang diperiksa. Tidak ada data peserta atau kamera/mikrofon manusia pada browser harness. Pemeriksaan ini adalah verifikasi teknis pendukung, **bukan subbab Black-Box Testing**, sertifikasi WCAG penuh, SUS, atau penelitian kepuasan pengguna.
''')
    failures=[r for r in cases if r['status']=='FAILED']
    write('09_integration/integration_report.md',f'''# Verifikasi Teknis Integrasi

Suite utama: 139 tes, 125 PASSED, 8 FAILED, 6 SKIPPED, 2 warnings. Suite mandiri tambahan: 3 PASSED, 0 FAILED. Total tes backend unik pada run akhir: **142**, dengan **128 PASSED, 8 FAILED, 6 SKIPPED**. Tidak ada error setup/teardown pada dua run akhir tersebut.

{table(failures,['test','status','reason'])}

Tujuh kegagalan langsung bergantung pada TTS/Piper yang tidak tersedia atau asumsi bahwa engine tersebut ready; satu kegagalan daftar practice game mengikuti kegagalan tes pelafalan sebelumnya karena tidak terbentuk catatan pronunciation. Assertion asli tidak diubah agar lulus. Status eksekusinya tetap FAILED; penyebab lingkungan/dependensi dilaporkan terpisah.

Empat tes riset/import ditandai SKIPPED agar tidak melatih ulang, menulis dataset, atau membuka detail peserta. Satu tes Whisper SKIPPED karena bobot tidak tersedia. Satu tes cross-session lama SKIPPED karena fixture sesi berbasis TTS gagal dibuat; isolasi sesi/PDF/review kemudian diuji oleh suite mandiri tambahan dan lulus.

Suite mandiri menggunakan audio publik berulang >5 detik, kalibrasi dan gaze sintetis, serta MongoDB terpisah. Ini memverifikasi audio→ASR→VAD→fluency, gaze→fitur, fusion→database, fetch hasil, review→metrik baru sambil mempertahankan fluency/gaze asli, serta PDF. Halaman Results diverifikasi terpisah dengan kontrak API sintetis pada browser. Belum ada satu sesi kamera/mikrofon manusia yang dijalankan melalui seluruh UI hingga database.

Percobaan awal disimpan dalam `attempt_1`: 116 passed, 10 failed, 6 skipped, 8 error reports termasuk teardown; MongoDB awal berhenti merespons. Run akhir memakai proses mongod tersendiri, cache 0,25 GB, path data khusus dan port acak. Penyebab berhentinya server awal tidak dipastikan. Percobaan awal suite mandiri ditolak validasi domain email `.invalid`; fixture diperbaiki ke domain contoh yang diterima dan dijalankan ulang, tanpa mengubah validasi produksi.

Tidak ada subbab atau hasil formal Black-Box Testing. Endpoint checks di sini merupakan verifikasi integrasi dan security yang diarahkan source code.
''')
    # Global summaries keep units explicit to avoid double-counting overlapping evidence.
    totals=[]
    for sec in ['02_vad','03_eye_tracking','05_pronunciation','06_fluency','07_multimodal_fusion']:
        cc=collections.Counter(r['status'] for r in algorithms if r['section']==sec)
        totals.append(dict(area=sec,unit='controlled cases',passed=cc['PASSED'],failed=cc['FAILED'],skipped=0,blocked=0,status='FAILED' if cc['FAILED'] else 'PASSED'))
    totals += [dict(area='01_whitebox',unit='independent paths (overlap controlled cases)',passed=sum(int(r['observed_independent_paths']) for r in complexity),failed=0,skipped=0,blocked=0,status='PASSED'),dict(area='02_vad BAHANA sample',unit='existing-audio regression cases',passed=6,failed=0,skipped=0,blocked=0,status='PASSED'),dict(area='04_speech_recognition',unit='inference/fallback/corrupt scenarios',passed=4,failed=0,skipped=0,blocked=1,status='BLOCKED'),dict(area='06_fluency BAHANA',unit='aggregate formula checks over existing artifacts',passed=5,failed=0,skipped=0,blocked=0,status='PASSED'),dict(area='09_integration backend',unit='unique pytest cases, final runs',passed=counts['PASSED'],failed=counts['FAILED'],skipped=counts['SKIPPED'],blocked=0,status='FAILED'),dict(area='08_nonfunctional UI browser',unit='technical checks',passed=len(browser['checks']),failed=0,skipped=0,blocked=0,status='PASSED'),dict(area='08_nonfunctional frontend',unit='Jest tests',passed=front['numPassedTests'],failed=front['numFailedTests'],skipped=front['numPendingTests'],blocked=0,status='PASSED'),dict(area='Human validation',unit='ground truth/SUS/live webcam',passed=0,failed=0,skipped=0,blocked=0,status='MANUAL REQUIRED'),dict(area='Whisper vs Vosk accuracy chart',unit='valid comparative experiment',passed=0,failed=0,skipped=0,blocked=0,status='NOT APPLICABLE')]
    csvout('TEST_SUMMARY.csv',totals)
    bugs='''# Bugs, kendala, dan batas interpretasi

| ID | Jenis / tingkat | Temuan | Tindakan berikutnya |
| --- | --- | --- | --- |
| B01 | Ketidaksesuaian kode–komentar / sedang | `substitution_cost(l,r)` dan arah sebaliknya terkena `same_place=0.6` sebelum aturan lateral/getar 0.4; satu tes formula gagal. | Konfirmasi spesifikasi fonetik yang diinginkan, lalu usulkan perbaikan urutan kondisi beserta tes. Tidak diperbaiki pada audit ini. |
| E01 | Dependensi lingkungan / tinggi untuk contoh suara | Piper tidak ready dan fallback espeak tidak tersedia; layanan TTS mengembalikan 503. Delapan tes gagal langsung/tidak langsung. | Sediakan model/engine yang diizinkan, kemudian ulangi tes terkait; jangan mengubah assertion menjadi menerima 503. |
| E02 | Dependensi lingkungan | Whisper tidak mempunyai snapshot bobot valid. | Sediakan bobot lokal yang sah dengan izin; evaluasi ulang Whisper terhadap transkripsi ujaran aktual. |
| E03 | Percobaan awal / teratasi pada run akhir | Koneksi MongoDB awal terputus, menyebabkan HTTP timeout/500. Penyebab proses berhenti tidak dipastikan. | Gunakan mongod/data pengujian terisolasi; run akhir berhasil menjalankan integrasi selain TTS. |
| T01 | Desain tes / sedang | Beberapa tes lama bergantung pada hasil tes TTS/pelafalan sebelumnya. | Pertahankan hasil gagal, tambah fixture mandiri; tiga tes mandiri telah lulus. |
| M01 | Validitas metodologi | Belum ada label temporal VAD, gaze manusia, rating pelafalan, atau label fusion ahli yang independen. | Lakukan anotasi/protokol manual; jangan menyimpulkan akurasi manusia dari fixture sintetis. |
| M02 | Domain | BAHANA Inggris memakai CMUdict; runtime Indonesia memakai hitung vokal. | Laporkan perbedaan dan validasi suku kata Indonesia; jangan menganggap ekuivalen. |
| M03 | Ruang lingkup coverage | Coverage pytest tidak memasukkan server HTTP terpisah dan bukan seluruh frontend/backend. | Gunakan angka sesuai scope. Jangan menyebut 100% basis CFG sebagai 100% coverage kode. |
| M04 | Performa | Satu mesin, n kecil untuk audio, warm sequential, RAM/CPU proses terbatas. | Uji perangkat target dan concurrency sebelum menetapkan SLA. |

Kegagalan harness yang diperbaiki: dependensi coverage awal tidak tersedia; paket uji dipasang hanya di `_test_dependencies`. Akses jaringan sandbox awal ditolak lalu instalasi yang diizinkan berhasil. Satu proses plotting mengalami OpenBLAS allocation error saat beban bersamaan; pekerjaan berikutnya membatasi thread BLAS pada proses pengujian dan menjalankan pekerjaan berat berurutan. Akses paket uji yang dipasang di luar sandbox memerlukan proses uji berizin. Tidak ada alasan ini dipakai untuk mengubah expected output algoritma.

Tidak ada source produksi yang diperbaiki. Model tidak dilatih ulang. Seluruh hasil yang belum memiliki ground truth dipisahkan dari hasil verifikasi implementasi.
'''
    write('BUGS_AND_LIMITATIONS.md',bugs)
    manual='''# Pengujian manual yang masih diperlukan

| Aktivitas | Status | Isian hasil yang belum tersedia |
| --- | --- | --- |
| Anotasi suara/hening dan batas segmen BAHANA oleh penilai independen | MANUAL REQUIRED | Jumlah audio: ___; penilai: ___; kesepakatan: ___; toleransi: ___ ms; Precision/Recall/F1: ___ |
| Transkripsi manual ujaran aktual untuk benchmark ASR multi-audio | MANUAL REQUIRED | Protokol normalisasi: ___; N ujaran: ___; WER/CER per model: ___ |
| Menyediakan bobot Whisper lokal (tanpa unduhan otomatis) | BLOCKED | Versi/checksum: ___; tanggal pemasangan: ___ |
| Memulihkan engine TTS/Piper lokal | BLOCKED | Engine/checksum: ___; hasil delapan tes setelah pemulihan: ___ |
| Validasi webcam terhadap titik referensi/eye tracker independen | MANUAL REQUIRED | Peserta anonim: ___; perangkat: ___; galat/presisi: ___; variasi viewport/cahaya/kacamata: ___ |
| Penilaian pelafalan oleh manusia | MANUAL REQUIRED | Rubrik: ___; N kata: ___; reliabilitas antarpenilai: ___; korelasi/kesesuaian: ___ |
| Evaluasi fusion terhadap anotasi pendamping/ahli pada sesi audio–gaze berpasangan | MANUAL REQUIRED | Target: ___; data uji terpisah: ___; eye-only/speech-only/fusion: ___ |
| Usability orang tua/guru/anak; SUS jika sesuai protokol | MANUAL REQUIRED | N responden: ___; persetujuan: ___; skor/temuan: ___ |
| Sesi nyata dari login, consent, kalibrasi, membaca, Results, review sampai PDF | MANUAL REQUIRED | Browser/perangkat: ___; hasil: ___; masalah: ___ |

Jangan mengisi kolom kosong dengan prediksi algoritma. Jangan memakai teks stimulus sebagai transkripsi manusia tanpa pemeriksaan ujaran. Template VAD tersedia di `02_vad/manual_validation_template.csv`. Browser harness hanya memakai data sintetis dan bukan studi pengguna.
'''
    write('MANUAL_TESTING_REQUIRED.md',manual)
    # Metadata records source integrity; local-only snapshots include all protected files.
    after=snapshot();before=readjson('PROTECTED_FILES_BEFORE.json')
    integrity=dict(protected_before=len(before),protected_after=len(after),unchanged=before==after,changed_files=[p for p in before if after.get(p)!=before[p]],added_files=[p for p in after if p not in before])
    dump('INTEGRITY_VERIFICATION.json',integrity)
    if not integrity['unchanged']:log('WARNING: protected source/artifact differences require review.')
    versions={}
    for name in ['numpy','scipy','scikit-learn','pandas','matplotlib','vosk','faster-whisper','webrtcvad-wheels','av','pytest','pytest-xdist','pytest-cov','coverage','psutil','fastapi','motor']:
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]='not registered'
    config=dict(date_local=datetime.now(timezone(timedelta(hours=7))).isoformat(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),uncommitted_changes_included=True,python=platform.python_version(),libraries=versions,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'backend/analytics.py',ROOT/'backend/fluency.py',ROOT/'backend/pronunciation.py',ROOT/'backend/sessions.py',ROOT/'backend/ml_pipeline.py',ROOT/'frontend/src/pages/Results.jsx']},vad=dict(mode=2,rate=16000,channels=1,bits=16,frame_ms=20,gap_fill_ms=100,min_speech_ms=60,pause_ms=250,long_pause_ms=500),idt=dict(dispersion_px=80,min_fixation_ms=120,max_gap_ms=500),test_database='cortexia_finaltest_20261127',test_server='temporary loopback; dynamic ports; isolated mongod',blas_threads=1,model_training_repeated=False,protected_files_unchanged=integrity['unchanged'],dataset_relevance=ml_check)
    dump('EXPERIMENT_CONFIG.json',config)
    # Main narrative and compact report-ready BAB IV content.
    ml=readcsv('10_existing_ml_results/comparison_metrics.csv')+readcsv('10_existing_ml_results/participant_metrics.csv')
    for row in ml:
        for k in ['accuracy','precision_macro','recall_macro','macro_f1','roc_auc']:row[k]=f"{100*float(row[k]):.2f}" if k!='roc_auc' else f"{float(row[k]):.4f}"
    tu=readcsv('11_existing_turead_results/metrics.csv')
    for r in tu:
        for k in ['mae','rmse','r2']:r[k]=f"{float(r[k]):.4f}"
    main=f'''# FINAL CAPSTONE TEST REPORT — CORTEXIA

Source yang diaudit adalah workspace terbaru, termasuk perubahan belum di-commit, HEAD `{config['git_head']}`. Source aplikasi dan artefak produksi terlindungi tidak berubah selama pekerjaan: **{integrity['unchanged']}**, {integrity['protected_before']} file diperiksa SHA-256. Tidak ada training LR/RF/TURead, cleaning ulang dataset, atau perubahan UI/arsitektur/hyperparameter.

## Ringkasan bukti

{table(totals,['area','unit','passed','failed','skipped','blocked','status'])}

Unit antarbaris berbeda dan beberapa bukti beririsan; **jangan menjumlahkan seluruh baris sebagai jumlah tes unik**. Keluarga bukti utama: 203 kasus algoritma langsung (202 lulus, 1 gagal); 142 tes pytest backend akhir (128 lulus, 8 gagal, 6 dilewati); 16 tes frontend lulus; 89 pemeriksaan browser lulus. Enam audio BAHANA dan lima audit formula agregat adalah bukti tambahan yang terpisah.

## Temuan utama

- CFG I-DT V=5, klasifikasi quality final V=3, fusion statement-level V=16; basis independen 5/5, 3/3, 16/16 teramati. Batas abstraksi dijelaskan dalam laporan white-box.
- Statement coverage {100*tot['covered_lines']/tot['num_statements']:.2f}% dan branch coverage {100*tot['covered_branches']/tot['num_branches']:.2f}% pada lima modul yang diinstrumentasi; bukan coverage keseluruhan aplikasi.
- Vosk pada satu fixture publik: WER/CER 0%. Whisper belum tersedia. Tidak ada klaim perbandingan model ASR yang belum dijalankan.
- VAD enam sampel BAHANA konsisten dengan hasil otomatis sebelumnya. Tidak tersedia ground truth temporal independen sehingga Precision/Recall/F1 manusia tidak dihitung.
- Seluruh 10 kasus formula fluency lulus. Lima audit aritmetika artefak BAHANA memiliki nol mismatch pada toleransi 2e-6.
- Satu tes biaya l/r gagal terhadap komentar metode (expected 0,4, actual 0,6). Delapan tes integrasi gagal terkait engine TTS/dependensi antar-tes. Tidak ada perbaikan produksi otomatis.
- Tiga integrasi mandiri lulus: ownership sesi/PDF/review, audio–gaze–fluency–database–review–PDF, dan benchmark HTTP lengkap.

## Hasil penelitian terdahulu yang digunakan kembali

Pipeline dan 211 file sumber ETDD70 masih cocok hash-nya dengan eksperimen lama. Tidak ada alasan material untuk training ulang. ETDD70 adalah eksperimen klasifikasi LR/RF 210 rekaman/70 peserta/16 fitur dengan fold peserta; BAHANA mendukung definisi fluency; TURead mendukung eksperimen regresi eksploratif. Ketiganya tidak dilatih bersama dan tidak menjadi classifier klinis pada sesi webcam.

{table(ml,['model','unit','n','accuracy','precision_macro','recall_macro','macro_f1','roc_auc'])}

Accuracy/Precision/Recall/F1 dalam persen; AUC dalam [0,1]. RF terbaik per rekaman (Macro F1 78,09%), LR terbaik per peserta (84,21%). Perbedaan kecil pada satu dataset/fold tetap tidak membuktikan superioritas umum.

{table(tu,['model','mae','rmse','r2'])}

TURead memakai 16.087 observasi oral yang dipilih dari 37.416 observasi terolah, 196 peserta, target WPM, 5-fold GroupKFold berdasarkan peserta. Multimodal MAE 13,3309 dibanding eye-only 13,4412 dan speech-only 13,6638; ini eksperimen terpisah, bukan validasi fusi runtime atau klasifikasi disleksia.

## Pemakaian bukti

Laporan per bagian terdapat pada folder 01–09. Folder 10–11 memuat salinan artefak agregat yang relevan beserta provenance. `REPORT_READY_CONTENT.md` adalah bahan BAB IV ringkas; `REPORT_FIGURE_INDEX.md` memilih grafik; `MANUAL_TESTING_REQUIRED.md` menyediakan ruang pengisian. Perintah reproduksi tersedia pada script pengujian di folder ini. Jalankan hanya terhadap lingkungan uji yang ditentukan; script `run_verification.py` memakai mongod sementara dan mempertahankan assertions suite lama.

Belum semua validasi penelitian selesai: anotasi manusia, uji webcam manusia, pemulihan TTS, bobot Whisper, dan studi usability masih diperlukan. ZIP bukti tidak menyertakan audio mentah, dataset baris peserta, model, database, credentials, environment, atau dependensi uji.
'''
    write('FINAL_CAPSTONE_TEST_REPORT.md',main)
    academic=f'''# Bahan BAB IV — Pengujian dan Analisis CORTEXIA

Dokumen ini merupakan naskah ringkas berbasis hasil eksekusi. Alokasi yang disarankan adalah 13–15 halaman BAB IV setelah tata letak kampus diterapkan; jumlah halaman akhir harus diperiksa pada dokumen laporan. Prioritaskan 3 halaman white-box, 2 halaman eksperimen terdahulu, 4–5 halaman pipeline audio/gaze/fusion, 2 halaman nonfungsional/integrasi, dan 1–2 halaman keterbatasan. Tidak ada subbab Black-Box Testing.

## 4.1 Tujuan dan rancangan

Pengujian bertujuan memverifikasi kesesuaian implementasi algoritma, batas input, interaksi antar-modul, serta karakteristik waktu proses. Source terbaru dan perubahan belum di-commit digunakan sebagai acuan. Pengujian dipisahkan menjadi verifikasi terkontrol, regresi terhadap artefak lama, pemeriksaan teknis integrasi/UI, dan validasi manusia yang belum dilaksanakan. Pemisahan tersebut mencegah hasil sintetis ditafsirkan sebagai akurasi asesmen membaca manusia.

Model penelitian tidak dilatih ulang. Kesamaan hash pipeline dan 211 file sumber ETDD70 memastikan hasil terdahulu masih relevan terhadap implementasi penelitian. Pengujian database memakai lingkungan terpisah. Status FAILED tetap dilaporkan meskipun penyebabnya adalah dependensi yang belum tersedia.

## 4.2 White-box dan basis path

Kompleksitas siklomatis dihitung menggunakan V(G)=E−N+2P, dengan P=1. Predicate biner meliputi if/while/for; compound boolean, comprehension dan conditional expression pada CFG fungsi diperlakukan atomik. Diagram quality hanya menyatakan pemilihan kategori akhir, dengan ternary diturunkan menjadi dua keputusan ekuivalen; bukan seluruh fungsi analyze.

{table(complexity,['function','nodes','edges','predicate_nodes','cyclomatic_complexity','observed_independent_paths'])}

Trace eksekusi dan matriks edge menunjukkan basis 5, 3, dan 16 jalur independen. Expected dan actual setiap jalur tercantum pada `01_whitebox/basis_path_testing.csv`. Kesamaan jumlah basis dengan kompleksitas berlaku pada abstraksi tersebut dan tidak menunjukkan seluruh path loop telah diuji. Statement coverage adalah {tot['covered_lines']}/{tot['num_statements']}={100*tot['covered_lines']/tot['num_statements']:.2f}%, sedangkan branch coverage adalah {tot['covered_branches']}/{tot['num_branches']}={100*tot['covered_branches']/tot['num_branches']:.2f}%. Coverage server HTTP terpisah tidak termasuk.

Kesimpulan: jalur basis prioritas telah dijalankan, tetapi cabang model yang tidak tersedia serta sejumlah penanganan exception tetap memerlukan verifikasi tambahan. Bukti: laporan, CFG Mermaid/PNG, source bernomor, JUnit, dan coverage pada folder 01.

## 4.3 Perbandingan LR–RF dan eksperimen TURead yang sudah tersedia

{table(ml,['model','unit','accuracy','precision_macro','recall_macro','macro_f1','roc_auc'])}

Evaluasi ETDD70 menggunakan prediksi out-of-fold dengan pembagian peserta yang sama, 210 rekaman dan 70 peserta. Angka persentase pada tabel berbeda unit dari AUC. Random Forest memberikan Macro F1 per rekaman 78,09%, lebih tinggi dari LR 77,04%. Setelah probabilitas OOF diagregasi per peserta, LR mencapai Macro F1 84,21% dan RF 81,39%. Pemilihan model bergantung unit evaluasi; tidak dilakukan klaim signifikansi atau generalisasi ke webcam Indonesia.

{table(tu,['model','mae','rmse','r2'])}

TURead mengevaluasi prediksi WPM menggunakan 16.087 observasi oral dari 196 peserta. MAE multimodal 13,3309 sedikit lebih rendah dari eye-only dan speech-only. Hasil ini bersifat eksploratif dan tidak membuktikan peningkatan akurasi diagnosis atau aturan fusi CORTEXIA. Bukti: folder 10 dan 11, digunakan kembali tanpa training.

## 4.4 Eye tracking dan I-DT

I-DT menggunakan dispersi maksimum 80 px, durasi minimum 120 ms, dan gap maksimum 500 ms. Empat puluh kasus terkontrol lulus, termasuk data kosong, NaN, duplikat, batas dispersi/durasi, pemetaan kata, regresi, revisit, skipped words dan cakupan. Pada lintasan sintetis [0,2,0], actual menunjukkan satu progression, satu regression, satu revisited word, dan 33,3% kata tidak tertatap.

Pengubahan lebar viewport dari 800 menjadi 2000 px dengan jitter relatif sama mengubah hasil deteksi dari satu menjadi nol fiksasi. Hasil tersebut konsisten dengan ambang dispersi dalam satuan piksel. Frontend membatalkan kalibrasi pada resize. Kesimpulan terbatas pada kebenaran pemrosesan data sintetis; galat webcam terhadap tatapan manusia belum diukur. Bukti: folder 03. Isian validasi manusia: jumlah peserta ___, galat ___, protokol referensi ___.

## 4.5 VAD dan speech recognition

VAD memakai mode 2, PCM16 mono 16 kHz, frame 20 ms, gap fill 100 ms, segmen minimum 60 ms, pause 250 ms, dan long pause 500 ms. Sepuluh pemeriksaan terkontrol lulus. Enam sampel BAHANA yang sudah diproses sebelumnya diuji ulang sebagai sampel regresi runtime; seluruh durasi aktif cocok dengan artefak lama. Grafik waveform menampilkan prediksi VAD, bukan anotasi ground truth. Precision, Recall, F1 dan boundary error belum dihitung karena anotasi temporal independen belum tersedia.

WER dihitung sebagai (S+D+I)/N. Pada satu rekaman publik 3,7135 s dengan referensi ujaran dari README, Vosk menghasilkan WER=0%, CER=0%, serta S=D=I=0. Timestamp terurut dan berada dalam rentang audio. Hasil tidak mewakili populasi atau keseluruhan BAHANA. Teks stimulus BAHANA tidak dipakai sebagai ground truth ASR. Whisper diblokir oleh ketiadaan bobot lokal; perbandingan akurasi dua model tidak dilakukan. Jalur fallback ke Vosk dan penolakan audio rusak berhasil diuji. Bukti: folder 02 dan 04.

## 4.6 Pronunciation scoring dan fluency

Skor latihan menggabungkan 35% similarity ejaan dan 65% confidence target pada forced-choice. Bila pesaing menang, komponen confidence target bernilai nol. Tanpa forced-choice skor hanya memakai similarity; tanpa ucapan skor null. Weighted phonetic distance menentukan kandidat pesaing, bukan langsung mengisi formula skor. Dari 25 kasus, 24 lulus dan satu gagal: biaya l/r aktual 0,6 tidak sesuai komentar 0,4 karena urutan cabang. Temuan tidak diperbaiki otomatis; keputusan metodologis diperlukan sebelum perubahan produksi.

Lima fitur fluency dihitung sebagai WPM=60W/U, AR=S/A, MLR=S/(J+1), PF=60J/U, dan MPD=D/J untuk J>0. Sepuluh kasus terkontrol lulus. Contoh dua kata, empat suku kata, U=1,5 s, A=1 s, J=1, D=0,5 s menghasilkan WPM 80, AR 4, MLR 2, PF 40, MPD 0,5. WPM rekaman dengan durasi 3 s adalah 40, sehingga kedua WPM tidak dapat dipertukarkan.

{table(ar,['metric','checked','mismatches','tolerance'])}

Audit artefak BAHANA mengonfirmasi konsistensi aritmetika pada metrik yang tersedia. CMUdict Inggris dan proxy vokal ortografis Indonesia merupakan metode suku kata berbeda. Mean pause null berarti tidak terdefinisi/tidak tersedia, bukan selalu nol. Kesimpulan: formula terimplementasi konsisten pada fixture, tetapi validitas linguistik terhadap ujaran manusia masih memerlukan anotasi. Bukti: folder 05 dan 06.

## 4.7 Quality gate dan multimodal fusion

Fusion observasional memakai irisan kata salah menurut alignment dan kata yang lama ditatap/dikunjungi ulang. Concordance=100×jumlah kata bersama/jumlah kata salah suara. Sebanyak 118 skenario terkontrol lulus. Batas 39,9%, 40%, dan 40,1% menghasilkan status concordant False, True, True. Ketika satu modalitas tidak layak, sistem tidak menyimpulkan pola gabungan; pembagi nol menghasilkan null. WER>20% dan WPM<60 merupakan aturan awal, bukan norma usia.

Hasil menunjukkan kesesuaian perilaku aturan, bukan peningkatan akurasi asesmen. ETDD70, BAHANA, dan TURead mempunyai peran berbeda dan tidak digabung sebagai dataset supervised multimodal palsu. Bukti: folder 07. Isian validasi ahli berpasangan: target ___, N sesi ___, hasil unimodal/fusion ___.

## 4.8 Nonfungsional dan integrasi

{table(perf+e2e,['operation','n','mean_ms','median_ms','p95_ms'])}

Performa diukur pada mesin lokal dengan percobaan berurutan, bukan uji beban. CPU dan RSS merupakan statistik proses dengan keterbatasan resolusi dan sampling. Pemeriksaan keamanan menguji autentikasi, role, ownership, consent, input, upload maksimum dan pembersihan berkas sementara. Pemeriksaan UI menghasilkan 89 checks dan 16 unit tests lulus pada empat viewport, tanpa menyatakan kepuasan pengguna.

Suite backend akhir mencatat 128 lulus, 8 gagal, dan 6 dilewati dari 142 tes. Kegagalan terkait TTS yang tidak tersedia serta dependensi antar-tes tetap dipertahankan. Tiga tes integrasi mandiri berhasil memverifikasi alur audio–gaze–database–review–PDF dan isolasi sesi lintas pengguna. Bukti: folder 08–09. Isian studi usability: responden ___, instrumen ___, hasil ___.

## 4.9 Batas kesimpulan

CORTEXIA telah memperoleh bukti verifikasi algoritma dan integrasi pada skenario yang diuji. Sistem belum dapat dinyatakan tervalidasi secara klinis atau bebas kesalahan. Kendala yang tersisa adalah ketidaksesuaian biaya fonetik l/r, TTS lokal tidak tersedia, Whisper belum tersedia, serta kebutuhan ground truth manusia untuk VAD, gaze, pelafalan, dan fusion. Pengujian manusia dan uji perangkat target harus diselesaikan sebelum klaim akurasi atau usability diperluas.
'''
    write('REPORT_READY_CONTENT.md',academic)
    write('CORTEXIA_CONTEXT_UPDATED.md',f'''# Konteks CORTEXIA setelah pengujian akhir

Tanggal lokal: {config['date_local']}. HEAD: {config['git_head']}. File ini melengkapi `CORTEXIA_CONTEXT.md` lama tanpa menimpanya. Source belum di-commit ikut diaudit.

Arsitektur: React Results/Reading/Calibration → FastAPI sessions/analytics/pronunciation/fluency → MongoDB. WebGazer/MediaPipe memproses wajah di browser; I-DT dan word mapping di backend. Audio didekode PCM16 mono 16 kHz satu kali, memakai Whisper bila bobot lokal valid, dengan fallback Vosk-ID. WebRTC VAD mode 2 mengisi lima fitur fluency. Fusi memakai aturan per kata, bukan LR/RF untuk inferensi pengguna.

ETDD70: eksperimen LR/RF, 70 peserta/210 rekaman/16 fitur, grouped out-of-fold; hasil lama masih relevan berdasarkan hash. RF unggul Macro F1 per rekaman, LR per peserta. TURead: regresi eksploratif WPM, 16.087 oral/196 peserta; model eksperimen tidak menjadi skor klinis runtime. BAHANA: 140 audio mendukung metodologi fluency Inggris; runtime Indonesia memakai perkiraan suku kata ortografis.

Results terbaru mempertahankan lima fitur, membedakan dua WPM, menjaga fluency ASR asli saat review, dan menampilkan fusion hanya bila kedua modalitas valid. 89 pemeriksaan browser dan 16 frontend tests lulus; data browser sintetis.

Hasil akhir: 203 kasus algoritma (202 lulus, 1 gagal); backend pytest 142 kasus unik (128 lulus, 8 gagal, 6 skipped); statement coverage {100*tot['covered_lines']/tot['num_statements']:.2f}% dan branch coverage {100*tot['covered_branches']/tot['num_branches']:.2f}% pada lima modul, bukan seluruh aplikasi. CFG basis lengkap pada abstraksi yang dijelaskan laporan white-box.

Bug/limit: komentar biaya l/r 0,4 versus hasil 0,6; TTS/Piper tidak tersedia; Whisper tidak tersedia; validasi manusia belum ada. Vosk WER/CER 0% hanya satu fixture publik. Enam sampel VAD BAHANA cocok artefak lama; bukan akurasi terhadap label manusia. Tiga integrasi mandiri audio/gaze/DB/review/PDF lulus. Tidak ada perubahan aplikasi/model selama audit. Lihat `FINAL_CAPSTONE_TEST_REPORT.md`, `BUGS_AND_LIMITATIONS.md`, `MANUAL_TESTING_REQUIRED.md`, dan `source_catalog.csv` untuk bukti rinci.
''')
    figures=[]
    for p in sorted(OUT.rglob('*.png')):
        if any(part.startswith('_') for part in p.relative_to(OUT).parts[:-1]):continue
        relative=str(p.relative_to(OUT)).replace('\\','/')
        recommended=any(x in relative for x in ['_idt.png','quality_gate_classification.png','comparison_recording.png','bahana_vad_waveforms','fixation_visualization','fluency_distribution','performance_visualization'])
        figures.append(dict(file=relative,placement='BAB IV (pilih sesuai ruang)' if recommended else 'Lampiran/bukti pendukung',note='Sintetis bila fixture; deskriptif bila BAHANA; model lama bila folder 10/11'))
    write('REPORT_FIGURE_INDEX.md','# Indeks gambar\n\n'+table(figures,['file','placement','note'])+'\nUntuk batas 50 halaman, gunakan sekitar 6–8 gambar paling informatif pada BAB IV; gabungkan confusion/metrics bila perlu. CFG fusion lengkap dan screenshot tambahan dapat menjadi lampiran sesuai aturan kampus. `asr_comparison.png` tidak dibuat karena perbandingan dua model belum valid.\n')
    # Format/readability verification, safe evidence package. Private runtime folders excluded.
    from PIL import Image
    verified=0
    for p in OUT.rglob('*.png'):
        if any(part.startswith('_') for part in p.relative_to(OUT).parts[:-1]):continue
        with Image.open(p) as img:img.verify();verified+=1
    dump('OUTPUT_VERIFICATION.json',dict(png_verified=verified,pytest_unique_cases=len(cases+extra),pytest_status_counts=dict(counts),algorithm_cases=len(algorithms),algorithm_failed=sum(r['status']=='FAILED' for r in algorithms),frontend_passed=front['numPassedTests'],browser_checks=len(browser['checks']),source_integrity=integrity['unchanged'],basis_formula_verified=all(int(r['edges'])-int(r['nodes'])+2*int(r['P'])==int(r['cyclomatic_complexity']) for r in complexity)))
    log('Reports generated from measured outputs; source integrity='+str(integrity['unchanged']))
    archive=OUT/'CORTEXIA_FINAL_TEST_EVIDENCE.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            rel=p.relative_to(OUT)
            if not p.is_file() or any(part.startswith('_') or part=='attempt_1' for part in rel.parts[:-1]):continue
            if p.suffix.lower() not in ['.md','.csv','.png','.mmd','.txt','.xml','.json','.log']:continue
            if p.name in ['PROTECTED_FILES_BEFORE.json','coverage.json','algorithm_results.json','frontend_tests.json','run.json','server.log','mongo.log','pytest.log','frontend_tests.log','EXECUTION.log','source_hashes.json']:continue
            # Raw test logs stay local. Only synthetic case CSVs, aggregate research and sanitized metadata are packaged.
            z.write(p,str(rel))
    log('Evidence ZIP created (reports, aggregate/synthetic CSV, figures, XML; no audio/datasets/models/database/dependencies).')

if __name__=='__main__':main()
