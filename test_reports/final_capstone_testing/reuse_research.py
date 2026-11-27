from common import *
import zipfile,io,statistics,shutil,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    ml=ROOT/'test_reports/ml_comparison'
    config=json.loads((ml/'experiment_config.json').read_text(encoding='utf-8'))
    # Existing reported data only. Do not load/refit estimator or regenerate OOF.
    names=['comparison_metrics.csv','participant_metrics.csv','fold_metrics.csv','baseline_comparison.csv','leakage_audit.csv','ML_COMPARISON_REPORT.md','verification.json']
    for name in names:
        if (ml/name).exists():shutil.copyfile(ml/name,OUT/'10_existing_ml_results'/name)
    hashes={n:sha(ml/n) for n in names if (ml/n).exists()}
    dump('10_existing_ml_results/provenance.json',dict(source='test_reports/ml_comparison',copied_sha256=hashes,experiment_source_hashes={k:v for k,v in config.items() if 'hash' in k},training_repeated=False))
    path=Path(r'C:\Users\LENOVO PC\Downloads\CORTEXIA_TUREAD_EXPERIMENT.zip')
    with zipfile.ZipFile(path) as z:
        for name in ['results/metrics.csv','results/fold_metrics.csv','results/summary.json']:(OUT/'11_existing_turead_results'/Path(name).name).write_bytes(z.read(name))
        dump('11_existing_turead_results/provenance.json',dict(archive_sha256=sha(path),training_script_sha256=hashlib.sha256(z.read('turead_multimodal.py')).hexdigest(),training_repeated=False))
    path=Path(r'C:\Users\LENOVO PC\Downloads\CORTEXIA_FLUENCY_FINAL (1).zip')
    with zipfile.ZipFile(path) as z:
        summary=json.loads(z.read('cortexia_fluency_summary.json'))
        data=list(csv.DictReader(io.StringIO(z.read('cortexia_dataset_integrated.csv').decode('utf-8-sig'))))
        dump('06_fluency/bahana_existing_summary.json',summary)
        dump('06_fluency/bahana_provenance.json',dict(archive_sha256=sha(path),members=len(z.namelist()),audio_files=sum(n.lower().endswith(('.wav','.mp3','.flac')) for n in z.namelist()),script_sha256=hashlib.sha256(z.read('cortexia_fluency_integrate.py')).hexdigest(),rows=len(data),preprocessing_repeated=False,available_audio_paths=sum(any(Path(r.get(k,'__missing__')).is_file() for k in ['resolved_audio_path','preprocessed_path','source_audio_path']) for r in data)))
    calculations={
        'wpm':lambda r:float(r['asr_word_count'])*60/float(r['utterance_duration_sec']),
        'articulation_rate_syllables_per_sec':lambda r:float(r['syllable_count'])/float(r['articulation_duration_sec']),
        'mlr_syllables_per_run':lambda r:float(r['syllable_count'])/float(r['run_count']),
        'pause_frequency_per_min':lambda r:float(r['num_internal_pauses'])*60/float(r['utterance_duration_sec']),
        'mean_pause_duration_sec':lambda r:float(r['fluency_pause_total_sec'])/float(r['num_internal_pauses']),
    }
    aggregate=[];audit=[]
    fig,axes=plt.subplots(2,3,figsize=(12,7))
    for ax,(metric,formula) in zip(axes.flat,calculations.items()):
        values=[float(r[metric]) for r in data if r[metric]!=''];deltas=[abs(float(r[metric])-formula(r)) for r in data if r[metric]!='']
        aggregate.append(dict(metric=metric,n=len(values),mean=statistics.mean(values),median=statistics.median(values),min=min(values),max=max(values),source='existing BAHANA 140 artifact; no re-extraction'))
        audit.append(dict(metric=metric,checked=len(deltas),mismatches=sum(d>2e-6 for d in deltas),max_absolute_error=max(deltas),tolerance=2e-6,status='PASSED' if all(d<=2e-6 for d in deltas) else 'FAILED'))
        ax.hist(values,bins=15,color='#8173ba');ax.set_title(metric,fontsize=9);ax.set_ylabel('Jumlah audio')
    axes.flat[-1].axis('off');fig.suptitle('Distribusi fitur dari artefak BAHANA yang sudah tersedia');fig.tight_layout();fig.savefig(OUT/'06_fluency/fluency_distribution.png',dpi=160);plt.close(fig)
    csvout('06_fluency/bahana_aggregate.csv',aggregate);csvout('06_fluency/bahana_formula_audit.csv',audit)
    log('Reused ML, TURead and BAHANA aggregate results without training, cleaning or dataset feature extraction.')
if __name__=='__main__':main()
