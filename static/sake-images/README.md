# 銘柄照片資料夾

每張圖片**自動套用到三個位置**:
1. **首頁銘柄英雄榜**:小縮圖 70×95px(自動裁切)
2. **酒造頁的銘柄卡片**:中尺寸 280×200px(自動 contain)
3. **銘柄詳細頁的 Hero**:大尺寸 260×340px(完整顯示)

**你只需要上傳一張高解析度照片**,三個位置自動縮放。

## 📐 規格建議

| 項目 | 規格 |
|------|------|
| **建議尺寸** | 600 × 800 px (寬 × 高) |
| 比例 | 3:4 直式 (配合日本酒瓶) |
| 格式 | `.jpg` / `.jpeg` / `.png` / `.webp` |
| 檔案大小 | 50-200 KB (壓縮後) |

## 📁 命名規則

檔案名 = 該銘柄的 `product_id`,例如:

```
sake-images/
├── sn_5482.jpg      ← 獺祭 純米大吟釀 23
├── sn_3210.jpg      ← 八海山 純米吟釀
├── sn_891.jpg       ← 十四代 中取大吟釀
└── ...
```

## 🔍 怎麼找對應的 product_id?

1. **看網址**:打開銘柄詳細頁,網址最後是 `.../products/sn_xxxx.html`,`sn_xxxx` 就是 ID
2. **看資料**:打開 `data/products.csv` 第一欄就是 product_id
3. **看 hover 提示**:在沒圖的銘柄頁,滑鼠移到設計卡上,下方會浮出 ID

## ⚙️ 自動偵測機制

- 系統會掃描這個資料夾
- 找到對應 `product_id.{jpg|jpeg|png|webp}` → 顯示真圖
- 找不到 → 顯示 CSS 設計卡片(預設)

**不用改任何程式碼,放圖檔即可。**

## ⚖️ 著作權注意

只放你**有權使用**的圖片:
- ✅ 自己拍的照片
- ✅ 酒造正式授權的圖片
- ✅ 進口商提供的官方圖
- ✅ CC0 / Public Domain
- ❌ Google 搜尋下載
- ❌ 從酒造官網直接抓
- ❌ 其他電商平台的圖

## 🎨 壓縮工具

- [TinyPNG](https://tinypng.com/) - 免費線上壓縮
- [Squoosh](https://squoosh.app/) - Google 出品,可轉 WebP
- [ImageOptim](https://imageoptim.com/) - Mac 桌面版

## 💡 批次上傳

要傳很多張時用 GitHub Desktop 最快:
1. 把所有圖片放到本機 `static/sake-images/` 資料夾
2. 確認檔名是 `{product_id}.jpg`
3. GitHub Desktop 自動偵測 → Commit + Push
