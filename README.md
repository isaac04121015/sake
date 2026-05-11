# Sakego 日本酒資料採集系統

為 [sakego.com.tw](https://www.sakego.com.tw) 建置的日本酒造與產品資料採集 / 內容生成 / 發布系統。

## ⚖️ 設計原則

**只抓事實性資料,不抓有著作權的描述性文字。**

- ✅ Sakenowa API(公開資料)
- ✅ 酒造官網的事實規格欄位(精米步合、米種、酵母等)
- ❌ saketime.jp / jp.sake-times.com 的評論與描述(著作權風險)
- ❌ 翻譯任何網站的描述性文字到 sakego.com.tw

繁中介紹、風味描述、搭餐建議由 Claude API 基於規格 + 你的品牌語調**重新撰寫**。

## 📁 專案結構

```
sake-skill/
├── SKILL.md                          # Claude 對話用的 skill 文件
├── README.md                         # 你正在讀的這個
├── requirements.txt                  # Python 依賴
├── scripts/
│   ├── fetch_sakenowa.py             # 抓 Sakenowa API
│   ├── normalize.py                  # 過濾目標 + 輸出 CSV/JSON
│   ├── fetch_brewery_specs.py        # 補酒造官網規格(可選)
│   ├── generate_content.py           # Claude 生成繁中內容(可選)
│   └── publish_to_wordpress.py       # 同步到 WP(可選)
├── config/
│   ├── target_breweries.txt          # 166 家目標酒造清單(可編輯)
│   └── brand_voice.md                # 你的品牌語調(請編輯)
├── data/
│   ├── regions_zhtw.json             # 47 都道府縣繁中對照(已備好)
│   ├── brewery_websites.csv          # 酒造官網對照(請補完)
│   ├── raw/                          # Sakenowa API 原始 JSON
│   ├── breweries.csv / .json         # 酒造主表(輸出)
│   ├── products.csv / .json          # 產品主表(輸出)
│   ├── products_with_content.csv     # 含繁中介紹(輸出)
│   └── _match_report.txt             # 比對報告
├── wordpress/
│   └── sakego-cpt.php                # WP 端 CPT 註冊程式碼
└── .github/workflows/
    └── daily.yml                     # GitHub Actions 排程
```

## 🚀 快速開始

### 第一次使用(本機跑)

```bash
# 1. clone 並安裝依賴
git clone <your-repo>
cd sake-skill
pip install -r requirements.txt

# 2. 抓 Sakenowa API
python scripts/fetch_sakenowa.py

# 3. 正規化 + 過濾出 166 家目標酒造
python scripts/normalize.py
# → data/breweries.csv / products.csv 已產生
# → 看 data/_match_report.txt 確認比對結果

# 4. (可選) 用 Claude 生成繁中介紹 - 先試 5 筆
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/generate_content.py --max 5

# 5. 看 data/products_with_content.csv 是否符合預期
#    若不滿意,編輯 config/brand_voice.md 後重跑

# 6. 滿意後跑全部
python scripts/generate_content.py
```

### 設定 GitHub Actions 自動排程

1. 把整個專案 push 到 GitHub repo(可設為 private)
2. 在 repo 的 **Settings → Secrets and variables → Actions** 加入:
   - `ANTHROPIC_API_KEY`(從 console.anthropic.com 取得)
   - `WP_BASE_URL` = `https://www.sakego.com.tw`
   - `WP_USERNAME` = 你的 WP 管理員帳號
   - `WP_APP_PASSWORD` = WP 後台 → 個人資料 → 應用程式密碼產生的密碼
3. 排程已設定為 **每天 UTC 19:00 = 台灣 03:00**
4. 也可在 **Actions** 頁面手動觸發 `Daily Sake Data Sync`

### 設定 WordPress

1. 把 `wordpress/sakego-cpt.php` 內容貼到主題的 `functions.php`
   或包成外掛:`/wp-content/plugins/sakego-cpt/sakego-cpt.php`
2. 後台會出現「日本酒」選單(CPT 已註冊)
3. 在 WP 後台 **使用者 → 個人資料** 拉到底部產生「應用程式密碼」
4. 拿這個密碼設定到 GitHub Secrets `WP_APP_PASSWORD`

## 📊 各腳本詳細說明

### `fetch_sakenowa.py`
從 Sakenowa Data Project 抓 7 個 API 端點,輸出 raw JSON。
**速度**:約 30 秒。**沒有規格欄位**(精米步合、米種等)。

### `normalize.py`
讀 raw JSON + 目標清單 → 過濾 + 套繁中地名 → 輸出 CSV/JSON。
**輸出欄位**:見 `SKILL.md` 的 schema 章節。
**比對方法**:銘柄日文名精準匹配 → 酒造名匹配 → 酒造名標準化匹配。
不在 Sakenowa 的酒造會列在 `_match_report.txt`,需手動處理。

### `fetch_brewery_specs.py`(可選)
從酒造官網補規格欄位。**有禮貌的設計**:
- 檢查 `robots.txt`
- 1 req/sec 速率限制
- 自訂 User-Agent 註明來源(`sakego-data-collector/1.0`)
- 失敗的酒造不影響其他

**預期成功率**:30-60%。剩餘需從酒款標籤、進口商目錄手動補。
**前置作業**:需先填好 `data/brewery_websites.csv`(已附範例)。

### `generate_content.py`
用 Claude API 為每款酒生成三段內容:
- `description`(120-180 字產品介紹)
- `tasting_note`(60-100 字品飲建議)
- `pairing`(60-100 字搭餐建議)

**完全基於規格從零撰寫,不翻譯任何網站文字。**
成本估算:~150 家酒造 × 平均 3 款 = 450 筆 × 約 $0.02 = **約 USD $9-10**(用 Opus 4.7)。
若想省錢,把腳本中的 `MODEL` 改成 `claude-haiku-4-5-20251001`,成本降到 1/10 左右。

### `publish_to_wordpress.py`
透過 WordPress REST API 建立/更新 CPT `sake_product`。
**冪等性**:用 `sakenowa_brand_id` meta 當鍵,重複跑不會建出重複文章。
**預設狀態 `draft`**,確認沒問題後改 `--status publish`。

## 🔧 客製化

### 增減目標酒造
編輯 `config/target_breweries.txt`,格式:
```
銘柄日文 | 酒造日文 | 都道府縣
```

### 調整品牌語調
編輯 `config/brand_voice.md`,然後跑:
```bash
python scripts/generate_content.py --regenerate --max 5
```
看效果再決定是否全量重生。

### 換 Claude 模型
編輯 `scripts/generate_content.py` 的 `MODEL` 常數。

## ❌ 不會做的事

- 不會抓取或翻譯 saketime.jp / jp.sake-times.com 的內容
- 不會繞過 robots.txt
- 不會發布為 `publish` 狀態(預設 `draft`,需人工確認後改)
- 不會刪除 WP 上既有但 CSV 沒有的文章

## 📝 待辦 / 已知限制

- [ ] `fetch_brewery_specs.py` 對複雜的酒造官網萃取率有限,建議搭配人工補完
- [ ] `data/brewery_websites.csv` 目前只有約 25 家,需逐步擴充
- [ ] Sakenowa 的銘柄與實際單品(SKU)有時是 1:N 關係,目前以銘柄為單位
- [ ] 沒有圖片抓取(著作權考量),需另行處理產品圖

## 🆘 常見問題

**Q: 跑 `normalize.py` 後好多酒造在 unmatched 怎麼辦?**
A: Sakenowa 的銘柄/酒造名可能用不同寫法(漢字 vs 假名)。看 `_match_report.txt`,
手動修改 `target_breweries.txt` 中對應的銘柄名。

**Q: Claude 生成的內容感覺很制式怎麼辦?**
A: 編輯 `config/brand_voice.md` 加更多範例和具體禁忌詞,然後 `--regenerate`。

**Q: 我想加新的資料來源怎麼辦?**
A: 寫新的 `scripts/fetch_xxx.py`,輸出格式對齊 `products.csv` 欄位,
在 `.github/workflows/daily.yml` 加一個 step。

**Q: 我擔心被酒造官網封 IP**
A: `fetch_brewery_specs.py` 已有 1 req/sec 限制和 robots.txt 檢查。
GitHub Actions 每次 IP 不同,影響有限。若仍擔心,把該 step 拿掉,
完全靠 Sakenowa + 人工補規格也行。
