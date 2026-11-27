"""Source-directed integration, independent of TTS fixtures and other tests' state."""
from common import *
import io,secrets,statistics,wave
import pytest,requests,numpy as np

@pytest.fixture(scope='module')
def context():
    base=os.getenv('REACT_APP_BACKEND_URL')
    if not base:pytest.skip('Dedicated test API unavailable')
    api=base+'/api';clients=[]
    for _ in range(2):
        c=requests.Session()
        response=c.post(api+'/auth/register',json=dict(name='Synthetic QA',email='qa-'+secrets.token_hex(8)+'@example.com',password=secrets.token_urlsafe(18),role='teacher'),timeout=30)
        response.raise_for_status();c.headers['Authorization']='Bearer '+response.json()['token'];clients.append(c)
    student=clients[0].post(api+'/students',json=dict(alias='Synthetic Reader',grade=2),timeout=30).json()
    text=clients[0].post(api+'/texts',json=dict(title='Fixture assessment',content='Sepulang sekolah Fitri sangat lapar. Sepulang sekolah Fitri sangat lapar.',level=2),timeout=30).json()
    sample=ROOT/'backend/tests/fixtures/bookbot_sample.wav';buffer=io.BytesIO()
    with wave.open(str(sample),'rb') as source,wave.open(buffer,'wb') as dest:
        dest.setparams(source.getparams());dest.writeframes(source.readframes(source.getnframes())*2)
    payload=dict(student_id=student['id'],text_id=text['id'],mode='multimodal',consent=True,duration=7.427,gaze_points=[dict(x=.5,y=.5,t=i/10) for i in range(74)],calibration=dict(passed=True,validation_samples=40,median_error=.08))
    response=clients[0].post(api+'/sessions',data=dict(payload=json.dumps(payload)),files=dict(audio=('fixture.wav',buffer.getvalue())),timeout=90);response.raise_for_status()
    yield api,clients,response.json(),payload,buffer.getvalue()
    for c in clients:c.post(api+'/auth/logout',timeout=15);c.close()

def test_cross_owner_session_and_report_isolation(context):
    api,clients,doc,_,_=context
    for suffix in ['', '/report']:
        assert clients[1].get(api+'/sessions/'+doc['id']+suffix,timeout=30).status_code==404
    assert clients[1].patch(api+'/sessions/'+doc['id']+'/review',json=dict(transcript='saya baca buku'),timeout=30).status_code==404

def test_full_audio_gaze_fluency_persistence_review_pdf(context):
    api,clients,doc,_,_=context;c=clients[0]
    loaded=c.get(api+'/sessions/'+doc['id'],timeout=30).json()
    assert loaded['metrics']['fluency']==doc['metrics']['fluency']
    assert loaded['metrics']['fluency']['wpm'] is not None
    assert loaded['metrics']['gaze_usable'] and loaded['metrics']['speech_reliable']
    assert loaded['metrics']['multimodal']['multimodal_complete']
    reviewed=c.patch(api+'/sessions/'+doc['id']+'/review',json=dict(transcript='saya baca buku'),timeout=30).json()
    assert reviewed['metrics']['fluency']==loaded['metrics']['fluency']
    assert reviewed['metrics']['gaze']==loaded['metrics']['gaze']
    assert reviewed['reviewed'] and reviewed['metrics']['wer_source']=='transkrip_manual'
    pdf=c.get(api+'/sessions/'+doc['id']+'/report',timeout=30)
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')

def test_end_to_end_http_database_performance(context):
    api,clients,_,payload,audio=context;durations=[]
    for i in range(5):
        start=time.perf_counter()
        response=clients[0].post(api+'/sessions',data=dict(payload=json.dumps(payload)),files=dict(audio=('fixture.wav',audio)),timeout=90)
        durations.append((time.perf_counter()-start)*1000)
        assert response.status_code==200
    csvout('08_nonfunctional/end_to_end_performance.csv',[dict(operation='HTTP upload + decode + ASR + VAD + gaze + fusion + MongoDB save',audio_sec=7.427,n=5,mean_ms=statistics.mean(durations),median_ms=statistics.median(durations),p95_ms=float(np.percentile(durations,95)),status='PASSED')])
