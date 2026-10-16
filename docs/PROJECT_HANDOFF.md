# 筆尖默書室接手紀錄

## v2.2 詞語分組及暫定排名（2026-10-16）

`feat/word-sections-and-provisional-ranking` 新增教師詞語分組及學生溫習選課。教材保留 `words` 原陣列，另以 `wordSections:[{title,start,end}]` 記錄1起算的連續區間。範圍不可重疊；未分配詞語仍可選。新增／刪除／調動原詞語後老師須重新核對範圍。

實際呼叫鏈：`tContent → renderWordEditor22`，`collect → collectWordSections22`，`storeConfig → validateWordSections22 / verifyWordSectionsSaved22`；`readyView → renderWordChoices22`，本機溫習 `startAttempt → selectReviewWords22`。保留 `wN` keys、讀音、歷史 snapshot 和所有原考試模式。分組只限溫習，不改計分範圍。

老師在課次設定中填四篇課文名稱與各自詞語起止位置，保存後學生可單課、多課或全部溫習。尚未取得真實六年級課文邊界，沒有自動把40詞均分或寫入正式教材。後台須原樣保存並回傳 metadata；若丟失會顯示錯誤。真實後台函式搭配模擬儲存的測試已通過，正式 Google 保存尚未驗證。

使用者已提供與原嵌入版本一致的現行 Code.gs。2.2 已局部修改兩份 `rankSummaries`，容許未覆核卷，以 `metrics.points` 入榜；人工改分經 `storeAttempt5_` 覆寫摘要及失效快取。`provisionalCount` 標示暫定卷數。保留零正確字、排除排名、不完整及練習卷的排除條件；舊未覆核卷也會按同一規則入榜。後台 `board5_` 使用 `rank22` 快取，公開設定提供 `backendVersion` 供前端相容處理。發布進度見 `PROGRESS.md`；更新與回復見 `RELEASE_2.2.md`。

## 入口、版本與發布

- 最新交付：2.2 功能提交 `e43c509` 已依授權推送 `main`；更新前版本保存在遠端 `backup/pre-v2.2-20261016-e152ae5`，保留香港楷書置中。更早的 pre-centering 備份仍在。Pages 完成狀態因網路403尚未確認；Google 後台須使用者部署，詳見 `PROGRESS.md`。
- 倉庫：`j1mwyyzz430/dictation`。本輪基準 `f5152e3ec08b53f5c626bcfb2df54e0efa9eb723`；檢查時遠端預設分支及 `main` 都指向此提交。
- 根目錄 `index.html` 是網站入口；`handoff/index.html` 是未部署候選。倉庫沒有 package manifest、建置腳本、GitHub Actions workflow、CNAME 或原有自動化測試。
- 原始兩檔逐位元組差異只有 `ghostAlign21Style`、`ghostAlign21Script`（30新增行）；其他內容相同。本輪只匯入這兩個區塊，保留原入口的全部既有內容。
- GitHub Pages 架構由使用者及交接文件確認；**Pages 後台所選分支／目錄尚未確認**：`gh api repos/j1mwyyzz430/dictation/pages` 回應 Forbidden；依倉庫名稱推算的 Pages 網址也被網路代理以403阻擋。不能據此宣稱線上版本已核對或測得首載速度。
- 發布前在 GitHub **Settings → Pages** 確認既有來源。若為 `main / (root)`，檢查後合併工作分支才會觸發該來源更新；若是其他來源，沿用實際設定，不任意改 Pages 設定。

## 架構與真正生效的程式

所有前端樣式及程式在 `index.html`，沒有本機後端。`request(action,payload,token)` 建立隱藏表單，POST 至既有 `PUBLISHED_ENDPOINT`，以 iframe 接收 Google Apps Script 的 `penroom-v1` postMessage。超時為180秒。開頁呼叫 `bootstrap`；登入後按需載入排名及答卷。後端帳戶／教材／歷史資料以部署中的 Apps Script 和私人 Sheet 為準。

| 區域 | 實際呼叫鏈／來源 |
| --- | --- |
| 路由 | `render` → `renderBase` → 各畫面最終函式 |
| 登入／選課 | `loginView` → `loginViewPre21`；`lessonView` 以 grade 選 published 課次 |
| 開卷 | `readyView` → `readyViewPre21`；最後的 `startAttempt` 建立 snapshot，正式默寫以 `start` API 取得 |
| 小格 | `writingView` → `writingViewBase`，只有 `attempt.mode==='review'` 建立 `.ghost` |
| 大書寫板 | `openPad` → `renderPad` → `renderPadBase` → `bindPad`，最後由 `fitPadUI` 定尺寸 |
| 換格／換頁 | `padGo`／縮圖重建大板；`goPage` → `goPageBase`；既有正規化 strokes 再繪 |
| 筆跡 | `bindPad` 按 canvas 實際 client rect 算 0–1 座標，處理 pen/touch、capture、擦膠；`paintCanvas` 繪筆跡 |
| 草稿 | **最後定義**的 `persistDraft`／`draft5` 使用記憶體快取、localStorage、IndexedDB `penroom-ink-v5`；`restoreInk5` 恢復資料 |
| 參考字體 | `hkKai21Style` 內嵌 WOFF2，`hkKaiState21`／`refreshKaiStatus21` 更新狀態；最後的 `loadChar` 直接回 null，`refGlyph` 用參考字體，不再依賴逐字 Hanzi CDN |
| 置中（新增） | `ghostAlign21Script` 觀察新增 `.ghost`，Canvas `measureText` 取實際墨跡邊界，SVG 等比例置中，長邊目標82%，縮放上限1.15；字體完成只刷新參考字 |
| 計分／交卷 | 最後 `marks` 用 scoreRule 判斷 v6／舊規則；`finishAttempt` 先持久保存原始筆跡，再 `syncAttempt` → `syncAttemptV5`，停用完整度檢測 |

`backendSource` 是 `type="text/plain"` 的 Apps Script 參考程式，不在瀏覽器執行。內含舊代及新代程式，**不保證等於現行部署**；不得拿 seed／舊函式推定正式行為。本輪 `appScript`、`backendSource`、整個 `hkKai21Style` 都與基準逐位元組相同。

常用 API：`bootstrap`、`studentLogin`、`teacherLogin`、`start`、`submit`、`myAttempts`、`attempt`、`leaderboard`、`teacherAttempts`、`review`、`teacherStudents`、`saveStudent`、`importStudents`、`saveStudentNumbers`、`saveConfig`。本輪沒有對正式後台執行它們；不需要重新部署 Apps Script。

## 保留的功能及規則

- 四位數字 PIN、前導0、首次設定／老師重設／停用、固定 studentId、批量匯入和學號排序；4N→4B 歷史相容，6A／6B 同年級共用教材。
- 課次發布、封存及歷史版本；獨立讀默／背默多段、段落命名和選段。
- 溫習、聽音默寫、背默、隨機測試；交卷前默寫／背默不顯示答案，背默沒有內容朗讀。
- 粵語、標點及單格／小段朗讀；手指／Pencil、擦膠、復原、大小格、原始筆跡、計時／離開記錄、草稿及不重複補交。
- Google 手寫辨識與教師覆核；新卷30／30／40、背默40，隨機每正確字3／2／2，舊卷依原規則；按年級總榜／香港週一開始週榜，覆核後才計排名。
- 首頁排名、進步卡、成果、錯字重練；暖色介面與 WenKai、觸控友善及 reduced-motion。更細節見原交接文件及上述最終函式。

## 字體鳴謝與首次載入

參考字形為 **Free HK Kai (4700 characters)／自由香港楷書（4700字），版本1.01**，© 2016 **Free Hong Kong Fonts／自由香港字型**。來源：[自由香港字型](https://freehkfonts.opensource.hk/)，授權：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。名稱、版本、作者、來源及授權已從保留的 WOFF2 name table 核對；字體資料及內嵌版權資訊未修改。本輪只改網頁參考字的顯示位置，不修改字形，也不代表教育局背書或提高 Google 辨識準確度。

本輪檔案大小量測（不代表線上傳輸量或耗時）：

| 項目 | 大小 |
| --- | ---: |
| 修改後 HTML | 3,778,807 bytes |
| 內嵌 WOFF2 Base64 | 3,403,728 bytes（約90.07%） |
| WOFF2 解碼後 | 2,552,796 bytes |
| 整份 HTML 本機 gzip | 2,705,462 bytes（僅估算，非線上回應） |

開頭還有 Google Fonts 外部樣式表（Fredoka、LXGW WenKai TC、Noto Sans HK），可能增加首次網路等待；大段嵌入字體在應用腳本之前，HTML 傳輸／解析也要付出成本。`font-display:swap` 允許後備字體先出現。開頁的 `bootstrap` 與後續登入是獨立後台請求，失敗可等180秒；不能把後台等待全歸因於字體。

後續先在實際 iPad／學校網路量測冷／暖載入：HTML TTFB／下載、外部 CSS／字體、香港楷書 ready、bootstrap／studentLogin 分別耗時，再決定是否把字體移至同站可快取、有版本檔名的 WOFF2。拆分需保留授權、涵蓋字元、後備提示及部署相對路徑，本輪不實作。網站「使用注意」仍有舊 Hanzi Writer 說明、`.hk-kai-credit` 只有樣式而無可見鳴謝元素，後續可校正文案；現有字體版權資訊及本文件鳴謝已保留。

## 驗證與更新／還原

執行 `python3 tests/check_reference.py`：自啟靜態伺服器，使用虛構的本機預覽帳戶，阻擋所有外部網路，不交正式卷。需 Node、Chromium、Python Playwright 和 Pillow（本雲端環境已提供）。可用 `CHROMIUM_PATH` 指定 Chromium。結果／截圖預設輸出 `/tmp/dictation-reference-checks`，詳細覆蓋範圍與結果見 `PROGRESS.md`。

使用者檢查後才更新：

1. 打開工作分支／PR，確認 `index.html` 只新增兩段置中區塊，文件及測試是獨立檔案。
2. 在 iPad Safari 用溫習檢查「老、實、審、視、一」、大小格、旋轉、落筆、擦膠、復原及草稿；正式驗收前不合併。
3. 確認 Settings → Pages 的既有來源，才合併／按既有方式發布根目錄 `index.html`，等待 Pages 建置完成再重新載入。手動上傳者只更新根目錄入口，不以 handoff 檔覆蓋。
4. **Apps Script 不用重新部署；不執行 setup、遷移或清除任何資料。**
5. 需要還原時，在 GitHub 對本次 PR／修正提交做 Revert，經檢查後發布還原提交；不要 reset/force-push 整個 main，也不要覆蓋之後其他人的修改。若尚無其他修改，`f5152e3` 是本輪前端基準。這次修正沒有改資料格式，還原前端不需處理 Sheet。
