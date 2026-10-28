"""Isolated word-section UI checks. Never contacts Apps Script or submits a paper."""
import functools
import os
import json
import subprocess
import shutil
import threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from check_reference import ROOT, QuietHandler


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium'), args=['--no-sandbox'])
            context = browser.new_context(viewport={'width': 768, 'height': 1024})
            context.route('**/*', lambda r: r.continue_() if r.request.url.startswith(origin + '/') else r.abort())
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(origin, wait_until='domcontentloaded')
            page.evaluate("""() => {
              endpoint=''; teacherPreview=true;
              user={studentId:'fictional-section-test',classId:'6B',grade:'6',name:'本機測試'};
              window.fixture={id:'section-test',title:'四課詞語',grade:'6',status:'published',
                words:Array.from({length:40},(_,i)=>'詞語'+(i+1)),sentences:['測試句子'],paragraphs:['測試段落'],memoryParagraphs:['背默內容'],readings:{'w7:0':'慈'},
                wordSections:[{title:'第一課',start:1,end:7},{title:'第二課',start:8,end:20},{title:'第三課',start:21,end:31},{title:'第四課',start:32,end:40}]};
              currentLesson=clone(fixture); mode='review'; scope='words'; screen='ready'; render();
            }""")
            assert page.locator('[data-word-choice]').count() == 4
            assert page.locator('[data-word-choice][aria-pressed=true]').count() == 4
            page.locator('[data-words-none]').click()
            assert page.locator('#begin').is_disabled()
            page.locator('[data-word-choice=section1]').click()
            assert page.locator('#begin').is_enabled()
            page.locator('#begin').click()
            page.wait_for_selector('body[data-screen=writing]')
            result = page.evaluate("({keys:attempt.groups.map(g=>g.key),titles:attempt.groups.map(g=>g.title),reading:attempt.readings['w7:0']})")
            assert result['keys'] == [f'w{i}' for i in range(7,20)], result
            assert set(result['titles']) == {'第二課'} and result['reading'] == '慈'
            print('PASS actual ready/start path: unequal sections, empty selection blocked, original reading keys retained')
            page.evaluate("closePad(true);draftCache5.clear();localStorage.removeItem(KEY+'-draft-'+user.studentId);screen='ready';render()")
            page.locator('[data-word-choice=section3]').click()
            assert page.evaluate("selectChosenWords22(buildGroups(currentLesson,'dictation','words')).map(g=>g.key)") == [f'w{i}' for i in list(range(7,20))+list(range(31,40))]
            page.locator('[data-words-all]').click()
            assert page.evaluate("selectChosenWords22(buildGroups(currentLesson,'dictation','words')).length") == 40
            page.evaluate("scope='all';render()")
            page.locator('[data-words-none]').click()
            page.locator('[data-word-choice=section0]').click()
            assert page.evaluate("selectChosenWords22(buildGroups(currentLesson,'dictation','all')).map(g=>g.key)") == [f'w{i}' for i in range(7)]+['s0','p0']
            for mode in ('memory','random'):
                page.evaluate("m=>{mode=m;scope='words';render()}",mode)
                assert page.locator('#wordChoices22').count() == 0
                assert page.evaluate("selectChosenWords22(buildGroups(currentLesson,'dictation','words')).length") == 40
            assert page.evaluate("""() => {
              mode='review';scope='words';currentLesson=clone(fixture);currentLesson.wordSections=[fixture.wordSections[0]];
              const parts=wordSections22(currentLesson);
              if(parts.length!==2||parts[1].keys.length!==33)return false;
              delete currentLesson.wordSections;
              return selectChosenWords22(buildGroups(currentLesson,'dictation','words')).length===40;
            }""")
            print('PASS multiple/all selection, mixed scope, unassigned words, legacy lessons, exam modes unaffected')
            # Drive the real browser start path against the actual backend start function.
            def backend_start(payload):
                result = subprocess.run(['node', 'tests/check_dictation_sections.cjs', '--snapshot'],
                    input=json.dumps(payload), text=True, capture_output=True, check=True, cwd=ROOT)
                return json.loads(result.stdout)
            page.expose_function('localBackendStart', backend_start)
            page.evaluate("""() => {
              window.realRequest=request;window.startPayloads=[];
              request=async(action,payload)=>{
                if(action!=='start')throw Error('Unexpected API in isolated test: '+action);
                startPayloads.push(clone(payload));return await window.localBackendStart(payload);
              };
              currentLesson=clone(fixture);cfg.stamp='fixture-stamp';cfg.wordSectionDictation=true;
              endpoint='https://invalid.example/exec';teacherPreview=false;mode='dictation';scope='words';screen='ready';render();
            }""")
            assert page.locator('[data-word-choice][aria-pressed=true]').count() == 4
            assert '默寫' in page.locator('#wordChoices22 h3').inner_text()
            page.locator('[data-words-none]').click()
            assert page.locator('#begin').is_disabled()
            page.locator('[data-word-choice=section1]').click()
            assert '30分' in page.locator('#wordChoices22').inner_text()
            # Old backend never silently gives all 40 words for a partial request.
            page.evaluate('delete cfg.wordSectionDictation;render()')
            assert page.locator('#begin').is_disabled()
            assert '老師更新後台' in page.locator('#summary21').inner_text()
            page.locator('[data-words-all]').click()
            assert page.locator('#begin').is_enabled()
            page.evaluate('cfg.wordSectionDictation=true;render()')
            page.locator('[data-words-none]').click()
            page.locator('[data-word-choice=section1]').click()
            page.locator('#begin').click()
            page.wait_for_selector('body[data-screen=writing]')
            result=page.evaluate("({keys:attempt.groups.map(g=>g.key),reading:attempt.readings['w7:0'],sent:startPayloads.at(-1).wordSectionKeys})")
            assert sorted(result['keys']) == sorted(f'w{i}' for i in range(7,20))
            assert result['reading']=='慈' and result['sent']==['section1']
            assert page.locator('#app .ghost,#app .ref').count()==0
            assert page.locator('#app [data-c]').count() > 0
            page.locator('[data-c="0"]').click()
            assert page.locator('#pad .ghost,#pad .ref').count()==0
            page.locator('#pdClose').click()
            # Snapshot/groups persist in the existing draft; no new storage schema.
            assert sorted(page.evaluate('draft5().groups.map(g=>g.key)')) == sorted(result['keys'])
            page.locator('#sub').click()
            assert '詞語8' not in page.locator('#modalBody').inner_text()
            page.locator('#cont').click()
            # Reject a misconfigured backend that advertises support but returns all words.
            page.evaluate("""() => {
              draftCache5.clear();localStorage.removeItem(KEY+'-draft-'+user.studentId);
              request=async(action,payload)=>({start:{groups:buildGroups(fixture,'dictation','words'),settings:cfg.settings}});
              screen='ready';render();
            }""")
            page.locator('#begin').click()
            assert page.locator('body').get_attribute('data-screen')=='ready'
            assert '後台題目與所選詞語不符' in page.locator('#toast').inner_text()
            assert page.evaluate('draft5()') is None
            page.evaluate("request=realRequest;endpoint='';teacherPreview=true")
            print('PASS dictation UI → real backend start, subset keys/readings, empty/old-backend guards, hidden answers, draft retention, mismatched response blocked')
            page.evaluate("""() => {
              document.getElementById('app').innerHTML='<div id="tBody"></div>';
              cEdit=clone(cfg);cEdit.lessons={'6B':[clone(fixture)]};cClass='6B';cLesson=0;tContent();
            }""")
            assert page.locator('[data-word-section-row]').count() == 4
            page.locator('[data-word-title]').first.fill('課文甲')
            page.evaluate('collect()')
            assert page.evaluate("cEdit.lessons['6B'][0].readings['w7:0']") == '慈'
            page.locator('[data-remove-word-section]').last.click()
            assert page.locator('#eW').input_value().splitlines() == [f'詞語{i}' for i in range(1,41)]
            page.locator('#addWordSection22').click()
            assert page.locator('[data-word-start]').last.input_value() == '32'
            page.locator('[data-word-title]').last.fill('課文丁')
            page.evaluate('collect();validateWordSections22(cEdit)')
            assert page.evaluate("cEdit.lessons['6B'][0].wordSections[0].title") == '課文甲'
            # Store through real storeConfig, using an isolated in-memory mock response.
            page.evaluate("""() => {
              window.oldRequest=request;window.oldRender=render;window.oldToast=toast;
              window.calls=0;window.messages=[];render=()=>{};toast=(m)=>messages.push(m);
              request=async(action,payload)=>{calls++;return {config:clone(payload.config)}};
            }""")
            page.evaluate('async()=>{await storeConfig(cEdit)}')
            assert page.evaluate("calls===1&&cEdit===null&&cfg.lessons['6B'][0].wordSections[3].title==='課文丁'")
            assert page.evaluate("localConfig5(JSON.parse(localStorage.getItem(KEY+'-config'))).lessons['6B'][0].wordSections[0].title") == '課文甲'
            for invalid in ({'title':'','start':1,'end':7},{'title':'錯誤','start':1,'end':41},{'title':'重疊','start':6,'end':8}):
                page.evaluate("s=>{cEdit=clone(cfg);cEdit.lessons['6B'][0].wordSections.push(s)}",invalid)
                page.evaluate('async()=>{await storeConfig(cEdit)}')
                assert page.evaluate('calls') == 1
                assert page.evaluate('cEdit!==null')
            page.evaluate("""async()=>{
              cEdit=clone(cfg);
              request=async(action,payload)=>{calls++;const config=clone(payload.config);delete config.lessons['6B'][0].wordSections;return {config}};
              await storeConfig(cEdit);
            }""")
            assert page.evaluate("cEdit!==null&&messages.at(-1).includes('未完整保存')")
            assert not errors, errors
            print('PASS teacher editing, preserved words/readings, save/reload, invalid ranges rejected before API, metadata loss detected')
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
