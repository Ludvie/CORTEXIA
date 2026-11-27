from common import *
import importlib.util,subprocess

def main():
    ui=OUT/'08_nonfunctional/ui';ui.mkdir(exist_ok=True)
    existing=ROOT/'test_reports/results_ui/browser_check.py'
    spec=importlib.util.spec_from_file_location('existing_ui_check',existing)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.OUT=ui
    module.main()
    env=os.environ.copy();env['CI']='true'
    with (ui/'frontend_tests.log').open('w',encoding='utf-8') as f:
        result=subprocess.run(['node','node_modules/@craco/craco/dist/bin/craco.js','test','--watchAll=false','--runInBand','--json','--outputFile='+str(ui/'frontend_tests.json')],cwd=ROOT/'frontend',env=env,stdout=f,stderr=subprocess.STDOUT)
    log('Technical UI check completed; frontend test exit='+str(result.returncode))
    # No production build writes: verify the existing build's source manifest.
    prior=json.loads((ROOT/'test_reports/results_ui/source_hashes.json').read_text())
    dump('08_nonfunctional/ui/source_match.json',{p:sha(ROOT/p)==h for p,h in prior.items()})
if __name__=='__main__':main()
