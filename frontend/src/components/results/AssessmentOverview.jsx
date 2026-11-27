import {Link} from 'react-router-dom';
import {Mic, Eye, BookOpen, ArrowRight, Layers, CheckCircle2, CircleHelp, Target, Gamepad2, ShieldCheck} from 'lucide-react';
import {isNumber, numberLabel, resultState, practiceFor, FLUENCY_FIELDS} from './resultPresentation';

export function MetricCard({icon: Icon, title, value, unit, interpretation, detail, id, percent = false}) {
  const available = isNumber(value);
  return <article className="assessment-metric">
    <h3><Icon size={20} aria-hidden="true"/>{title}</h3>
    <div className="assessment-value" data-testid={`metric-${id}`}><strong>{numberLabel(value, 2)}</strong><span>{available ? unit : 'Belum tersedia'}</span></div>
    {percent && available && <div className="assessment-meter" aria-hidden="true"><span style={{width: `${Math.max(0, Math.min(100, value))}%`}}/></div>}
    <p>{interpretation}</p>
    <details className="assessment-help"><summary><CircleHelp size={16} aria-hidden="true"/>Cara membaca metrik<span className="sr-only"> {title}</span></summary><p data-testid={`metric-help-${id}`}>{detail}</p></details>
  </article>;
}

export function KeyMetrics({data}) {
  const m = data.metrics || {}, state = resultState(m);
  return <section className="assessment-kpis" aria-label="Tiga metrik utama">
    <MetricCard id="accuracy" icon={Mic} title="Ketepatan kata" value={m.accuracy} unit="%" percent
      interpretation={!isNumber(m.accuracy) ? 'Belum ada transkrip untuk dibandingkan.' : !state.audio ? 'Hasil transkripsi awal; perlu ditinjau pendamping.' : data.reviewed ? 'Berdasarkan transkrip yang sudah ditinjau.' : 'Berdasarkan transkripsi otomatis; dapat mengandung salah dengar mesin.'}
      detail="Dihitung dari 100% − WER, dengan nilai minimum 0%. WER menghitung kata tertukar, terlewat, dan tambahan. Ini bukan penilaian fonem. Ambang latihan backend adalah WER >20%, bukan norma usia."/>
    <MetricCard id="wpm" icon={BookOpen} title="Kecepatan membaca" value={m.wpm} unit="kata/menit"
      interpretation={isNumber(m.wpm) ? 'Dihitung dari seluruh durasi rekaman, termasuk waktu hening.' : 'Belum ada transkrip atau durasi rekaman yang memadai.'}
      detail="WPM rekaman = jumlah kata transkrip ÷ durasi rekaman dalam menit. Berbeda dari WPM ujaran pada detail kelancaran. Ambang <60 kata/menit adalah aturan latihan awal, bukan norma kemampuan berdasarkan usia."/>
    <MetricCard id="on_text_percent" icon={Eye} title="Tatapan di area teks" value={m.on_text_percent} unit="%" percent
      interpretation={!isNumber(m.on_text_percent) ? 'Belum ada sampel tatapan yang dapat dihitung.' : state.gaze ? 'Bagian dari sampel tatapan yang berada di area bacaan.' : 'Gambaran awal; kualitas tatapan belum memenuhi syarat.'}
      detail="Persentase sampel tatapan di area teks. Bukan persentase pemahaman atau fokus anak. Ambang <65% adalah aturan observasional; interpretasi juga memerlukan kalibrasi dan cakupan yang memadai."/>
  </section>;
}

function ReadingStat({label, value, unit = ''}) {
  return <div><dt>{label}</dt><dd>{isNumber(value) ? <>{numberLabel(value)} <small>{unit}</small></> : 'Belum tersedia'}</dd></div>;
}

export function MultimodalAnalysis({data}) {
  const m = data.metrics || {}, g = m.gaze || {}, f = m.multimodal || {}, state = resultState(m);
  return <section className="assessment-section" aria-labelledby="multimodal-heading">
    <div className="assessment-section-heading"><div><span className="assessment-kicker">DUA SUDUT PANDANG</span><h2 id="multimodal-heading">Suara dan tatapan saat membaca</h2></div><span className="assessment-tag">{state.combined ? '2 modalitas layak' : 'Data belum lengkap'}</span></div>
    <div className={`assessment-modalities ${state.combined ? 'connected' : ''}`}>
      <article className="assessment-modality audio"><header><h3><Mic size={22}/>Suara</h3><span className="assessment-status">{state.audio ? 'Layak digunakan' : 'Perlu ditinjau'}</span></header>
        <dl className="assessment-stat-list"><ReadingStat label="Ketepatan kata" value={m.accuracy} unit="%"/><ReadingStat label="Kecepatan rekaman" value={m.wpm} unit="kata/menit"/><div><dt>Kata tertukar / terlewat / tambahan</dt><dd>{numberLabel(m.substitutions)} / {numberLabel(m.deletions)} / {numberLabel(m.insertions)}</dd></div></dl>
        <p>{isNumber(m.fluency?.pause_frequency_per_min) ? `Jeda ujaran: ${numberLabel(m.fluency.pause_frequency_per_min)} jeda/menit.` : 'Jeda ujaran belum tersedia.'} {!data.reviewed && 'Perbedaan kata masih dapat berasal dari salah dengar mesin.'}</p>
      </article>
      <article className="assessment-modality gaze"><header><h3><Eye size={22}/>Tatapan</h3><span className="assessment-status">{state.gaze ? 'Layak digunakan' : 'Perlu ditinjau'}</span></header>
        <dl className="assessment-stat-list"><ReadingStat label="Di area teks" value={m.on_text_percent} unit="%"/><ReadingStat label="Fiksasi (tatapan menetap)" value={m.fixations} unit="kali"/><ReadingStat label="Kembali ke kata / baris sebelumnya" value={m.regressions} unit="kali"/></dl>
        <p>{state.gaze && g.longest_dwell?.length ? `Tatapan terlama: ${g.longest_dwell.slice(0, 3).map(w => w.word).join(', ')}.` : 'Kata dengan tatapan terlama belum dapat diinterpretasikan.'}</p>
      </article>
    </div>
    {state.combined ? <div className="assessment-fusion" data-testid="fusion-panel">
      <div className="assessment-fusion-icon"><Layers size={25} aria-hidden="true"/></div><div>
        <span className="assessment-kicker">TEMUAN GABUNGAN SUARA & TATAPAN</span>
        <h3 data-testid="fusion-pattern">{f.pattern || 'Pola gabungan belum tersedia'}</h3>
        <p>{f.speech_error_words === 0 ? 'Tidak ada kata tertukar atau terlewat pada transkripsi untuk dibandingkan dengan tatapan.' : f.concordant === true ? 'Kedua sumber data menandai sebagian kata yang sama untuk ditinjau bersama.' : f.concordant === false && isNumber(f.concordance) ? 'Ada perbedaan antara kata yang ditandai oleh suara dan tatapan. Tinjau masing-masing temuan bersama pendamping.' : 'Hubungan per kata belum cukup untuk menyimpulkan kesulitan yang sama.'}</p>
        {isNumber(f.concordance) && <p className="assessment-concordance" data-testid="fusion-concordance"><b>{numberLabel(f.concordance)}%</b> dari {f.speech_error_words} kata tertukar atau terlewat juga ditandai oleh tatapan.</p>}
        <details className="assessment-help"><summary>Lihat dasar temuan gabungan</summary><p>{f.explanation || 'Penjelasan belum tersedia.'}</p><p>Kecocokan adalah hubungan antar pengamatan pada sesi ini, bukan skor kemampuan atau probabilitas diagnosis.</p></details>
      </div>
    </div> : <div className="assessment-partial" data-testid="fusion-unavailable"><CircleHelp size={22}/><div><b>Temuan gabungan belum dapat ditampilkan</b><p>{state.audio ? 'Hanya suara yang memenuhi syarat kualitas. Kalibrasi ulang untuk melengkapi pengamatan tatapan.' : state.gaze ? 'Hanya tatapan yang memenuhi syarat kualitas. Tinjau transkripsi atau ulangi rekaman suara.' : 'Belum ada dua modalitas yang memenuhi syarat. Tinjau kualitas data sebelum menarik kesimpulan.'}</p></div></div>}
  </section>;
}

export function PracticeWords({data}) {
  const m = data.metrics || {}, state = resultState(m);
  const audio = state.audio ? (m.annotations || []).filter(w => ['substitute', 'delete'].includes(w.type)) : [];
  const gaze = state.gaze ? m.gaze?.longest_dwell || [] : [];
  const both = state.combined ? m.multimodal?.agreement_words || [] : [];
  return <section className="assessment-section" aria-labelledby="practice-words-heading">
    <h2 id="practice-words-heading">Kata yang perlu dilatih</h2><p className="assessment-intro">Pilih kata untuk mendengarkan contoh dan berlatih pelafalan. Pengamatan ini menjadi bahan diskusi bersama pendamping.</p>
    <div className="assessment-word-groups">
      {[[Layers, 'Suara & tatapan', both, 'both', 'Ditandai oleh kedua modalitas.'], [Mic, 'Berdasarkan suara', audio, 'audio', 'Kata tertukar atau terlewat pada transkripsi.'], [Eye, 'Perhatian visual lebih lama', gaze, 'gaze', 'Tatapan terlama; belum tentu berarti kesulitan.']].map(([Icon, title, words, kind, desc]) => <div className={`assessment-word-group ${kind}`} key={kind} data-testid={`word-group-${kind}`}><h3><Icon size={19}/>{title}</h3><p>{desc}</p><div className="assessment-word-links">{words.length ? words.map((w, i) => <Link key={`${w.index}-${i}`} to={`/pronunciation?word=${encodeURIComponent(w.word)}`} data-testid={kind === 'both' ? `agreement-word-${w.index}` : undefined}><span>{w.word}</span><ArrowRight size={15} aria-hidden="true"/></Link>) : <span className="assessment-no-words">{kind === 'both' && !state.combined ? 'Menunggu dua modalitas yang layak.' : kind === 'audio' && !state.audio ? 'Menunggu suara yang layak.' : kind === 'gaze' && !state.gaze ? 'Menunggu tatapan yang layak.' : 'Belum ada kata yang ditandai.'}</span>}</div></div>)}
    </div>
  </section>;
}

export function FluencyDetails({fluency}) {
  return <section className="assessment-section" aria-labelledby="fluency-heading">
    <h2 id="fluency-heading">Detail kelancaran membaca</h2><p className="assessment-intro">Dari audio dan transkrip otomatis asli. Nilai ini tetap menggunakan transkrip asli setelah koreksi pendamping.</p>
    <div className="assessment-fluency">{FLUENCY_FIELDS.map(([key, title, unit, term, definition]) => <article key={key}>
      <h3>{title}</h3><div className="assessment-fluency-value" data-testid={`fluency-${key}`}>{isNumber(fluency?.[key]) ? numberLabel(fluency[key], 2) : 'Belum tersedia'}</div><p>{unit}</p>
      <details className="assessment-help"><summary>{term}</summary><p>{definition}</p></details>
    </article>)}</div>
    <p className="assessment-footnote">Suku kata adalah perkiraan dari huruf vokal bahasa Indonesia, sehingga diftong, singkatan, dan kata serapan dapat berbeda dari pengucapan sebenarnya.</p>
    {!!fluency?.qc_flags?.length && <details className="assessment-help"><summary>Catatan kualitas kelancaran ({fluency.qc_flags.length})</summary><p>{fluency.qc_flags.join(', ')}</p></details>}
  </section>;
}

function PracticeCard({icon: Icon = Target, title, goal, instruction, to, onClick, label, testId}) {
  return <article><Icon size={26}/><h3>{title}</h3><p><b>Tujuan:</b> {goal}</p><p data-testid={testId}>{instruction}</p>
    {to ? <Link to={to} className="assessment-link">{label}<ArrowRight size={17}/></Link> : <button type="button" className="assessment-link" onClick={onClick}>{label}<ArrowRight size={17}/></button>}
  </article>;
}

export function Recommendations({data, onReview}) {
  const practice = practiceFor(data.profile);
  return <section className="assessment-section" aria-labelledby="practice-heading"><h2 id="practice-heading">Langkah latihan berikutnya</h2>
    <div className="assessment-practices"><PracticeCard {...practice} instruction={data.recommendations?.[0] || 'Tinjau hasil bersama pendamping sebelum memilih latihan.'} testId="recommendation-0" label="Buka latihan"/>
      <article><Gamepad2 size={26}/><h3>Bermain bersama CORTI</h3><p><b>Tujuan:</b> Menjaga pengalaman belajar tetap menyenangkan.</p><p>Pilih aktivitas di Game Center bersama pendamping dan berlatih sesuai kenyamanan anak.</p><Link to="/games" className="assessment-link" data-testid="result-games">Pilih permainan <ArrowRight size={17}/></Link></article>
    </div>
    {data.recommendations?.length > 1 && <details className="assessment-help assessment-extra-advice"><summary>Langkah tambahan dari sesi ini ({data.recommendations.length - 1})</summary><div className="assessment-practices">{data.recommendations.slice(1).map((r, i) => {
      // Choose an existing action for the backend's recommendation; no assessment thresholds here.
      const text = r.toLowerCase();
      const action = /transkrip|koreksi/.test(text) ? {title: 'Tinjau transkripsi', goal: 'Memastikan ucapan terbaca dengan benar oleh sistem.', onClick: onReview, label: 'Lihat transkripsi', icon: Mic}
        : /kalibrasi|cakupan|perbesar|penunjuk/.test(text) ? {title: 'Siapkan pengamatan tatapan', goal: 'Membantu pengamatan visual pada sesi berikutnya.', to: '/reading?mode=gaze', label: 'Siapkan sesi tatapan', icon: Eye}
        : /kata|pelafalan/.test(text) ? {title: 'Berlatih kata pilihan', goal: 'Mengenali bunyi kata yang ditandai pada sesi ini.', to: '/pronunciation', label: 'Buka pelafalan', icon: Mic}
        : {title: 'Coba sesi membaca berikutnya', goal: 'Melengkapi pengamatan bersama pendamping.', to: '/reading', label: 'Mulai sesi baru', icon: BookOpen};
      return <PracticeCard key={i} {...action} instruction={r} testId={`recommendation-${i + 1}`}/>;
    })}</div></details>}
  </section>;
}

export function Methodology({data}) {
  const m = data.metrics || {};
  return <section className="assessment-section assessment-methodology" aria-labelledby="methodology-heading">
    <h2 id="methodology-heading"><ShieldCheck size={24}/>Kualitas data & metodologi</h2>
    <details><summary>Kualitas suara, transkripsi, dan kalibrasi</summary><div className="assessment-detail-body">
      <ul data-testid="quality-reasons">{(data.quality_reasons || []).map(r => <li key={r}>{r}</li>)}</ul>
      <dl className="assessment-stat-list"><ReadingStat label="Keyakinan transkripsi otomatis" value={m.asr_confidence} unit="%"/><ReadingStat label="Cakupan sampel tatapan" value={m.gaze_coverage} unit="%"/></dl>
      <p>Kalibrasi: {m.calibration_valid === true ? 'memenuhi syarat' : 'belum memenuhi syarat / belum tersedia'}.</p><p>Keyakinan transkripsi berasal dari model pengenal suara; bukan keyakinan profil membaca.</p>
      {(data.speech_error || m.speech_error) && <p>Catatan audio: {data.speech_error || m.speech_error}</p>}
    </div></details>
    <details><summary>Verifikasi pendamping & dasar pengamatan</summary><div className="assessment-detail-body">
      <p data-testid="review-status"><CheckCircle2 size={17}/>{data.reviewed ? 'Transkripsi sudah ditinjau pendamping.' : 'Transkripsi otomatis belum ditinjau pendamping.'}</p>
      <p data-testid="profile-method">{data.profile_method || 'Informasi metode belum tersedia.'}</p><p data-testid="profile-reason">{data.profile_reason || 'Dasar profil belum tersedia.'}</p><p>Ambang latihan adalah aturan observasional awal, bukan norma kemampuan berdasarkan usia. Tidak ada probabilitas profil atau diagnosis yang dihitung.</p>
      <p>Metode kelancaran: {m.fluency?.method_version || 'Belum tersedia'}. Sumber transkrip: {m.fluency?.transcript_source || 'Belum tersedia'}.</p>
    </div></details>
    <details><summary data-testid="limitations-toggle">Batasan interpretasi</summary><div className="assessment-detail-body"><ul>{(data.limitations || []).map(l => <li key={l}>{l}</li>)}</ul><p>Hasil penelitian ETDD70 dan TURead bukan prediksi individual pada halaman ini. Hasil ini adalah pengamatan sesi, bukan diagnosis klinis.</p></div></details>
  </section>;
}
