# 靜態網站建置 + GitHub Pages 部署

這個功能讓你不依賴 WordPress 就能把資料展示在網路上。

## 🌐 你會得到什麼

部署完後,你會有一個公開網址,例如:
- `https://你的GitHub帳號.github.io/sake-data/`(預設子路徑)
- 或自訂網域(例如 `data.sakego.com.tw`,需 DNS 設定)

## 🚀 啟用 GitHub Pages 步驟

### Step 1:把專案推上 GitHub repo

```bash
tar -xzf sake-skill.tar.gz
cd sake-skill
git init
git add .
git commit -m "init"
# 在 github.com 建一個 repo (建議叫 sake-data),然後:
git remote add origin https://github.com/你的帳號/sake-data.git
git branch -M main
git push -u origin main
```

### Step 2:啟用 GitHub Pages

1. 進 repo → **Settings** → 左邊選單 **Pages**
2. **Source** 選擇 **GitHub Actions**(不要選 "Deploy from a branch")
3. 不用按其他按鈕,設定自動儲存

### Step 3:首次觸發 workflow

1. **Actions** 分頁 → 左邊選 `Daily Sake Data Sync` → 右上角 **Run workflow**
2. 等 5-10 分鐘跑完
3. 跑完後回到 **Pages** 設定頁面,會看到網址出現

### Step 4:訪問你的網站

打開 GitHub Pages 顯示的網址,你會看到:
- 首頁:按地區分類的酒造目錄、搜尋框、統計數字
- 點地區 → 看該地區所有酒造
- 點酒造 → 看旗下所有酒款
- 點酒款 → 詳細規格 + 風味雷達(若有 Claude 內容也會顯示介紹/搭餐)

## 🎨 客製化

### 改配色

編輯 `static/styles.css` 最上面 `:root` 區塊的 6 個顏色變數即可:
```css
--primary: #722F37;    /* 主色 */
--secondary: #1A1A1A;  /* 標題 */
--accent: #C9A961;     /* 點綴 */
--bg: #FAF7F0;         /* 背景 */
--text: #2C2C2C;
--border: #E5E0D5;
```

### 改首頁文案

編輯 `templates/index.html.j2`,改完後 commit 推上去,GitHub Actions 會自動重建部署。

### 改網站標題

編輯 `templates/index.html.j2` 找「日本酒造資料庫」,改成你想要的標題。

## 🔧 本機預覽

push 前想先看效果:

```bash
pip install -r requirements.txt
python scripts/build_static_site.py
# 開個簡單 server
cd dist && python -m http.server 8000
# 瀏覽器打開 http://localhost:8000
```

## 🌍 用自訂網域(例如 data.sakego.com.tw)

1. 在 repo 根目錄建立 `static/CNAME` 檔案,內容只有一行:`data.sakego.com.tw`
2. DNS 後台加一筆 CNAME 記錄:
   - 名稱:`data`
   - 值:`你的帳號.github.io`
3. 等 DNS 生效(5 分鐘到 24 小時)
4. GitHub Pages 設定頁會自動偵測並啟用 HTTPS

## ❓ 常見問題

**Q: 部署失敗,Pages 頁面說 "GitHub Pages is not enabled for this repository"**
A: Step 2 沒做對。回去確認 Source 是 **GitHub Actions** 不是 branch。

**Q: 網站 404**
A: 第一次部署需要 5-10 分鐘生效,刷新看看。如果還是不行,看 Actions 分頁有沒有跑成功。

**Q: 我想用 sakego.com.tw 主網域,不是子網域**
A: 主網域指過來會跟你現在的 WordPress 衝突。建議用子網域(如 `data.` 或 `sake.`),
   或等之後 WordPress 方案決定好再說。

**Q: 改了模板但網站沒變**
A: 1) 確認 commit 推上去了 2) 看 Actions 是否跑成功 3) 瀏覽器強制重整 `Ctrl+Shift+R`
