from common import *
import subprocess,socket,xml.etree.ElementTree as ET,shutil
import requests
import pymongo

def main():
    supplemental='--supplemental' in sys.argv
    run_dir=OUT/'09_integration'/('supplemental' if supplemental else '')
    run_dir.mkdir(exist_ok=True)
    env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(OUT/'_test_dependencies'),str(OUT),str(ROOT/'backend')])
    env['COVERAGE_FILE']=str(OUT/'01_whitebox/.coverage')
    env['TMP']=env['TEMP']=str(OUT/'_tmp');Path(env['TMP']).mkdir(exist_ok=True)
    attempt=run_dir/'attempt_1';attempt.mkdir(exist_ok=True)
    for name in ['pytest.log','pytest_results.xml','server.log','run.json']:
        old=run_dir/name
        if old.exists() and not (attempt/name).exists():shutil.copyfile(old,attempt/name)
    if (OUT/'01_whitebox/coverage.json').exists() and not (attempt/'coverage.json').exists():shutil.copyfile(OUT/'01_whitebox/coverage.json',attempt/'coverage.json')
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));mongo_port=sock.getsockname()[1]
    dbpath=OUT/'_mongo';dbpath.mkdir(exist_ok=True)
    mongo_log=(run_dir/'mongo.log').open('w',encoding='utf-8')
    mongo=subprocess.Popen([r'C:\Program Files\MongoDB\Server\9.0\bin\mongod.exe','--bind_ip','127.0.0.1','--port',str(mongo_port),'--dbpath',str(dbpath),'--wiredTigerCacheSizeGB','0.25'],stdout=mongo_log,stderr=subprocess.STDOUT)
    env['MONGO_URL']=env['CORTEXIA_TEST_MONGO_URL']=f'mongodb://127.0.0.1:{mongo_port}'
    client=pymongo.MongoClient(env['MONGO_URL'],serverSelectionTimeoutMS=3000)
    server=None;ready=False
    try:
        for _ in range(20):
            try:client.admin.command('ping');break
            except pymongo.errors.ServerSelectionTimeoutError:
                if mongo.poll() is not None:raise
                time.sleep(.5)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        loghandle=(run_dir/'server.log').open('w',encoding='utf-8')
        server=subprocess.Popen([sys.executable,'-m','uvicorn','server:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT/'backend',env=env,stdout=loghandle,stderr=subprocess.STDOUT)
        base=f'http://127.0.0.1:{port}'
        for _ in range(90):
            try:
                if requests.get(base+'/api/health',timeout=2).status_code==200:ready=True;break
            except requests.RequestException:pass
            if server.poll() is not None:break
            time.sleep(.5)
        if ready:env['REACT_APP_BACKEND_URL']=base
    except Exception as e:log('Integration local DB/server unavailable: '+type(e).__name__)
    if not ready:env.pop('REACT_APP_BACKEND_URL',None)
    log('Dedicated local integration server ready='+str(ready)+'; DB='+env['DB_NAME'])
    args=[sys.executable,'-m','pytest','tests',str(OUT/'test_security_internal.py'),'-p','audit_pytest_plugin','--cov=analytics','--cov=fluency','--cov=pronunciation','--cov=sessions','--cov=core','--cov=auth','--cov=content','--cov-branch','--cov-report=json:'+str(OUT/'01_whitebox/coverage.json'),'--cov-report=term-missing','--junitxml='+str(OUT/'09_integration/pytest_results.xml'),'-ra','--tb=short']
    if supplemental:args=[sys.executable,'-m','pytest','-c',str(ROOT/'backend/pytest.ini'),str(OUT/'test_isolated_roundtrip.py'),'--junitxml='+str(run_dir/'pytest_results.xml'),'-ra','--tb=short']
    started=time.perf_counter()
    try:
        with (run_dir/'pytest.log').open('w',encoding='utf-8') as loghandle:
            result=subprocess.run(args,cwd=ROOT/'backend',env=env,stdout=loghandle,stderr=subprocess.STDOUT)
        dump(str((run_dir/'run.json').relative_to(OUT)),dict(exit_code=result.returncode,elapsed_sec=time.perf_counter()-started,server_ready=ready,database=env['DB_NAME'],command=args))
        log('Existing + source-directed pytest finished; exit='+str(result.returncode))
    finally:
        if server:server.terminate();server.wait(timeout=20)
        client.close()
        mongo.terminate();mongo.wait(timeout=20)
if __name__=='__main__':main()
