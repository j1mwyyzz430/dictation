"""Ranking/result/deployment UI regression, all external requests blocked."""
import functools
import os
import shutil
import tempfile
import threading
from pathlib import Path
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
            assert page.title() == '筆尖默書室 v2.2'
            page.evaluate("""() => {
              endpoint='https://invalid.example/exec';teacherPreview=false;studentToken='';teacherToken='';
              user={studentId:'fictional-a',name:'本機測試',classId:'6B',grade:'6'};
              cfg.backendVersion='2.2';
              attempt={...user,id:'test-ranking-ui',lessonId:'test-lesson',lessonTitle:'本機測試',mode:'dictation',scope:'words',settings:{scoreRule:6,punctuationCounts:false},groups:[{key:'w0',kind:'詞語',text:'甲乙丙丁'}],cells:Array.from('甲乙丙丁',(expected,i)=>({i,expected,auto:['match','match','review','blank'][i],manual:null,strokes:[]})),created:new Date().toISOString(),version:1,approved:false,elapsed:40,timeValid:true,cloudSaved:true};
              rankData={rankingVersion:'2.2',updated:new Date().toISOString(),rows:rankSummaries([{...attempt,metrics:marks(attempt)}],[user],'6','total',Date.now())};
              showBoard();
            }""")
            assert '含1份暫定成績' in page.locator('#bT').inner_text()
            assert page.locator('.ui21-rpts').inner_text().startswith('15')
            assert '待核字暫不加分' in page.locator('#modalBody').inner_text()
            for width, height in ((768,1024),(1024,768)):
                page.set_viewport_size({'width':width,'height':height})
                assert page.locator('.ui21-rpts').is_visible()
            page.evaluate("closeModal();screen='result';resultView()")
            assert '先按此分數計入龍虎榜' in page.locator('#app').inner_text()
            assert '15' in page.locator('#app .note.blue').inner_text()
            page.evaluate("attempt.excluded=true;resultView()")
            assert '此卷不計排名' in page.locator('#app').inner_text()
            page.evaluate("attempt.excluded=false;delete cfg.backendVersion;resultView()")
            assert '等待老師確認後計入排名' in page.locator('#app').inner_text()
            assert '先按此分數計入' not in page.locator('#app').inner_text()
            page.evaluate("delete rankData.rankingVersion;showBoard()")
            assert '目前只計老師已確認的成績' in page.locator('#bU').inner_text()
            page.evaluate("closeModal();cfg.backendVersion='2.2';$('app').innerHTML='<div id=\"tBody\"></div>';tDeploy()")
            assert '2.2（已支援系統分數先上榜）' in page.locator('#tBody').inner_text()
            assert '不用執行 setup' in page.locator('#tBody').inner_text()
            with page.expect_download() as download_info:
                page.locator('#gsDl').click()
            with tempfile.TemporaryDirectory() as folder:
                out=Path(folder)/'Code.gs'
                download_info.value.save_as(out)
                assert out.read_text() == page.locator('#backendSource').text_content()
                assert "rankingVersion:'2.2'" in out.read_text()
            assert not errors, errors
            print('PASS v2.2 title, provisional scores/labels, portrait/landscape, exclusions, old backend fallback, complete Code.gs download')
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
