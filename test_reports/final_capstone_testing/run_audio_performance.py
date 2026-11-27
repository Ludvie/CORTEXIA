from common import *
import asyncio,statistics,threading,platform,io
import numpy as np
import psutil,jiwer
import analytics as a,pronunciation as pr,sessions
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fastapi import UploadFile,HTTPException
from unittest.mock import patch

def main():
    sample=ROOT/'backend/tests/fixtures/bookbot_sample.wav';pcm=pr.decode_pcm(str(sample))
    ref='sepulang sekolah fitri sangat lapar'
    rows=[];perf=[];errors=[]
    proc=psutil.Process()
    def benchmark(name,fn,n):
        times=[];cpu=[];ram=[]
        for i in range(n):
            values=[];stop=threading.Event()
            def watch():
                while not stop.is_set():values.append(proc.memory_info().rss/2**20);stop.wait(.02)
            thread=threading.Thread(target=watch,daemon=True);thread.start()
            c0=sum(proc.cpu_times()[:2]);t0=time.perf_counter()
            try:fn()
            finally:
                times.append((time.perf_counter()-t0)*1000);cpu.append((sum(proc.cpu_times()[:2])-c0)*1000);stop.set();thread.join();ram.append(max(values or [proc.memory_info().rss/2**20]))
        perf.append(dict(operation=name,n=n,mean_ms=statistics.mean(times),median_ms=statistics.median(times),p95_ms=float(np.percentile(times,95)),mean_process_cpu_ms=statistics.mean(cpu),peak_sampled_process_rss_mb=max(ram),rss_sampling_ms=20,status='PASSED'))
    for model,ready,fn in [('Vosk-ID',pr.vosk_ready(),lambda:pr.recognize(pcm)),('Whisper',a.asr_ready(),lambda:a.transcribe_pcm(pcm)['words'])]:
        if not ready:
            rows.append(dict(model=model,source='public_fixture',status='BLOCKED',reason='Local model weights unavailable; no download',wer_percent='',cer_percent=''));continue
        start=time.perf_counter();words=fn();elapsed=time.perf_counter()-start
        hyp=a.normalize(' '.join(w['word'] for w in words));result=jiwer.process_words(ref,hyp)
        valid=all(0<=w['start']<=w['end']<=len(pcm)/32000+.1 for w in words) and [w['start'] for w in words]==sorted(w['start'] for w in words)
        rows.append(dict(model=model,source='public_fixture',status='PASSED',reference_type='documented utterance in fixture README; not independent multi-rater annotation',wer_percent=100*result.wer,cer_percent=100*jiwer.cer(ref,hyp),substitutions=result.substitutions,deletions=result.deletions,insertions=result.insertions,duration_sec=len(pcm)/32000,cold_processing_sec=elapsed,timestamps_valid=valid,words=len(words)))
        errors.append(dict(model=model,reference_words=len(ref.split()),recognized_words=len(words),substitutions=result.substitutions,deletions=result.deletions,insertions=result.insertions,scope='one public fixture only'))
        benchmark(model+'_warm_recognition',fn,5)
    for mode in [False,True]:
        def broken(_):raise RuntimeError('synthetic unavailable Whisper')
        with patch.object(sessions,'asr_ready',lambda:mode),patch.object(sessions,'transcribe_pcm',broken):
            result=sessions.reading_audio(str(sample),ref)
        rows.append(dict(model='fallback_failed_whisper' if mode else 'fallback_no_whisper',source='public_fixture',status='PASSED' if result['model']==pr.MODEL_NAME and result['transcript'] else 'FAILED',reason='Actual Vosk; mocked Whisper readiness/failure only'))
    invalid=UploadFile(file=io.BytesIO(b'corrupt'*100),filename='synthetic.wav')
    try:asyncio.run(sessions.audio_result(invalid));status='FAILED'
    except HTTPException as e:status='PASSED' if e.status_code==422 else 'FAILED'
    rows.append(dict(model='corrupt_audio',source='synthetic',status=status,reason='Expected HTTPException 422'))
    points=[dict(x=.1+(i//8%5)*.15,y=.5,t=i/8) for i in range(240)]
    cal=dict(passed=True,median_error=.08,validation_samples=40)
    m=a.analyze(ref,ref,30,points,cal,[dict(word=w,start=i,end=i+.4,probability=.9) for i,w in enumerate(ref.split())])['metrics']
    benchmark('gaze_analysis_240_points',lambda:a.gaze_metrics(points,30,cal),30)
    benchmark('rule_fusion',lambda:a.fuse(ref,m,True),100)
    benchmark('audio_decode_asr_vad_fluency',lambda:sessions.reading_audio(str(sample),ref),5)
    def integrated():
        speech=sessions.reading_audio(str(sample),ref)
        a.analyze(ref,speech['transcript'],speech['audio_duration'],points,cal,speech['words'],pronunciation=speech.get('pronunciation'))
    benchmark('inprocess_session_excluding_http_database',integrated,5)
    csvout('04_speech_recognition/speech_recognition_metrics.csv',rows)
    csvout('04_speech_recognition/speech_error_analysis.csv',errors)
    csvout('08_nonfunctional/performance_metrics.csv',perf)
    dump('08_nonfunctional/device.json',dict(platform=platform.platform(),python=platform.python_version(),processor=os.environ.get('PROCESSOR_IDENTIFIER','unknown'),logical_cpu=psutil.cpu_count(),physical_cpu=psutil.cpu_count(logical=False),total_ram_gib=psutil.virtual_memory().total/2**30,scope='one local process, no load concurrency; CPU time not utilization percent; RSS sampled every 20ms'))
    fig,ax=plt.subplots(figsize=(10,4));ax.barh([r['operation'] for r in perf],[r['median_ms'] for r in perf],color='#8173ba');ax.set_xscale('log');ax.set(xlabel='Median (ms), skala log',title='Performa lokal; proses hangat');fig.tight_layout();fig.savefig(OUT/'08_nonfunctional/performance_visualization.png',dpi=160);plt.close(fig)
    log('Audio inference and performance completed; no models downloaded. Whisper ready='+str(a.asr_ready()))
if __name__=='__main__':main()
