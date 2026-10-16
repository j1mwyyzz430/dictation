# 筆尖默書室維護指引

- 用繁體中文溝通，先說實際結果和使用者下一步。節省用量，不啟動多個代理。
- 先讀 `docs/PROGRESS.md`、`docs/PROJECT_HANDOFF.md`；詳細背景在 `handoff/CODEX_HANDOFF.md`。交接文件的歷史任務不等於每輪都要重做。
- 正式前端入口為根目錄 `index.html`，是單檔 HTML/CSS/JavaScript；`handoff/index.html` 是候選參考檔，不是發布入口。不得用候選整檔覆蓋正式版本。
- 架構維持免費 GitHub Pages → Google Apps Script → 私人 Google Sheet。保留 `PUBLISHED_ENDPOINT` 和現有表單 POST／iframe／postMessage 請求方式。
- 在工作分支修改，交給使用者檢查；沒有明確要求不合併或部署。雲端任務已隔離，沿用既有 checkout，不另建 worktree，除非使用者要求。
- 不清空 Sheet、不重設學生或老師密碼、不執行 `setup`、`migrateV5`、`upgradeV6` 或密碼遷移。不要向正式學生帳戶提交測試卷。
- GitHub 權限不代表 Apps Script／Sheet 權限。`backendSource` 只是嵌入的參考程式；真的要改後端時才索取**目前部署的完整 Code.gs**。不能把 seed 資料寫回正式後台。
- 不將真實學生資料、密碼或憑證新增至原始碼、文件或測試。測試使用虛構資料並阻擋外部請求。
- 保留四位數字 PIN（含前導 0）、固定 studentId、4N→4B 歷史相容、grade/classId 分離、課次版本／封存、多段選擇、筆跡／草稿／補交及排名規則。
- 新卷計分：詞語30、句子30、段落／背默40；隨機詞語每正確字3分、句子／段落2分；舊卷沿用舊規則。不恢復字形完整度檢測。
- 保留暖米白介面、WenKai 介面字體、香港楷書參考字及未收錄字提示、粵語限定與 reduced-motion。教育局查字沿用表單 POST。
- 單檔有 Base／Pre21／V5／V6 多代函式，先確認最後生效定義及呼叫鏈。溫習參考字的置中只處理 `.ghost`；字體事件不能重建書寫 canvas。
- 不修改 `.paper`、`#pdPaper`、`#pdCv` 的幾何動畫、`bindPad` 正規化座標、pointer capture 或原始筆跡。若任務確實涉及它們，須做相應瀏覽器驗證。
- 香港楷書 WOFF2 約2.55 MB，Base64 約3.40 MB；用完整檔案比較／雜湊確認保留，閱讀時省略大型編碼及字元覆蓋表。不任意拆分或重編字體。
- 插入腳本要定位最外層文檔；內嵌後端字串也含 `</body></html>`，禁止全域替換。保留字體作者、來源和 CC BY 4.0 鳴謝，見接手文件。

## 執行與局部驗證

在倉庫根目錄執行：

```sh
python3 -m http.server 8000 --bind 127.0.0.1
python3 tests/check_reference.py
python3 tests/check_word_sections.py
git diff --check
```

測試自啟另一個暫時本機伺服器，需 Python Playwright、Pillow、Node 及 Chromium；可用 `CHROMIUM_PATH` 指定瀏覽器。輸出預設在 `/tmp/dictation-reference-checks`。沒有前端套件安裝／編譯步驟。不要建立面向使用者的 localhost 預覽連結。

只跑與改動有關的測試；確認實際執行的結果，不把語法檢查等同後端或 iPad 實測。結束或中斷前更新 `docs/PROGRESS.md`，寫明修改、已驗證／未驗證項目及下一步。

詞語分組使用 `wordSections` 的1起算範圍，保留 `words`／`wN`，只篩選溫習。即時系統分數上榜是已授權的新需求，尚待現行 Code.gs，狀態以 `docs/PROGRESS.md` 為準。
