import json, re
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score,f1_score,confusion_matrix,precision_score,recall_score

import os
DATA=Path(os.environ.get('ETDD70_DIR') or Path(__file__).resolve().parent.parent/'assets'/'dataset'/'ETDD70_v2')
MODELS=Path(__file__).parent/'models'/'research'
TRIAL=['n_fix_trial','sum_fix_dur_trial','dwell_time_trial','mean_fix_dur_trial','n_sacc_trial','mean_sacc_dur_trial','mean_sacc_ampl_trial','n_between_line_regress_trial','n_within_line_regress_trial','n_regress_trial','n_progress_trial']
ROI=['dwell_time_aoi','n_fix_aoi','mean_fix_dur_aoi','skipped_aoi','n_revisits_aoi']
def dataset_frame():
    labels=pd.read_csv(DATA/'dyslexia_class_label.csv').set_index('subject_id')['class_id'].to_dict();rows=[]
    for path in sorted((DATA/'data'/'data').glob('*_metrics.csv')):
        f=pd.read_csv(path);sid=int(f.iloc[0]['sid']);row={c:float(f.iloc[0][c]) for c in TRIAL};words=f[f['aoi_kind']=='subline']
        row.update({f'avg_{c}':float(words[c].mean()) for c in ROI});row.update({'subject_id':str(sid),'task':f.iloc[0]['task'],'label':int(labels[sid])});rows.append(row)
    return pd.DataFrame(rows).replace([np.inf,-np.inf],np.nan)

FEATURE_VERSION='etdd70-trial+roi-v1'

def _sha256(paths):
    import hashlib
    h=hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode());h.update(p.read_bytes())
    return h.hexdigest()

def environment():
    import platform, sklearn
    return {'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scikit_learn':sklearn.__version__,'joblib':joblib.__version__}

def participant_metrics(frame,probabilities,threshold=0.5):
    """Agregasi OOF per peserta: rerata probabilitas semua rekaman peserta, lalu ambang 0,5.
    Semua rekaman satu peserta berada di fold uji yang sama, jadi agregat ini tetap out-of-fold."""
    f=pd.DataFrame({'subject_id':frame['subject_id'].astype(str).values,'label':frame['label'].astype(int).values,'p':probabilities})
    g=f.groupby('subject_id').agg(label=('label','first'),p=('p','mean'),recordings=('p','size'))
    pred=(g['p']>=threshold).astype(int);y=g['label']
    majority=int(y.mode().iloc[0]);base=np.full(len(y),majority)
    return {'participants':int(len(g)),'threshold':threshold,'aggregation':'rerata probabilitas OOF semua rekaman peserta',
            'accuracy':round(accuracy_score(y,pred),4),'macro_f1':round(f1_score(y,pred,average='macro'),4),
            'precision_macro':round(precision_score(y,pred,average='macro',zero_division=0),4),'recall_macro':round(recall_score(y,pred,average='macro',zero_division=0),4),
            'precision_dyslexia':round(precision_score(y,pred,pos_label=1,zero_division=0),4),'recall_dyslexia':round(recall_score(y,pred,pos_label=1,zero_division=0),4),
            'baseline_accuracy':round(accuracy_score(y,base),4),'baseline_macro_f1':round(f1_score(y,base,average='macro'),4),
            'confusion_matrix':confusion_matrix(y,pred,labels=[0,1]).tolist()}

def train(algorithm='logistic',import_frame=None,output_dir=None):
    frame=import_frame if import_frame is not None else dataset_frame()
    features=[c for c in frame.columns if c not in ['subject_id','task','label']]
    X=frame[features].astype(float);y=frame['label'].astype(int);groups=frame['subject_id'].astype(str)
    cv=list(StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=42).split(X,y,groups))
    estimator=RandomForestClassifier(n_estimators=160,max_depth=5,min_samples_leaf=3,random_state=42,n_jobs=2,class_weight='balanced') if algorithm=='forest' else LogisticRegression(max_iter=3000,C=0.1,class_weight='balanced',random_state=42)
    model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),estimator)
    predictions=cross_val_predict(model,X,y,cv=cv,method='predict')
    probabilities=cross_val_predict(model,X,y,cv=cv,method='predict_proba')[:,1]
    baseline=cross_val_predict(DummyClassifier(strategy='most_frequent'),X,y,cv=cv)
    fold_scores=[{'fold':i+1,'train_participants':len(set(groups.iloc[tr])),'test_participants':len(set(groups.iloc[te])),'overlap':len(set(groups.iloc[tr])&set(groups.iloc[te])),'macro_f1':round(f1_score(y.iloc[te],predictions[te],average='macro'),4)} for i,(tr,te) in enumerate(cv)]
    model.fit(X,y)
    importance=np.abs(estimator.coef_[0]) if algorithm!='forest' else estimator.feature_importances_
    version=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    report={'id':version+'-'+algorithm,'algorithm':algorithm,'model_name':'Random Forest' if algorithm=='forest' else 'Logistic Regression','version':version,'created_at':datetime.now(timezone.utc).isoformat(),'samples':len(frame),'participants':int(groups.nunique()),'features':features,'accuracy':round(accuracy_score(y,predictions),4),'macro_f1':round(f1_score(y,predictions,average='macro'),4),'baseline_macro_f1':round(f1_score(y,baseline,average='macro'),4),'baseline_accuracy':round(accuracy_score(y,baseline),4),'precision_macro':round(precision_score(y,predictions,average='macro',zero_division=0),4),'recall_macro':round(recall_score(y,predictions,average='macro',zero_division=0),4),
           'precision_dyslexia':round(precision_score(y,predictions,pos_label=1,zero_division=0),4),'recall_dyslexia':round(recall_score(y,predictions,pos_label=1,zero_division=0),4),
           'evaluation_unit':'rekaman per tugas; lihat participant_level untuk agregat per peserta','participant_level':participant_metrics(frame,probabilities),'feature_importance_source':'model akhir yang di-fit pada seluruh data setelah evaluasi OOF',
           'confusion_matrix':confusion_matrix(y,predictions,labels=[0,1]).tolist(),'folds':fold_scores,'feature_importance':sorted([{'feature':f,'value':round(float(v),4)} for f,v in zip(features,importance)],key=lambda x:-x['value']),'evaluation':'5-fold StratifiedGroupKFold, dipisah berdasarkan peserta; preprocessing dipelajari hanya dari fold pelatihan.','dataset':'CSV impor' if import_frame is not None else 'ETDD70 v2','oof':[{'subject_id':str(row['subject_id']),'task':str(row.get('task','import')),'label':int(row['label']),'prediction':int(predictions[i]),'probability':round(float(probabilities[i]),4)} for i,(_,row) in enumerate(frame.iterrows())]}
    import hashlib
    report['reproducibility']={'feature_version':FEATURE_VERSION,'environment':environment(),'random_state':42,'cv':'StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)',
        'dataset_sha256':_sha256([DATA/'dyslexia_class_label.csv',*(DATA/'data'/'data').glob('*_metrics.csv')]) if import_frame is None else None,
        'import_sha256':hashlib.sha256(pd.util.hash_pandas_object(frame,index=False).values.tobytes()).hexdigest() if import_frame is not None else None}
    dest=output_dir or MODELS;dest.mkdir(parents=True,exist_ok=True);joblib.dump(model,dest/(report['id']+'.joblib'))
    report['reproducibility']['model_sha256']=_sha256([dest/(report['id']+'.joblib')]);(dest/(report['id']+'.json')).write_text(json.dumps(report,indent=2));return report

if __name__=='__main__':
    r=train();print(json.dumps({k:v for k,v in r.items() if k not in ['oof','feature_importance']},indent=2))