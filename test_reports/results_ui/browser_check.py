"""Exercise the production build in Edge with synthetic API responses only.
Run from the repository root with Python (requests, websockets installed).
No backend, participant records, credentials, microphone, or camera are used.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import requests
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


class StaticHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'frontend/build'), **kwargs)

    def do_GET(self):
        if self.path == '/test-error':
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"detail":"Simulated API unavailable"}')
            return
        if not Path(self.translate_path(self.path)).is_file():
            self.path = '/index.html'
        super().do_GET()

    def log_message(self, *_):
        pass

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError):
            # Expected when Edge closes a keep-alive connection during shutdown.
            pass


MOCK = r"""
sessionStorage.setItem('cortexia-token','synthetic-ui-test');
sessionStorage.setItem('cortexia-splash-seen','1');
window.testEl=id=>document.querySelector('[data-testid="'+id+'"]');
window.uiCalls=[];
const scenario=new URLSearchParams(location.search).get('scenario')||'both';
const audio=!['gaze','empty-data'].includes(scenario), gaze=!['audio','empty-data'].includes(scenario);
const fixture={id:'synthetic-session',student_alias:'Peserta Demo (data uji)',text_title:'Petualangan di Taman',created_at:'2026-11-27T00:00:00Z',
 quality:audio&&gaze?'layak':audio||gaze?'parsial':'tidak_cukup',duration:32,mode:'both',retention_days:30,
 profile:'Latihan ketepatan kata',profile_method:'Aturan observasional v1',profile_reason:'Contoh dasar pengamatan untuk pengujian antarmuka.',
 transcript:'Pagi ini Rani pergi ke taman bunga bersama ibu.',reviewed:false,reviews:[],
 recommendations:['Dengarkan dan ulangi kata yang ditandai, lalu baca kembali kalimatnya.','Prioritaskan kata yang ditandai kedua modalitas saat latihan.'],
 quality_reasons:['Suara memadai (keyakinan transkripsi 94,1%).','Tatapan memadai (kalibrasi layak, cakupan 100%).'],
 limitations:['Ketepatan kata berasal dari transkripsi, bukan penilaian fonem.','Fiksasi webcam memiliki ketelitian lebih rendah dari eye-tracker laboratorium.'],
 calibration:{median_error:.08,validation_samples:20},gaze_points:[{x:.2,y:.3,t:0},{x:.5,y:.4,t:1}],
 layouts:[{width:1000,height:500,words:[{i:0,text:'kupu-kupu',x:.1,y:.3,w:.2,h:.1}]}],
 metrics:{accuracy:audio?59.38:null,wpm:audio?59.7:null,wer:40.62,wer_source:'transkrip_otomatis',substitutions:8,deletions:2,insertions:3,
 speech_reliable:audio,gaze_usable:gaze,gaze_analyzable:gaze,on_text_percent:gaze?74.1:null,fixations:42,regressions:17,mean_fixation_ms:240,
 gaze_samples:256,gaze_rate_hz:8,gaze_coverage:100,calibration_valid:true,asr_confidence:94.1,
 annotations:audio?[{index:0,word:'kupu-kupu',spoken:'kupu',type:'substitute'},{index:1,word:'riang',spoken:'',type:'delete'}]:[],
 gaze:{longest_dwell:[{index:0,word:'kupu-kupu',ms:650,visits:3},{index:1,word:'riang',ms:550,visits:2}],regression_rate:41.5,
 scanpath:[{t:0,d:200,x:.2,y:.35,word:0},{t:1,d:400,x:.2,y:.35,word:0}]},
 multimodal:{multimodal_complete:audio&&gaze,basis:'suara + tatapan',signals:{word_accuracy_low:true,fluency_low:true,gaze_irregular:true},pattern:'Kesalahan ucap dan alur visual tidak teratur (belum pada kata yang sama)',
 concordance:30,concordant:false,speech_error_words:10,agreement_words:[{index:0,word:'kupu-kupu'},{index:1,word:'riang'},{index:2,word:'kupu-kupunya'}],
 explanation:'Contoh uji tampilan: beberapa kata yang ditandai suara berbeda dari kata yang lebih lama ditatap.'},
 fluency:{wpm:65.4,articulation_rate_syllables_per_sec:2.8,mlr_syllables_per_run:7.6,pause_frequency_per_min:4.2,mean_pause_duration_sec:.52,method_version:'bahana-id-v1',transcript_source:'asr_original',qc_flags:[]},
 word_observations:[{display_index:0,word:'kupu-kupu',first_fixation_ms:200,first_visit_ms:200,first_visit_fixations:1,total_fixation_ms:600,asr_word_duration_ms:500}]}};
if(scenario==='legacy')fixture.metrics={};
if(scenario==='empty-data'){fixture.metrics={};fixture.profile='Data belum cukup';}
const open=XMLHttpRequest.prototype.open, send=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(method,url,...rest){
 this.testURL=url;this.testMethod=method;let data;
 if(url.endsWith('/auth/me'))data={name:'Demo',role:scenario==='student'?'student':'teacher'};
 else if(url.includes('/sessions/')){
  window.uiCalls.push({method,url});
  if(scenario==='error')return open.call(this,'GET','/test-error',...rest);
  if(scenario==='loading'){this.testPending=true;return open.call(this,'GET','/test-error',...rest);}
  if(url.endsWith('/report'))return open.call(this,'GET',URL.createObjectURL(new Blob(['%PDF-1.4\n%%EOF'],{type:'application/pdf'})),...rest);
  if(method.toUpperCase()==='PATCH'){fixture.reviewed=true;fixture.metrics.accuracy=100;fixture.transcript='Transkripsi ditinjau';}
  data=scenario==='empty'?null:fixture;
 }
 if(data!==undefined)return open.call(this,'GET',URL.createObjectURL(new Blob([JSON.stringify(data)],{type:'application/json'})),...rest);
 return open.call(this,method,url,...rest);
};
XMLHttpRequest.prototype.send=function(body){if(this.testPending)return;return send.call(this,body);};
"""

# Computed-style contrast for visible text in the Results subtree. This checks
# flat surfaces used here; it is not a full WCAG / assistive technology audit.
CONTRAST = r"""(()=>{
 const root=document.querySelector('.assessment-results');
 const rgb=s=>(s.match(/[\d.]+/g)||[]).map(Number);
 const lum=c=>c.slice(0,3).map(x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4}).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0);
 const bg=el=>{while(el){let c=rgb(getComputedStyle(el).backgroundColor);if(c.length===3||c[3]===1)return c;el=el.parentElement;}return [255,255,255];};
 const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let node,fail=[],count=0;
 while((node=walker.nextNode())){
   if(!node.textContent.trim())continue;const el=node.parentElement,range=document.createRange();range.selectNodeContents(node);
   if(!range.getBoundingClientRect().width||el.closest('[hidden]')||getComputedStyle(el).visibility==='hidden')continue;
   const closed=el.closest('details:not([open])');if(closed&&!el.closest('summary'))continue;
   if(el.closest('.sr-only'))continue;
   const style=getComputedStyle(el),fg=rgb(style.color),back=bg(el),a=lum(fg),b=lum(back),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
   const size=parseFloat(style.fontSize),large=size>=24||(size>=18.66&&parseInt(style.fontWeight)>=700);count++;
   if(ratio<(large?3:4.5))fail.push({text:node.textContent.trim().slice(0,80),ratio,size,color:style.color});
 }
 return {checked:count,failures:fail};
})()"""


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), StaticHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    profile = tempfile.mkdtemp(prefix='cortexia-results-')
    edge = Path(os.environ['ProgramFiles(x86)']) / 'Microsoft/Edge/Application/msedge.exe'
    process = subprocess.Popen([str(edge), '--headless', '--disable-gpu', '--no-first-run', '--disable-extensions',
                                '--remote-debugging-port=0', '--user-data-dir=' + profile, 'about:blank'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    checks, errors, contrast_results = [], [], []
    try:
        portfile = Path(profile) / 'DevToolsActivePort'
        for _ in range(150):
            if portfile.exists():
                break
            time.sleep(.1)
        port = portfile.read_text().splitlines()[0]
        targets = requests.get(f'http://127.0.0.1:{port}/json/list').json()
        url = next(t['webSocketDebuggerUrl'] for t in targets if t['type'] == 'page' and t['url'] == 'about:blank')
        ws = connect(url.replace('localhost', '127.0.0.1'), max_size=None, proxy=None, legacy=True)
        serial = 0

        def call(method, params=None):
            nonlocal serial
            serial += 1
            ws.send(json.dumps(dict(id=serial, method=method, params=params or {})))
            while True:
                item = json.loads(ws.recv(timeout=30))
                if item.get('method') == 'Runtime.exceptionThrown':
                    errors.append(item['params']['exceptionDetails'])
                if item.get('id') == serial:
                    if 'error' in item:
                        raise RuntimeError(item['error'])
                    return item.get('result', {})

        def ev(expression):
            result = call('Runtime.evaluate', dict(expression=expression, returnByValue=True))
            return result.get('result', {}).get('value')

        def wait(expression):
            for _ in range(100):
                if ev("typeof testEl!=='undefined' && (" + expression + ')'):
                    return
                time.sleep(.2)
            raise AssertionError(expression + ' ' + str(ev('({text:document.body.innerText.slice(-300),url:location.href,scripts:[...document.scripts].map(s=>s.src)})')) + ' errors: ' + json.dumps(errors))

        def check(name, expression):
            value = ev(expression)
            checks.append({'name': name, 'passed': bool(value)})
            assert value, name

        def navigate(scenario='both'):
            call('Page.navigate', dict(url=f'http://127.0.0.1:{server.server_port}/results/synthetic-session?scenario={scenario}'))

        call('Page.enable'); call('Runtime.enable')
        call('Page.addScriptToEvaluateOnNewDocument', {'source': MOCK})
        for width, height in [(1920, 1080), (1366, 768), (768, 1024), (390, 844)]:
            call('Emulation.setDeviceMetricsOverride', dict(width=width, height=height, deviceScaleFactor=1, mobile=False))
            navigate(); wait("!!testEl('fusion-panel')")
            time.sleep(.5)
            check(f'no page overflow {width}', 'document.documentElement.scrollWidth<=innerWidth')
            check(f'body readable {width}', "parseFloat(getComputedStyle(document.querySelector('.assessment-profile-main>p')).fontSize)>=16")
            check(f'three shared words {width}', "document.querySelectorAll('[data-testid=word-group-both] a').length===3")
            check(f'word practice URL {width}', "testEl('agreement-word-0').getAttribute('href')==='/pronunciation?word=kupu-kupu'")
            contrast = ev(CONTRAST)
            contrast_results.append({'width': width, **contrast})
            assert not contrast['failures'], contrast
            checks.append({'name': f'visible overview text contrast {width}', 'passed': True})
            png = call('Page.captureScreenshot', {'format': 'png'})['data']
            (OUT / f'results-{width}.png').write_bytes(base64.b64decode(png))
            if width in (1366, 390):
                ev("document.querySelector('.assessment-tabs').scrollIntoView()")
                png = call('Page.captureScreenshot', {'format': 'png'})['data']
                (OUT / f'analysis-{width}.png').write_bytes(base64.b64decode(png))
                ev("document.getElementById('fluency-heading').scrollIntoView()")
                png = call('Page.captureScreenshot', {'format': 'png'})['data']
                (OUT / f'fluency-{width}.png').write_bytes(base64.b64decode(png))
            for tab in ['speech', 'gaze', 'details', 'overview']:
                ev(f"testEl('result-tab-{tab}').click()")
                wait(f"testEl('result-tab-{tab}').getAttribute('aria-selected')==='true'")
                check(f'{tab} no overflow {width}', 'document.documentElement.scrollWidth<=innerWidth')
                check(f'{tab} finite labels {width}', "!document.querySelector('.assessment-results').innerText.match(/undefined|NaN/)")
                contrast = ev(CONTRAST)
                contrast_results.append({'width': width, 'tab': tab, **contrast})
                assert not contrast['failures'], {'tab': tab, **contrast}
                checks.append({'name': f'{tab} visible text contrast {width}', 'passed': True})
            ev("testEl('result-tab-overview').focus()")
            call('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'ArrowRight', 'code': 'ArrowRight'})
            check(f'keyboard tabs {width}', "document.activeElement===testEl('result-tab-speech')&&testEl('result-tab-speech').getAttribute('aria-selected')==='true'")
        ev("testEl('edit-transcript').click()")
        wait("!!testEl('corrected-transcript')")
        ev("testEl('corrected-transcript').closest('form').requestSubmit()")
        wait("testEl('metric-accuracy').innerText.includes('100')")
        check('review endpoint preserved', "uiCalls.some(c=>c.method.toUpperCase()==='PATCH'&&c.url.endsWith('/review'))")
        check('original fluency after review', "testEl('fluency-wpm').textContent==='65,4'")
        ev("testEl('download-report').click()")
        wait("uiCalls.some(c=>c.url.endsWith('/report'))")
        checks.append({'name': 'PDF endpoint called', 'passed': True})
        for scenario in ['audio', 'gaze', 'empty-data', 'legacy', 'student', 'empty', 'error', 'loading']:
            navigate(scenario)
            target = {'empty': "document.body.innerText.includes('Hasil asesmen belum tersedia')", 'error': "!!testEl('results-error')", 'loading': "!!testEl('loading-state')"}.get(scenario, "!!testEl('result-heading')")
            wait(target)
            if scenario in ['audio', 'gaze', 'empty-data', 'legacy']:
                check(f'{scenario}: no false fusion', "!testEl('fusion-panel')&&!!testEl('fusion-unavailable')")
            if scenario == 'student':
                ev("testEl('result-tab-speech').click()")
                check('student cannot edit', "!testEl('edit-transcript')")
            check(f'{scenario}: no overflow', 'document.documentElement.scrollWidth<=innerWidth')
        assert not errors, errors
        checks.append({'name': 'no uncaught browser exceptions', 'passed': True})
        (OUT / 'browser_results.json').write_text(json.dumps({'checks': checks, 'runtime_errors': errors, 'contrast': contrast_results}, indent=2), encoding='utf-8')
        print(f'{len(checks)} browser checks passed. Screenshots: {OUT}', flush=True)
        ws.close()
    finally:
        server.shutdown(); process.terminate(); process.wait(timeout=10)


if __name__ == '__main__':
    main()
