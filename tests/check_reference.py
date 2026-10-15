"""Local UI regression checks; all non-local browser requests are blocked.

Run: python3 tests/check_reference.py
Requires Python Playwright, Pillow, Node, and Chromium (CHROMIUM_PATH overrides).
Artifacts go to /tmp/dictation-reference-checks, never into the published site.
"""

import functools
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get("DICTATION_TEST_ARTIFACTS", "/tmp/dictation-reference-checks"))
CHARS = "老實審視一"
HIDDEN_CHARS = "龘龖麤靐"


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.current = None
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.current = [dict(attrs), ""]

    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.items.append(self.current)
            self.current = None


def check_syntax():
    for entry in ("index.html", "handoff/index.html"):
        parser = Scripts()
        parser.feed((ROOT / entry).read_text())
        with tempfile.TemporaryDirectory() as folder:
            for n, (attrs, source) in enumerate(parser.items):
                script = Path(folder) / f"script-{n}.js"
                script.write_text(source)
                subprocess.run(["node", "--check", str(script)], check=True, capture_output=True)
            ids = [attrs.get("id") for attrs, _ in parser.items]
            assert ids.count("ghostAlign21Script") == 1, ids
            backend = next(source for attrs, source in parser.items if attrs.get("id") == "backendSource")
            assert "ghostAlign21Script" not in backend
        print(f"PASS syntax: {entry}, {len(parser.items)} scripts including embedded backend")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def prepare(page, mode="review"):
    # Use the real readyView/startAttempt path with a fictional local preview user.
    page.evaluate("""modeToUse => {
      closePad(true); closeModal(); endpoint=''; teacherPreview=true;
      user={studentId:'local-centering-test',classId:'4B',grade:'4',name:'本機測試'};
      draftCache5.clear(); localStorage.removeItem(KEY+'-draft-'+user.studentId);
      currentLesson={id:'local-centering-lesson',title:'本機字形測試',grade:'4',status:'published',
        words:['老實審視一','老人'],sentences:[],paragraphs:[],memoryParagraphs:['老實審視一'],readings:{}};
      if(modeToUse!=='review'){
        currentLesson.words=['龘龖麤靐'];currentLesson.memoryParagraphs=['龘龖麤靐'];
      }
      mode=modeToUse; scope='words'; screen='ready'; render();
    }""", mode)
    page.locator("#begin").click()
    page.wait_for_selector("body[data-screen=writing]")


def ink_bounds(ghost, label):
    # Rasterize the actual rendered glyph, not the font line-box or the fit formula.
    png = ghost.screenshot(style="""
      .paper canvas,.paper .hint{visibility:hidden!important}
      .ghost{color:#000!important;background:#fff!important}
    """)
    image = Image.open(io.BytesIO(png)).convert("L")
    box = image.point(lambda p: 255 if p < 100 else 0).getbbox()
    assert box, f"{label}: no visible ink"
    left, top, right, bottom = box
    width, height = image.size
    dx = abs((left + right) / 2 - width / 2) / width
    dy = abs((top + bottom) / 2 - height / 2) / height
    assert max(dx, dy) < .02, f"{label}: off-center {dx=:.3f}, {dy=:.3f}"
    ratio = (bottom - top) / (right - left)
    if label.endswith("一"):
        assert ratio < .25, f"{label}: stretched horizontal stroke {ratio=}"
    else:
        assert .72 < max((right-left)/width, (bottom-top)/height) < .88, label
    return {"label": label, "size": [width, height], "bounds": list(box),
            "center_error": [round(dx, 4), round(dy, 4)], "height_width": round(ratio, 4)}


def draw_right(page):
    box = page.locator("#pdCv").bounding_box()
    x, y, w, h = (box[k] for k in ("x", "y", "width", "height"))
    page.mouse.move(x + w * .70, y + h * .30)
    page.mouse.down()
    page.mouse.move(x + w * .88, y + h * .70, steps=6)
    page.mouse.up()
    strokes = page.evaluate("attempt.cells[selectedCell].strokes")
    assert len(strokes) == 1
    assert abs(strokes[0][0][0] - .70) <= .003
    assert abs(strokes[0][-1][0] - .88) <= .003
    assert abs(strokes[0][-1][1] - .70) <= .003
    return strokes


def check_review(page, label, measurements):
    prepare(page)
    page.wait_for_function("hkKaiState21==='ready'")
    page.evaluate("document.fonts.ready")
    assert page.evaluate("document.fonts.check('100px \"Penroom HK Kai\"','老實審視一')")
    for n, ch in enumerate(CHARS):
        ghost = page.locator(".grid .ghost").nth(n)
        assert ghost.inner_text() == ch
        measurements.append(ink_bounds(ghost, f"{label}-small-{ch}"))
    page.locator('[data-c="0"]').click()
    for n, ch in enumerate(CHARS):
        if n:
            page.locator("#pdNext").click()
        page.wait_for_function("document.querySelector('#pad .ghost svg') !== null")
        ghost = page.locator("#pad .ghost")
        assert ghost.inner_text() == ch
        measurements.append(ink_bounds(ghost, f"{label}-large-{ch}"))
    page.locator('[data-m="0"]').click()
    strokes = draw_right(page)
    # A font completion refresh must preserve the DOM canvas, bitmap, raw ink and capture.
    page.evaluate("""() => document.querySelector('#pdCv').addEventListener('pointerdown',
      e=>window.testPointer=e.pointerId,{once:true})""")
    box = page.locator("#pdCv").bounding_box()
    page.mouse.move(box['x'] + box['width'] * .6, box['y'] + box['height'] * .2)
    page.mouse.down()
    page.evaluate("""() => {
      window.testCanvas=document.querySelector('#pdCv');
      window.testBitmap=testCanvas.toDataURL();
      document.fonts.dispatchEvent(new Event('loadingdone'));
    }""")
    page.wait_for_function("document.querySelector('#pad .ghost svg') !== null")
    assert page.evaluate("testCanvas===document.querySelector('#pdCv') && testBitmap===testCanvas.toDataURL() && testCanvas.hasPointerCapture(testPointer)")
    page.mouse.move(box['x'] + box['width'] * .65, box['y'] + box['height'] * .4, steps=3)
    page.mouse.up()
    assert len(page.evaluate("attempt.cells[0].strokes")) == 2
    page.locator("#pdUndo").click()
    assert page.evaluate("attempt.cells[0].strokes") == strokes
    page.locator("#pdNext").click()
    page.locator("#pdPrev").click()
    assert page.evaluate("attempt.cells[0].strokes") == strokes
    assert page.locator("#pad .ghost").inner_text() == "老"
    # Erase and undo via existing controls; clear and undo retain original raw points.
    page.locator("#pdEr").click()
    box = page.locator("#pdCv").bounding_box()
    page.mouse.click(box['x'] + box['width'] * .79, box['y'] + box['height'] * .50)
    assert page.evaluate("attempt.cells[0].strokes") != strokes
    page.locator("#pdUndo").click()
    assert page.evaluate("attempt.cells[0].strokes") == strokes
    page.locator("#pdPen").click()
    page.locator("#pdClr").click()
    assert page.evaluate("attempt.cells[0].strokes") == []
    page.locator("#pdUndo").click()
    assert page.evaluate("attempt.cells[0].strokes") == strokes
    page.locator("#pdClose").click()
    page.locator("#next").click()
    assert page.locator(".grid .ghost").first.inner_text() == "老"
    page.locator("#prev").click()
    assert page.evaluate("attempt.cells[0].strokes") == strokes
    page.locator("#later").click()
    page.locator("#resume").click()
    assert page.evaluate("attempt.cells[0].strokes") == strokes
    assert page.evaluate("JSON.parse(localStorage.getItem(KEY+'-draft-'+user.studentId)).cells[0].strokes") == strokes
    assert page.evaluate("""async () => {
      const db=await inkDB5();
      const entry=await new Promise((resolve,reject)=>{
        const r=db.transaction('entries').objectStore('entries').get('draft:'+user.studentId);
        r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);
      });return JSON.stringify(entry.value.cells[0].strokes)===JSON.stringify(attempt.cells[0].strokes);
    }""")
    page.locator('[data-c="0"]').click()
    page.screenshot(path=str(ARTIFACTS / f"{label}.png"))
    other = {"width": 1024, "height": 768} if label == "portrait" else {"width": 768, "height": 1024}
    page.set_viewport_size(other)
    page.wait_for_timeout(400)  # Existing resize debounce is 250ms.
    assert page.evaluate("attempt.cells[0].strokes") == strokes
    measurements.append(ink_bounds(page.locator("#pad .ghost"), f"{label}-rotated-老"))
    print(f"PASS {label}: five glyphs in both sizes, navigation, coordinates, font refresh, draft and rotation")


def check_hidden_answers(page, mode):
    prepare(page, mode)
    for big in (False, True):
        if big:
            page.locator('[data-c="0"]').click()
        host = page.locator("#pad" if big else "#app")
        assert host.locator(".ghost,.ref,.edb-links21,[data-edb-char]").count() == 0
        text = host.inner_text()
        assert not any(ch in text for ch in HIDDEN_CHARS), (mode, big, text)
        for ch in HIDDEN_CHARS:
            assert not host.locator(f'[aria-label*="{ch}"],[title*="{ch}"]').count()
        if mode == "memory":
            assert host.locator("#listen,#cellRead,#pdListen,#pdCellRead").count() == 0
    page.locator("#pdClose").click()
    page.locator("#sub").click()
    assert not any(ch in page.locator("#modalBody").inner_text() for ch in HIDDEN_CHARS)
    assert page.evaluate("attempt.created") == ""  # Never submit a paper.
    page.locator("#cont").click()
    print(f"PASS {mode}: no displayed answers in small/large cells or submission confirmation")


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    check_syntax()
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    measurements = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or shutil.which("chromium"),
                                        args=["--no-sandbox"])
            for label, viewport in (("portrait", {"width": 768, "height": 1024}),
                                    ("landscape", {"width": 1024, "height": 768})):
                context = browser.new_context(viewport=viewport, device_scale_factor=2)
                context.route("**/*", lambda r: r.continue_() if r.request.url.startswith(origin + "/") else r.abort())
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                response = page.goto(origin + "/", wait_until="domcontentloaded")
                assert response.status == 200
                check_review(page, label, measurements)
                for mode in ("dictation", "memory", "random"):
                    check_hidden_answers(page, mode)
                assert not errors, errors
                context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    (ARTIFACTS / "measurements.json").write_text(json.dumps(measurements, ensure_ascii=False, indent=2))
    print(f"PASS all checks; {len(measurements)} raster measurements; artifacts: {ARTIFACTS}")


if __name__ == "__main__":
    main()
