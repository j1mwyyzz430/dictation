"""Review reward flow against real backend handlers; all network requests are blocked."""
import functools
import json
import os
import shutil
import subprocess
import threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from check_reference import ROOT, QuietHandler


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    objects={}
    calls=[]
    def api(message):
        nonlocal objects
        calls.append(message['action'])
        result=subprocess.run(['node','tests/check_dictation_sections.cjs','--review-rpc'],
            input=json.dumps({**message,'objects':objects}),text=True,capture_output=True,check=True,cwd=ROOT)
        data=json.loads(result.stdout);objects=data['objects'];return data['result']
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium'),args=['--no-sandbox'])
            context=browser.new_context(viewport={'width':768,'height':1024})
            context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(origin+'/') else r.abort())
            page=context.new_page();errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(origin,wait_until='domcontentloaded');page.expose_function('localReviewAPI',api)
            page.evaluate("""() => {
              endpoint='https://invalid.example/exec';teacherPreview=false;
              user={studentId:'fictional-section-test',classId:'6B',grade:'6',name:'本機測試'};studentToken='fixture';
              cfg.stamp='fixture-stamp';cfg.reviewRewardMax=3;cfg.wordSectionDictation=true;
              window.lessonFixture={id:'section-test',title:'四課詞語',grade:'6',status:'published',words:Array.from({length:40},(_,i)=>'詞語'+(i+1)),sentences:['測試句子'],paragraphs:['測試段落'],memoryParagraphs:['背默內容'],readings:{'w7:0':'慈'},wordSections:[{title:'第一課',start:1,end:7},{title:'第二課',start:8,end:20},{title:'第三課',start:21,end:31},{title:'第四課',start:32,end:40}]};
              currentLesson=clone(lessonFixture);mode='review';scope='words';screen='ready';
              window.failSubmission=true;
              request=async(action,payload)=>{if(action==='submit'&&failSubmission)throw Error('模擬網絡暫停');return await localReviewAPI({action,payload:payload||{}})};
              render();
            }""")
            assert '最多3分' in page.locator('#app').inner_text()
            page.locator('[data-words-none]').click();page.locator('[data-word-choice=section0]').click()
            page.locator('#begin').click();page.wait_for_selector('body[data-screen=writing]')
            assert calls.count('start')==1
            assert page.evaluate('attempt.reviewRewardMax')==3
            assert page.locator('#app .ghost').count()>0
            page.evaluate("attempt.cells.forEach(c=>c.strokes=[[[.2,.5],[.8,.5]]]);persistDraft()")
            ink=page.evaluate('attempt.cells.map(c=>c.strokes)')
            page.locator('#sub').click()
            assert '溫習獎勵' in page.locator('#modalBody').inner_text()
            page.locator('#okSub').click()
            page.wait_for_selector('#retry')
            assert '還未交到老師' in page.locator('#app').inner_text()
            assert page.evaluate('unsynced().length')==1
            assert page.evaluate('attempt.cells.map(c=>c.strokes)')==ink
            page.evaluate('failSubmission=false')
            page.locator('#retry').click()
            page.wait_for_function('attempt.cloudSaved===true && !submissionBusy.size')
            assert page.evaluate('marks(attempt).points')==3
            assert page.evaluate('marks(attempt).maxScore')==3
            assert page.evaluate('attempt.cells.map(c=>c.strokes)')==ink
            assert page.evaluate('unsynced().length')==0
            assert '溫習獎勵分數' in page.locator('#app').inner_text()
            assert '每份最多3分' in page.locator('#app .note.blue').inner_text()
            page.wait_for_function('rankData?.rows?.[0]?.points===3')
            page.evaluate('async()=>{await syncAttempt(attempt)}')
            assert len([k for k in objects if k.startswith('attempt:')])==1
            assert page.evaluate('rankData.rows[0].points')==3
            # Old local reviews, previews and wrong-word practice do not gain retroactive rewards.
            page.evaluate("""() => {
              studentToken='';delete cfg.reviewRewardMax;
              currentLesson=clone(lessonFixture);screen='ready';render();
            }""")
            assert '不計積分' in page.locator('#app').inner_text()
            page.locator('#begin').click();page.wait_for_selector('body[data-screen=writing]')
            assert page.evaluate('rewardedReview22(attempt)') is False
            assert calls.count('start')==1
            for preview,lesson_id in ((True,'section-test'),(False,'wrong-practice')):
                page.evaluate("""([preview,id])=>{
                  draftCache5.clear();localStorage.removeItem(KEY+'-draft-'+user.studentId);
                  cfg.reviewRewardMax=3;teacherPreview=preview;currentLesson=clone(lessonFixture);currentLesson.id=id;screen='ready';render();
                }""",[preview,lesson_id])
                assert page.evaluate('reviewRewardsAvailable22()') is False
                page.locator('#begin').click();page.wait_for_selector('body[data-screen=writing]')
                assert page.evaluate('rewardedReview22(attempt)') is False
            assert calls.count('start')==1
            assert not errors,errors
            print('PASS review selection → server start → offline ink retention → retry → 3-point board, no duplicate or legacy/preview/wrong-word awards')
            browser.close()
    finally:
        server.shutdown();server.server_close()


if __name__=='__main__':
    main()
