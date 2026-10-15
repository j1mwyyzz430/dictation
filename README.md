# 筆尖默書室

香港小學默書網站：單檔前端 `index.html`，使用 GitHub Pages、Google Apps Script 與私人 Google Sheet。

- [維護指引](AGENTS.md)
- [專案接手、字體鳴謝及更新／還原](docs/PROJECT_HANDOFF.md)
- [本輪進度與測試結果](docs/PROGRESS.md)
- [原始詳細交接](handoff/CODEX_HANDOFF.md)；`handoff/index.html` 是參考候選，並非正式入口。

在倉庫根目錄啟動本機靜態伺服器：

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

局部測試：`python3 tests/check_reference.py`（需 Node、Chromium、Python Playwright、Pillow）。測試使用虛構本機資料並阻擋外部請求，不會提交正式試卷。此專案沒有編譯步驟。

發布前須經使用者檢查；不要執行後端 setup／遷移或重設任何帳戶。
