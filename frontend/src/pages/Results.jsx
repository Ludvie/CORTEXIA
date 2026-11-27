import {useState, useEffect} from 'react';
import {useParams, Link} from 'react-router-dom';
import {Download, ArrowRight, ShieldCheck, Mic, Eye, CalendarDays, BookOpen, UserRound, Sparkles} from 'lucide-react';
import {toast} from 'sonner';
import {api, message, dateLabel} from '../lib/api';
import {useAuth} from '../components/Auth';
import {Action, Back, Loading, Empty} from '../components/Common';
import {KeyMetrics, MultimodalAnalysis, PracticeWords, FluencyDetails, Recommendations, Methodology} from '../components/results/AssessmentOverview';
import {ResultsDetails} from '../components/results/ResultsDetails';
import {resultState, practiceFor, profileExplanation} from '../components/results/resultPresentation';
import './Results.css';

const TABS = [['overview', 'Ringkasan'], ['speech', 'Kata & transkripsi'], ['gaze', 'Jejak tatapan'], ['details', 'Detail sesi']];
const QUALITY = {layak: 'Data layak', parsial: 'Data parsial', tidak_cukup: 'Data belum cukup'};

export default function Results() {
  const {id} = useParams(), {user} = useAuth();
  const [data, setData] = useState(null), [error, setError] = useState('');
  const [loading, setLoading] = useState(true), [retry, setRetry] = useState(0);
  const [tab, setTab] = useState('overview'), [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false), [downloading, setDownloading] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(''); setData(null); setEditing(false); setTab('overview');
    api.get(`/sessions/${id}`).then(r => {if (active) setData(r.data);})
      .catch(e => {if (active) setError(message(e));})
      .finally(() => {if (active) setLoading(false);});
    return () => {active = false;};
  }, [id, retry]);

  const download = async () => {
    setDownloading(true);
    try {
      const r = await api.get(`/sessions/${id}/report`, {responseType: 'blob'});
      const url = URL.createObjectURL(r.data), a = document.createElement('a');
      a.href = url; a.download = `CORTEXIA-${id.slice(0, 8)}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {toast.error(message(e));} finally {setDownloading(false);}
  };
  const review = async e => {
    e.preventDefault(); setBusy(true);
    try {
      const r = await api.patch(`/sessions/${id}/review`, Object.fromEntries(new FormData(e.target)));
      setData(r.data); setEditing(false); toast.success('Transkripsi dan metrik diperbarui.');
    } catch (e) {toast.error(message(e));} finally {setBusy(false);}
  };
  const onTabKey = e => {
    const current = TABS.findIndex(([key]) => key === tab);
    const next = {ArrowRight: (current + 1) % TABS.length, ArrowLeft: (current + TABS.length - 1) % TABS.length, Home: 0, End: TABS.length - 1}[e.key];
    if (next === undefined) return;
    e.preventDefault(); setTab(TABS[next][0]);
    document.getElementById(`assessment-tab-${TABS[next][0]}`)?.focus();
  };
  const dashboard = user?.role === 'teacher' ? '/teacher' : '/progress';
  if (loading) return <div className="page assessment-results" role="status"><Loading/></div>;
  if (error) return <div className="page assessment-results"><Back to={dashboard}/><div role="alert"><h1>Hasil belum dapat dimuat</h1><p data-testid="results-error">{error}</p></div><Action onClick={() => setRetry(v => v + 1)}>Coba lagi</Action></div>;
  if (!data || !data.metrics) return <div className="page assessment-results"><Back to={dashboard}/><Empty icon={BookOpen} title="Hasil asesmen belum tersedia">Sesi ini belum memiliki hasil analisis. Kembali ke dashboard untuk memeriksa sesi.</Empty></div>;
  const m = data.metrics, state = resultState(m), practice = practiceFor(data.profile);
  return <div className="page assessment-results">
    <Back to={dashboard} text="Kembali ke dashboard"/>
    <header className="assessment-header">
      <div><span className="assessment-kicker">CORTEXIA · PENGAMATAN SESI</span><h1 data-testid="result-heading">Hasil Asesmen Membaca</h1>
        <div className="assessment-meta" data-testid="result-session-info"><span><UserRound size={17}/>{data.student_alias || 'Peserta'}</span><span><BookOpen size={17}/>{data.text_title || 'Bacaan'}</span><span><CalendarDays size={17}/>{data.created_at ? dateLabel(data.created_at) : 'Tanggal belum tersedia'}</span></div>
      </div><div className="assessment-header-actions"><span className={`assessment-quality ${data.quality || ''}`} data-testid="quality-badge"><ShieldCheck size={16}/>{QUALITY[data.quality] || 'Kualitas belum tersedia'}</span><Action kind="ghost" data-testid="download-report" onClick={download} busy={downloading}><Download size={18}/>Unduh PDF</Action></div>
    </header>
    <p className="assessment-disclaimer"><ShieldCheck size={18}/>Hasil ini bukan diagnosis klinis. Tinjau temuan bersama guru atau pendamping.</p>
    <section className="assessment-profile" aria-labelledby="profile-heading">
      <div className="assessment-profile-main"><span className="assessment-kicker"><Sparkles size={16}/>RINGKASAN MEMBACA</span><h2 id="profile-heading" data-testid="result-profile">{data.profile || 'Profil belum tersedia'}</h2>
        <p>{profileExplanation(m)}</p>
        <div className="assessment-sources" aria-label="Modalitas yang berkontribusi"><span className={state.audio ? 'valid' : ''}><Mic size={16}/>Suara: {state.audio ? 'digunakan' : 'belum layak'}</span><span className={state.gaze ? 'valid' : ''}><Eye size={16}/>Tatapan: {state.gaze ? 'digunakan' : 'belum layak'}</span></div>
      </div><div className="assessment-profile-action"><span>Mulai dari satu langkah kecil</span><Link to={practice.to} className="action" data-testid="adaptive-next-practice">Lanjutkan latihan<ArrowRight size={18}/></Link><small>Latihan sesuai pengamatan sesi ini.</small></div>
    </section>
    {!!data.analysis_warnings?.length && <div className="assessment-warning" role="status">{data.analysis_warnings.join(' ')}</div>}
    <KeyMetrics data={data}/>
    <div className="assessment-tabs" role="tablist" aria-label="Bagian hasil asesmen" onKeyDown={onTabKey}>
      {TABS.map(([key, label]) => <button type="button" role="tab" key={key} id={`assessment-tab-${key}`} aria-controls={`assessment-panel-${key}`} aria-selected={tab === key} tabIndex={tab === key ? 0 : -1} data-testid={`result-tab-${key}`} onClick={() => setTab(key)}>{label}</button>)}
    </div>
    {TABS.map(([key]) => <div key={key} id={`assessment-panel-${key}`} role="tabpanel" aria-labelledby={`assessment-tab-${key}`} tabIndex={0} hidden={tab !== key}>
      {tab === key && (key === 'overview' ? <><MultimodalAnalysis data={data}/><PracticeWords data={data}/><FluencyDetails fluency={m.fluency}/><Recommendations data={data} onReview={() => {setTab('speech'); document.getElementById('assessment-tab-speech')?.focus();}}/><Methodology data={data}/></> : <>
        {key === 'speech' && <FluencyDetails fluency={m.fluency}/>}
        <ResultsDetails tab={key} data={data} user={user} editing={editing} setEditing={setEditing} busy={busy} review={review}/>
        {key === 'details' && <Methodology data={data}/>}
      </>)}
    </div>)}
  </div>;
}
