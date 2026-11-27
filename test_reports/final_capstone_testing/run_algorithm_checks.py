from common import *
import copy, io, itertools, math, statistics, wave, zipfile
from unittest.mock import patch
import numpy as np
import analytics as a
import fluency as f
import pronunciation as pr
from cfg_tools import CFG
from quality_gate_fragment import quality_gate_classification
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

records=[]
def check(section,case,inputs,expected,operation,unit=''):
    started=time.perf_counter()
    try:
        actual=operation()
        equal=np.allclose(actual,expected,rtol=0,atol=1e-5) if isinstance(actual,(float,int)) and isinstance(expected,(float,int)) else actual==expected
        status='PASSED' if equal else 'FAILED'
    except Exception as e:actual=type(e).__name__+': '+str(e);status='FAILED'
    row=dict(section=section,case_id=case,input=json.dumps(inputs,ensure_ascii=False,default=str),expected=json.dumps(expected,ensure_ascii=False,default=str),actual=json.dumps(actual,ensure_ascii=False,default=str),unit=unit,status=status,elapsed_ms=(time.perf_counter()-started)*1000)
    records.append(row);return actual

CAL=dict(passed=True,median_error=.08,validation_samples=40)
def pts(n=24,dt=.125,x=.5):return [dict(x=x,y=.5,t=round(i*dt,6)) for i in range(n)]
def words(prob=.9):return [dict(word=w,start=i,end=i+.4,probability=prob) for i,w in enumerate('saya baca buku'.split())]
def gd(seq):return [[x,y,t,x/800,y/400] for x,y,t in seq]
def graph_cases():
    cfg=CFG(a._idt)
    specifications=[('empty',[],[]),('single',[(400,200,0)],[]),('short',[(400,200,0),(400,200,.119)],[]),
      ('exact120',[(400,200,0),(400,200,.12)],[120.0]),('extended',[(400,200,0),(400,200,.12),(400,200,.3)],[300.0]),
      ('disp80',[(400,200,0),(480,200,.06),(400,200,.12)],[120.0]),('disp81',[(400,200,0),(481,200,.06),(400,200,.12)],[]),
      ('gap500',[(400,200,0),(400,200,.5)],[500.0]),('gap501',[(400,200,0),(400,200,.501)],[]),
      ('twofix',[(100,200,0),(100,200,.12),(700,200,.2),(700,200,.32)],[120.,120.]),
      ('discard_then_fix',[(100,200,0),(700,200,.05),(700,200,.17)],[120.])]
    for name,points,expected in specifications:
        check('03_eye_tracking','IDT_'+name,points,expected,lambda: [v['d'] for v in cfg.run('IDT_'+name,(gd(points),),expected,lambda r:[v['d'] for v in r])],'ms')
    qcfg=CFG(quality_gate_classification)
    for speech,gaze in itertools.product([False,True],repeat=2):
        expected='layak' if speech and gaze else 'parsial' if speech or gaze else 'tidak_cukup'
        case=f'Q_{int(speech)}{int(gaze)}'
        check('07_multimodal_fusion',case,dict(speech=speech,gaze=gaze),expected,lambda:qcfg.run(case,(speech,gaze),expected))
        actual=a.analyze('saya baca buku','saya baca buku' if speech else '',10,pts(80) if gaze else [],CAL,words())
        check('07_multimodal_fusion',case+'_production',dict(speech=speech,gaze=gaze),expected,lambda:actual['quality'])
    fusioncfg=CFG(a.fuse)
    ref=' '.join('kata'+str(i) for i in range(10))
    patterns=['Kesulitan pengenalan kata (didukung suara dan tatapan)','Kesalahan ucap dan alur visual tidak teratur (belum pada kata yang sama)','Kesalahan ucap tanpa hambatan visual yang jelas','Bacaan lambat dengan alur visual tidak teratur','Bacaan lambat tanpa hambatan visual yang jelas','Alur visual tidak teratur meski ucapan tepat','Suara dan tatapan sama-sama lancar']
    for idx,(reliable,gaze,wer,wpm,reg,shared) in enumerate(itertools.product([False,True],[False,True],[20,20.01],[59.99,60],[40,40.01],[0,2,3])):
        errors=set(range(5));hard=set(range(shared));con=100*shared/5 if reliable and gaze else None
        m=dict(accuracy=100-wer,wer=wer,wpm=wpm,gaze_usable=gaze,on_text_percent=90,
          annotations=[dict(index=i,type='delete',word='kata'+str(i)) for i in errors],gaze=dict(words=[dict(index=i,ms=100,visits=2 if i in hard else 1) for i in range(10)],regression_rate=reg,skipped_words_percent=0))
        basis='suara + tatapan' if reliable and gaze else 'suara saja' if reliable else 'tatapan saja' if gaze else 'tidak ada'
        pattern=None
        if reliable and gaze:
            pattern=patterns[0 if wer>20 and con>=40 else 1 if wer>20 and reg>40 else 2 if wer>20 else 3 if wpm<60 and reg>40 else 4 if wpm<60 else 5 if reg>40 else 6]
        expected=dict(basis=basis,concordance=con,pattern=pattern)
        project=lambda o:{k:o[k] for k in expected}
        check('07_multimodal_fusion',f'F_{idx:03}',dict(speech=reliable,gaze=gaze,wer=wer,wpm=wpm,regression=reg,shared=shared),expected,
              lambda:fusioncfg.run(f'F_{idx:03}',(ref,m,reliable),expected,project) and project(a.fuse(ref,m,reliable)))
    # Additional structural paths: absent data, zero denominator, dwell and acoustic support.
    for name,m,reliable,expected in [
      ('absent',dict(accuracy=None,gaze_usable=False,gaze=None),False,dict(basis='tidak ada',concordance=None)),
      ('zero_errors',dict(accuracy=100,wer=0,wpm=80,gaze_usable=True,gaze=dict(words=[])),True,dict(basis='suara + tatapan',concordance=None)),
      ('one_gaze_word',dict(accuracy=100,wer=0,wpm=80,gaze_usable=True,gaze=dict(words=[dict(index=0,ms=100,visits=1)])),True,dict(basis='suara + tatapan',concordance=None)),
      ('dwell',dict(accuracy=70,wer=30,wpm=80,gaze_usable=True,annotations=[dict(index=0,type='delete')],gaze=dict(words=[dict(index=i,ms=150 if i==0 else 100,visits=1) for i in range(10)])),True,dict(basis='suara + tatapan',concordance=100.))]:
        project=lambda o:{k:o[k] for k in expected}
        check('07_multimodal_fusion','F_'+name,m,expected,lambda:fusioncfg.run('F_'+name,(ref,m,reliable),expected,project) and project(a.fuse(ref,m,reliable)))
    for name,overrides in [('outside',dict(on_text_percent=64.99)),('skipped',dict(gaze=dict(words=[],skipped_words_percent=50.01)))]:
        m=dict(accuracy=100,wer=0,wpm=80,gaze_usable=True,on_text_percent=90,gaze=dict(words=[]));m.update(overrides)
        expected=patterns[5]
        check('07_multimodal_fusion','F_'+name,m,expected,lambda:fusioncfg.run('F_'+name,(ref,m,True),expected,lambda o:o['pattern'])['pattern'])
    complexities=[];basis=[]
    for numerator in [399,400,401]:
        reference=' '.join('w'+str(i) for i in range(1000))
        m=dict(accuracy=70,wer=30,wpm=80,gaze_usable=True,annotations=[dict(index=i,type='delete') for i in range(1000)],gaze=dict(words=[dict(index=i,ms=100,visits=2 if i<numerator else 1) for i in range(1000)]))
        check('07_multimodal_fusion',f'F_exact_boundary_{numerator}',dict(error_words=1000,shared_words=numerator),[numerator/10,numerator>=400],lambda:[a.fuse(reference,m,True)['concordance'],a.fuse(reference,m,True)['concordant']])
    for graph in [cfg,qcfg,fusioncfg]:
        comp,paths=graph.export();complexities.append(comp);basis+=paths
    csvout('01_whitebox/cyclomatic_complexity.csv',complexities)
    csvout('01_whitebox/basis_path_testing.csv',basis)

def quality_eye():
    for err,passed,n in itertools.product([.159,.16,.161,None,float('nan')],[False,True],[14,15]):
        cal=dict(median_error=err,passed=passed,validation_samples=n)
        expected=passed and err is not None and math.isfinite(err) and err<=.16 and n>=15
        check('03_eye_tracking',f'cal_{len(records)}',cal,expected,lambda:a.calibration_ok(cal))
    for dur,n,expected in [(10,23,False),(10,24,True),(2,19,False),(2,20,True),(0,24,False)]:
        check('03_eye_tracking',f'coverage_{dur}_{n}',dict(duration=dur,samples=n),expected,lambda:a.gaze_metrics(pts(n,.05),dur,CAL)['gaze_usable'])
    dirty=[dict(x=.5,y=.5,t=.2),dict(x=.5,y=.5,t=.1),dict(x=.5,y=.5,t=.1),dict(x=float('nan'),y=.5,t=.3),dict(x=.5,y=.5,t=-1),dict(x=.5,y=.5,t=9)]
    check('03_eye_tracking','clean_dirty','duplicate, NaN, negative/out-of-range time',dict(valid=2,duplicates=1,invalid=2,out_of_range=1),lambda:{k:a.clean_gaze(dirty,1)[1][k] for k in ['valid','duplicates','invalid','out_of_range']})
    boxes=[dict(i=i,text='kata'+str(i),x=x,y=.45,w=.1,h=.1,line=0) for i,x in enumerate([.05,.45,.75])]
    layout=dict(t=0,width=900,height=500,words=boxes)
    points=[dict(x=x,y=.5,t=i/10) for i,x in enumerate([.1]*10+[.8]*10+[.1]*10)]
    g=a.gaze_metrics(points,3,CAL,[layout])['gaze']
    check('03_eye_tracking','mapped_revisit',dict(sequence=[0,2,0],unvisited=[1]),dict(regressions_within_line=1,progressions=1,revisited_words=1,skipped_words_percent=33.3),lambda:{k:g[k] for k in ['regressions_within_line','progressions','revisited_words','skipped_words_percent']})
    for width,expected in [(800,1),(2000,0)]:
        p=[dict(x=.5+(i%2)*.05,y=.5,t=i*.05) for i in range(25)]
        check('03_eye_tracking',f'viewport_{width}',dict(width=width,jitter=.05),expected,lambda:len(a.fixations_idt(p,width,400)))
    for dur,prob,review,expected in [(4.99,.9,False,False),(5,.6,False,True),(5,.599,False,False),(5,None,False,False),(5,None,True,True)]:
        check('07_multimodal_fusion',f'speech_gate_{dur}_{prob}_{review}',dict(duration=dur,probability=prob,reviewed=review),expected,lambda:a.speech_metrics('saya baca buku','saya baca buku',dur,words(prob),review)[3])
    fig,ax=plt.subplots(figsize=(8,3));ax.plot([p['t'] for p in points],[p['x'] for p in points],'.-');ax.set(xlabel='Waktu (s)',ylabel='x ternormalisasi',title='Fixture sintetis: maju dan kembali ke kata pertama');fig.tight_layout();fig.savefig(OUT/'03_eye_tracking/fixation_visualization.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3))
    for b in boxes:ax.add_patch(plt.Rectangle((b['x'],b['y']),b['w'],b['h'],fill=False));ax.text(b['x'],.6,b['text'])
    ax.scatter([p['x'] for p in points],[p['y'] for p in points],s=60,color='#bc4b16');ax.set(xlim=(0,1),ylim=(.3,.8),title='Pemetaan sintetis; kata tengah tidak tertatap');fig.savefig(OUT/'03_eye_tracking/gaze_mapping_visualization.png',dpi=160);plt.close(fig)

def vad_fluency():
    import webrtcvad
    class MaskVad:
        modes=[]
        def __init__(self,mode):self.modes.append(mode)
        def is_speech(self,frame,rate):
            assert rate==16000 and len(frame)==640
            return bool(frame[0])
    for name,mask,expected in [('empty',[],[]),('40ms',[1]*2,[]),('60ms',[1]*3,[(0.,.06)]),('fill100',[1]*3+[0]*5+[1]*3,[(0.,.22)]),('gap120',[1]*3+[0]*6+[1]*3,[(0.,.06),(.18,.24)])]:
        with patch.object(webrtcvad,'Vad',MaskVad):
            check('02_vad','VAD_'+name,mask,expected,lambda:f.segments(b''.join(bytes([v])*640 for v in mask)))
    check('02_vad','VAD_mode_reset','Five calls create five VAD instances', [2]*5,lambda:MaskVad.modes)
    rng=np.random.default_rng(42)
    waveforms={'silence':np.zeros(32000,dtype=np.int16),'noise':rng.normal(0,500,32000).astype(np.int16)}
    real=pr.decode_pcm(str(ROOT/'backend/tests/fixtures/bookbot_sample.wav'));waveforms['public_speech_fixture']=np.frombuffer(real,dtype=np.int16)
    desc=[];gaps=[]
    for name,pcm in waveforms.items():
        seg=f.segments(pcm.tobytes());pause=[c-b for (_,b),(c,_) in zip(seg,seg[1:]) if c-b>=.25-2e-6];gaps+=pause
        desc.append(dict(source=name,duration_sec=len(pcm)/16000,active_sec=sum(b-a for a,b in seg),segments=len(seg),pauses=len(pause),precision='',recall='',f1='',boundary_error_ms='',status='PASSED' if name=='silence' and not seg else 'NOT APPLICABLE',interpretation='Descriptive; no independent speech boundary annotations'))
        check('02_vad','valid_boundaries_'+name,name,True,lambda:all(0<=s<e<=len(pcm)/16000 for s,e in seg))
    check('02_vad','silence_no_segments','digital zero PCM',[],lambda:f.segments(waveforms['silence'].tobytes()))
    # Speech-in-silence is an independently known insertion window, not a phonetic boundary annotation.
    inserted=np.concatenate([np.zeros(8000,dtype=np.int16),waveforms['public_speech_fixture'],np.zeros(8000,dtype=np.int16)])
    seg=f.segments(inserted.tobytes())
    fig,ax=plt.subplots(figsize=(10,3));ax.plot(np.arange(len(inserted))/16000,inserted/32768,lw=.5)
    for s,e in seg:ax.axvspan(s,e,color='#8173ba',alpha=.25)
    ax.set(xlabel='Waktu (s)',ylabel='Amplitudo',title='Fixture suara publik + hening; arsiran = prediksi VAD');fig.tight_layout();fig.savefig(OUT/'02_vad/vad_waveform.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,3));ax.hist(gaps,bins=8) if gaps else ax.text(.5,.5,'Tidak ada jeda >=250 ms pada fixture uji',ha='center');ax.set(xlabel='Durasi jeda (s)',ylabel='Jumlah',title='Jeda VAD fixture nyata (deskriptif)');fig.tight_layout();fig.savefig(OUT/'02_vad/vad_pause_distribution.png',dpi=160);plt.close(fig)
    csvout('02_vad/vad_metrics.csv',desc)
    csvout('02_vad/manual_validation_template.csv',[dict(audio_id='PUBLIC_FIXTURE',annotator_id='',segment_start_sec='',segment_end_sec='',label_speech_or_silence='',boundary_tolerance_ms='',notes='Isi independen; jangan salin prediksi VAD')])
    definitions=[]
    for pause in [.24,.25,.499,.5]:
        regions=[(.5,1),(1+pause,1.5+pause)];span=1+pause
        worddata=[dict(word='saya',start=.5,end=1),dict(word='baca',start=1+pause,end=1.5+pause)]
        npause=int(pause>=.25);runs=npause+1
        expected=dict(wpm=round(120/span,6),articulation_rate_syllables_per_sec=4.,mlr_syllables_per_run=4/runs,pause_frequency_per_min=round(60*npause/span,6),mean_pause_duration_sec=round(pause,6) if npause else None,long_pause_count=int(pause>=.5))
        with patch.object(f,'segments',lambda _:regions):
            actual=f.measure(bytes(96000),'saya baca',worddata)
            check('06_fluency',f'formula_pause_{pause}',dict(regions=regions,words=2,syllables=4),expected,lambda:{k:actual[k] for k in expected})
            for k,v in expected.items():definitions.append(dict(case_id=f'pause_{pause}',metric=k,expected=v,actual=actual[k],status='PASSED' if v==actual[k] else 'FAILED'))
    with patch.object(f,'segments',lambda _:[(.5,2)]):
        for name,text,wd in [('mismatch','saya',[dict(word='baca',start=.5,end=1)]),('zero_time','saya',[dict(word='saya',start=1,end=1)]),('out_of_range','saya',[dict(word='saya',start=1,end=5)]),('absent','',[])]:
            check('06_fluency',name,wd,None,lambda:f.measure(bytes(96000),text,wd)['wpm'])
    with patch.object(f,'segments',lambda _:[(.5,2)]):
        check('06_fluency','no_pause_null','continuous speech',None,lambda:f.measure(bytes(96000),'saya baca',[dict(word='saya',start=.5,end=1),dict(word='baca',start=1,end=2)])['mean_pause_duration_sec'])
        legacy=a.speech_metrics('saya baca','saya baca',3,[])[0]['wpm']
        check('06_fluency','legacy_vs_utterance',dict(words=2,recording=3,span=1.5),[40.,80.],lambda:[legacy,f.measure(bytes(96000),'saya baca',[dict(word='saya',start=.5,end=1),dict(word='baca',start=1,end=2)])['wpm']])
    csvout('06_fluency/fluency_formula_validation.csv',definitions)

def pronunciation_checks():
    for a1,b,cost in [('p','b',.3),('i','e',.4),('i','u',.7),('m','n',.5),('t','s',.6),('l','r',.4),('a','p',1),('p','p',0),('!','?',1)]:
        check('05_pronunciation','cost_'+a1+b,[a1,b],cost,lambda:pr.substitution_cost(a1,b))
    for a1,b,expected in [('baku','paku',.3),('ban','bang',.5),('akil','aqil',0),('sapi','sapi',0)]:
        check('05_pronunciation','distance_'+a1+b,[a1,b],expected,lambda:pr.phonetic_distance(a1,b))
    for score,expected in [(None,None),(0,'latihan'),(59.99,'latihan'),(60,'hampir'),(84.99,'hampir'),(85,'tepat'),(100,'tepat')]:
        check('05_pronunciation','verdict_'+str(score),score,expected,lambda:pr.verdict_for(score))
    for label,free,forced,vocab,competitors,score in [('target','apel','apel',['apel','apes'],['apes'],87.),('competitor','apes','apes',['apel','apes'],['apes'],26.2),('oov','apel','apel',[],[],100.),('no_competitor','apel','apel',['apel'],[],100.),('no_speech','','',['apel'],[],None)]:
        def recognize(pcm,grammar=None):return [dict(word=forced if grammar else free,conf=.8,start=0,end=.5)] if free else []
        with patch.object(pr,'decode_pcm',lambda _:b'\x10\x00'*16000),patch.object(pr,'_load',lambda:None),patch.object(pr,'_vocab',vocab),patch.object(pr,'competitors',lambda *args,**kwargs:competitors),patch.object(pr,'recognize',recognize):
            check('05_pronunciation','score_'+label,dict(free=free,forced=forced,confidence=.8),score,lambda:pr.assess('synthetic','apel')['score'])
    rows=[r for r in records if r['section']=='05_pronunciation' and r['case_id'].startswith('score_')]
    fig,ax=plt.subplots(figsize=(8,3));vals=[json.loads(r['actual']) for r in rows];ax.bar([r['case_id'][6:] for r in rows],[v or 0 for v in vals],color='#8173ba');ax.set(ylabel='Skor algoritma (0-100)',title='Pengujian terkontrol: bukan penilaian manusia');fig.tight_layout();fig.savefig(OUT/'05_pronunciation/pronunciation_visualization.png',dpi=160);plt.close(fig)

def main():
    graph_cases();quality_eye();vad_fluency();pronunciation_checks()
    dump('algorithm_results.json',records)
    for sec,file in [('03_eye_tracking','eye_tracking_metrics.csv'),('05_pronunciation','pronunciation_test_cases.csv'),('06_fluency','fluency_metrics.csv'),('07_multimodal_fusion','fusion_test_cases.csv')]:csvout(sec+'/'+file,[r for r in records if r['section']==sec])
    csvout('03_eye_tracking/idt_test_cases.csv',[r for r in records if r['case_id'].startswith('IDT_')])
    csvout('05_pronunciation/pronunciation_scores.csv',[r for r in records if r['case_id'].startswith('score_')])
    csvout('07_multimodal_fusion/quality_gate_test_cases.csv',[r for r in records if r['case_id'].startswith(('Q_','speech_gate','coverage','cal_'))])
    csvout('07_multimodal_fusion/concordance_validation.csv',[r for r in records if r['case_id'].startswith('F_')])
    csvout('02_vad/vad_test_cases.csv',[r for r in records if r['section']=='02_vad'])
    log(f'Algorithm checks: {len(records)}; passed={sum(r["status"]=="PASSED" for r in records)}; failed={sum(r["status"]=="FAILED" for r in records)}')
if __name__=='__main__':main()
