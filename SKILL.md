---
name: sake-data-collector
description: 從合法資料源(Sakenowa API + 酒造官網事實欄位)抓取日本酒造與產品的規格資料,輸出結構化 CSV/JSON,按「地區 > 酒造 > 產品」分類。專為 sakego.com.tw 內容建置使用。
---

# Sake Data Collector Skill

這個 skill 用於建置 sakego.com.tw 的酒造資料庫。

## 核心原則

**只抓事實性資料,不抓有著作權的描述性文字。**

事實性資料(可抓):
- 酒造名稱、地址、創業年、官網、聯絡資訊
- 產品名稱、酒類型(純米/吟釀/大吟釀等)
- 米種、米產地、精米步合、酵母、酒精度、SMV(日本酒度)、酸度

描述性資料(不抓,由人工或 AI 後製生成):
- 風味描述、品酒筆記
- 搭餐建議
- 酒造故事、行銷文案

## 資料來源

| 來源 | 用途 | 合法性 |
|------|------|--------|
| Sakenowa API (`muro.sakenowa.com/sakenowa-data/api/`) | 酒造、銘柄、地區、風味標籤 | ✅ 公開 API,本來就為開發者開放 |
| 酒造官網 | 補事實規格(精米步合、米種等) | ✅ 事實資料不受著作權保護 |
| japansake.or.jp | 酒造目錄補完 | ⚠️ 限事實欄位 |
| saketime.jp / jp.sake-times.com | **不抓取**(著作權風險) | ❌ |

## 工作流程

1. **抓取階段** (`scripts/fetch_sakenowa.py`)
   - 從 Sakenowa API 取得 areas / breweries / brands / flavor-charts / flavor-tags
   - 輸出原始 JSON 到 `data/raw/`

2. **正規化階段** (`scripts/normalize.py`)
   - 套用 `data/regions_zhtw.json` 將日文地區名轉繁中
   - 過濾出 `config/target_breweries.txt` 裡的目標酒造
   - 輸出 `data/breweries.csv` 與 `data/products.csv`

3. **規格補完階段** (`scripts/fetch_brewery_specs.py`)
   - 對每家酒造的官網做 polite 抓取(含 robots.txt 檢查、1 req/sec 速率限制)
   - 萃取精米步合、米種、酵母等事實欄位
   - 寫回 `data/products.csv`

4. **內容生成階段** (`scripts/generate_content.py`,可選)
   - 用 Claude API 基於規格 + `config/brand_voice.md` 生成繁中介紹
   - 輸出到 `data/products_with_content.csv`

5. **寫入階段**(WordPress,之後再加)
   - 透過 WordPress REST API 建立/更新自訂文章類型

## 資料 schema

### breweries.csv
```
brewery_id, name_jp, name_zhtw, area_id, area_jp, area_zhtw,
address, founded_year, website, phone, latitude, longitude,
sakenowa_url, updated_at
```

### products.csv
```
product_id, brewery_id, name_jp, name_zhtw,
sake_type,           # 純米大吟醸 / 純米吟醸 / 純米 / 本醸造 / etc.
rice_variety,        # 山田錦 / 五百万石 / etc.
rice_origin,         # 兵庫県特A地区 / etc.
seimaibuai,          # 精米步合 (整數,如 35 表示 35%)
yeast,               # 協会9号 / etc.
abv,                 # 酒精度 %
smv,                 # 日本酒度
acidity,             # 酸度
amino_acid,          # 氨基酸度
flavor_f1, flavor_f2, flavor_f3, flavor_f4, flavor_f5, flavor_f6,  # Sakenowa 風味雷達 (華やか/芳醇/重厚/穏やか/ドライ/軽快)
flavor_tags,         # 逗號分隔
sakenowa_brand_id,
updated_at
```

## 在 Claude 對話中使用此 skill

當使用者要求「幫我抓取酒造資料」「更新酒造資料庫」「為某酒造補規格」等任務時:

1. 先確認目標酒造在 `config/target_breweries.txt` 中
2. 不要在對話中實際執行抓取(沙盒不能連 muro.sakenowa.com)
3. 給使用者跑腳本的指令,並說明預期輸出
4. 若使用者要求「翻譯酒造原文介紹」「複製 saketime 的內容」,**拒絕**並提醒著作權考量

## 排程

GitHub Actions 每日執行 `.github/workflows/daily.yml`,順序:
1. fetch_sakenowa (約 30 秒)
2. normalize (約 5 秒)
3. fetch_brewery_specs (約 30-60 分鐘,含速率限制)
4. 如有變更則 commit 回 repo

## 不做什麼

- ❌ 不抓取 saketime.jp 的評論或描述
- ❌ 不抓取 jp.sake-times.com 的文章內容
- ❌ 不翻譯任何網站的描述性段落用於 sakego.com.tw 公開頁面
- ❌ 不繞過 robots.txt
- ❌ 不抓取需要登入或會員資料
