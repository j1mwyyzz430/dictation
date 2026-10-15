# 工作進度

## 2026-10-15：香港楷書置中整合

工作分支：`fix/hk-kai-ink-centering`；起點 `f5152e3`，與檢查時遠端 main 相同。原工作目錄乾淨。尚未合併或部署。

### 已完成

- 讀取詳細交接、候選及正式入口，比較完整檔案；大型 Base64／字元表用完整資料比對，沒有逐行輸出。原倉庫沒有 AGENTS.md。
- 原兩檔只差 `ghostAlign21Style`、`ghostAlign21Script`，共30新增行。局部匯入正式入口，沒有整檔覆蓋或新增重複覆寫層；候選原檔未修改。
- 確認 `writingView → writingViewBase`、`renderPad → renderPadBase → bindPad／fitPadUI` 等實際呼叫鏈，記入接手文件。
- 以逐位元組與 SHA256 核對：原 `appScript`、`backendSource`、`hkKai21Style` 完全保留，因此現有計分、排名、帳戶、資料、PUBLISHED_ENDPOINT、座標及筆跡邏輯沒有改動。
- 新增 `AGENTS.md`、`docs/PROJECT_HANDOFF.md`、本文件及 `tests/check_reference.py`；更新 README 入口指引。
- 從嵌入字體 metadata 核實 Free HK Kai 4700 v1.01、自由香港字型及 CC BY 4.0，補記來源和鳴謝。
- 首載分析及更新／還原步驟已記錄。HTML 約3.78 MB，字體 Base64 約90%；本輪未拆分字體／架構。

### 驗證結果

執行 `python3 tests/check_reference.py` 全部通過。環境：Chromium 154.0.8037.57、Python 3.12.14、Node 24.19.0；直向768×1024及橫向1024×768，device scale factor 2。使用虛構本機預覽帳戶，阻擋全部外部請求，沒有提交任何試卷。

| 檢查 | 結果 |
| --- | --- |
| 正式／候選 HTML 腳本語法 | 各3個 script，包含內嵌後端，Node 語法檢查通過；置中腳本只一段且未落入後端字串 |
| 老、實、審、視、一 | 實際瀏覽器墨跡截圖量測，大小格×直橫向20次，另加旋轉2次，共22次；最大中心偏差0.44%，低於2%門檻 |
| 「一」自然比例 | 高／寬約0.183，沒有拉成正方形 |
| 回歸對照 | 基準版同一組小格的垂直中心偏差8.37%–10.35%，確實不能通過同一2%門檻 |
| 右半邊落筆 | mouse pointer 實際落筆，x=0.70→0.88、y終點0.70，儲存正規化座標誤差≤0.003 |
| 字體完成事件 | 模擬 `document.fonts.loadingdone` 時持續落筆，canvas 節點、bitmap 及 pointer capture 保持，筆畫可完成；不是 iPad 觸控實測 |
| 換格／縮圖／換頁 | 參考字跟隨實際字格，上一格／下一格及跨頁後原始 strokes 相同 |
| 擦膠、清空、復原 | 操作後筆跡有相應變化，復原精確回到原始座標 |
| 草稿 | 稍後繼續／恢復、localStorage 與 IndexedDB 都保留原始 strokes |
| 旋轉 | 直→橫及橫→直，既有250ms resize後筆跡保留，參考字仍置中 |
| 交卷前答案 | 默寫、背默、隨機模式的小格、大板、交卷確認窗不顯示測試答案；背默無內容朗讀控制 |
| 瀏覽器錯誤／差異格式 | 無 pageerror；`git diff --check` 通過 |

截圖與量測輸出在 `/tmp/dictation-reference-checks`（不提交到網站）；重跑測試可重建22筆量測及兩張大板截圖。基準對照另存在該目錄的 `baseline.json`。

### 未驗證／下一步

- 使用者檢查工作分支後，以 iPad Safari／Apple Pencil 實測觸控、手掌防誤觸、粵語朗讀及上述畫面；本輪只有桌面 Chromium 模擬尺寸和 mouse pointer。
- GitHub Pages 設定 API 回應 Forbidden；推算的 Pages 網址被代理403阻擋。需在 GitHub Settings → Pages 確認真正發布分支／目錄，不能把預設 main 視作已確認的 Pages 設定。
- 沒有正式 Apps Script／私人 Sheet 的部署原始碼及資料存取；正式登入、收卷、排名和學校網路冷／暖載入未實測。本輪純前端修改，Apps Script 不需重新部署。
- 外部 Google Fonts 在隔離測試中阻擋，因此未驗證線上介面字體下載；內嵌香港楷書已實際載入並量測。
- 後續先量測 HTML／外部字體／bootstrap／登入各段時間，再決定可快取的字體分檔；另可校正網站設定內的舊 Hanzi Writer 文案及可見字體鳴謝。
- 更新及還原見 `PROJECT_HANDOFF.md`。不清空 Sheet、不重設密碼、不執行 setup 或遷移，不自動合併到正式發布分支。
