"""Six-case runtime VAD regression sample; does not regenerate the dataset."""
from common import *
import zipfile,io,wave
import numpy as np
import fluency
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    archive=Path(r'C:\Users\LENOVO PC\Downloads\CORTEXIA_FLUENCY_FINAL (1).zip')
    with zipfile.ZipFile(archive) as z:rows=list(csv.DictReader(io.StringIO(z.read('cortexia_dataset_integrated.csv').decode('utf-8-sig'))))
    selected=[]
    for status in ['PASS','REVIEW']:
        eligible=[r for r in rows if r['fluency_qc_status']==status]
        eligible.sort(key=lambda r:float(r['audio_duration_sec']))
        selected.extend(eligible[i] for i in [0,len(eligible)//2,len(eligible)-1])
    out=[];gaps=[];fig,axes=plt.subplots(3,2,figsize=(12,8))
    for i,(row,ax) in enumerate(zip(selected,axes.flat),1):
        path=Path(row['preprocessed_path'])
        with wave.open(str(path),'rb') as audio:
            fmt=(audio.getframerate(),audio.getnchannels(),audio.getsampwidth())
            assert fmt==(16000,1,2),'Existing preprocessing incompatible'
            pcm=audio.readframes(audio.getnframes())
        start=time.perf_counter();regions=fluency.segments(pcm);elapsed=time.perf_counter()-start
        active=sum(b-a for a,b in regions);duration=len(pcm)/32000
        pauses=[c-b for (_,b),(c,_) in zip(regions,regions[1:]) if c-b>=.25-2e-6];gaps+=pauses
        prior=float(row['speech_duration_sec']);match=abs(active-prior)<=1e-5
        out.append(dict(case_id=f'BAHANA_SAMPLE_{i}',selection='min/median/max duration within existing PASS or REVIEW stratum',existing_qc=row['fluency_qc_status'],audio_sha256=sha(path),rate_hz=fmt[0],channels=fmt[1],pcm_bits=fmt[2]*8,duration_sec=duration,active_sec=active,prior_active_sec=prior,active_delta_sec=active-prior,segments=len(regions),pauses=len(pauses),mean_pause_sec=float(np.mean(pauses)) if pauses else None,processing_ms=elapsed*1000,timestamps_valid=all(0<=a<b<=duration for a,b in regions),status='PASSED' if match else 'FAILED',comparison='Regression against existing automatic VAD; not ground truth',precision='',recall='',f1='',boundary_error_ms=''))
        samples=np.frombuffer(pcm,dtype=np.int16);step=max(1,len(samples)//5000)
        ax.plot(np.arange(len(samples))[::step]/16000,samples[::step]/32768,lw=.4)
        for a,b in regions:ax.axvspan(a,b,color='#8173ba',alpha=.2)
        ax.set(title=f'BAHANA sample {i} (anonim)',xlabel='Waktu (s)',ylabel='Amplitudo')
    fig.suptitle('Sampel audio BAHANA: sinyal dan prediksi VAD runtime');fig.tight_layout();fig.savefig(OUT/'02_vad/bahana_vad_waveforms.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3));ax.hist(gaps,bins=10,color='#8173ba');ax.set(xlabel='Durasi jeda (s)',ylabel='Jumlah jeda',title='Distribusi jeda pada enam sampel BAHANA; deskriptif');fig.tight_layout();fig.savefig(OUT/'02_vad/bahana_pause_distribution.png',dpi=160);plt.close(fig)
    csvout('02_vad/bahana_runtime_regression.csv',out)
    # Validation CSVs previously found contain algorithm flags, not independent human time labels.
    log(f'BAHANA VAD regression sample: {len(out)} audio; matches={sum(r["status"]=="PASSED" for r in out)}. No dataset regeneration.')
if __name__=='__main__':main()
