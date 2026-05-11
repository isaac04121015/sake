#!/usr/bin/env python3
"""
fetch_brewery_specs.py
從各酒造官網補完 Sakenowa API 沒有的事實規格欄位:
精米步合、米種、米產地、酵母、酒精度、SMV、酸度。

設計原則:
- 只抓事實性規格 (數字、米種名等),不抓描述性文字
- 嚴格遵守 robots.txt
- 1 req/sec 速率限制 (對小酒造官網有禮貌)
- 失敗的酒造記錄到 _spec_failures.txt,不影響整體流程

用法:
  python fetch_brewery_specs.py                  # 處理所有缺欄位的產品
  python fetch_brewery_specs.py --brewery-id 5   # 只處理特定酒造
  python fetch_brewery_specs.py --dry-run        # 只列出預計處理的清單

注意:
  本腳本是「best-effort」工具,不同酒造官網結構差異大,
  抓取成功率預期約 30-60%。剩餘欄位需人工從酒款標籤、進口商資料補。
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse, urljoin
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

USER_AGENT = "sakego-data-collector/1.0 (+https://www.sakego.com.tw; contact@sakego.com.tw)"
RATE_LIMIT_SECONDS = 1.0
REQUEST_TIMEOUT = 20

# 規格欄位的正規表達式樣板 (用於從 HTML 文字中萃取)
# 注意:這些只抓「規格欄位的數值」,不抓描述性文字
SPEC_PATTERNS = {
    "seimaibuai": [
        r"精米歩合[\s::]*(\d{1,3})\s*[%%]",
        r"精米步合[\s::]*(\d{1,3})\s*[%%]",
    ],
    "abv": [
        r"アルコール分?[\s::]*(\d{1,2}(?:\.\d)?)\s*[%%]",
        r"アルコール度数?[\s::]*(\d{1,2}(?:\.\d)?)",
        r"酒精度數?[\s::]*(\d{1,2}(?:\.\d)?)",
    ],
    "smv": [
        r"日本酒度[\s::]*([+\-±]?\s*\d{1,2}(?:\.\d)?)",
    ],
    "acidity": [
        r"酸度[\s::]*(\d(?:\.\d{1,2})?)",
    ],
    "amino_acid": [
        r"アミノ酸度?[\s::]*(\d(?:\.\d{1,2})?)",
        r"氨基酸度[\s::]*(\d(?:\.\d{1,2})?)",
    ],
}

# 米種與酵母用詞表匹配 (避免誤抓)
KNOWN_RICE_VARIETIES = [
    "山田錦", "五百万石", "美山錦", "雄町", "愛山", "亀の尾",
    "出羽燦々", "吟風", "彗星", "華吹雪", "華想い", "ぎんおとめ",
    "蔵の華", "秋田酒こまち", "美郷錦", "出羽の里", "改良信交",
    "越淡麗", "高嶺錦", "若水", "夢山水", "誉富士", "祭り晴",
    "神力", "強力", "白鶴錦", "渡船", "穀良都", "新山田穂",
]

KNOWN_YEASTS = [
    "協会1号", "協会6号", "協会7号", "協会9号", "協会10号", "協会11号",
    "協会14号", "協会1801号", "協会901号", "協会701号", "協会1501号",
    "M310", "K-1801", "山形酵母", "うつくしま夢酵母", "蔵付き酵母",
    "自家培養酵母", "蔵付酵母",
]


class PoliteSession:
    """有禮貌的 HTTP session:檢查 robots.txt + 速率限制。"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last_request_at = 0.0

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._robots_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(urljoin(base, "/robots.txt"))
            try:
                rp.read()
            except Exception:
                # robots.txt 讀不到視為允許
                pass
            self._robots_cache[base] = rp
        return self._robots_cache[base].can_fetch(USER_AGENT, url)

    def get(self, url: str) -> requests.Response | None:
        if not self.can_fetch(url):
            print(f"    blocked by robots.txt: {url}")
            return None

        elapsed = time.time() - self._last_request_at
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed)

        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            self._last_request_at = time.time()
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            print(f"    request failed: {e}")
            self._last_request_at = time.time()
            return None


def extract_spec_from_text(text: str) -> dict:
    """從一段文字中萃取規格欄位。只抓事實性數字。"""
    result = {}

    for field, patterns in SPEC_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                value = m.group(1).replace(" ", "").replace("%", "").replace("%", "")
                result[field] = value
                break

    # 米種:在文字中找已知米名
    for rice in KNOWN_RICE_VARIETIES:
        if rice in text:
            result["rice_variety"] = rice
            break

    # 酵母:在文字中找已知酵母名
    for yeast in KNOWN_YEASTS:
        if yeast in text:
            result["yeast"] = yeast
            break

    return result


def find_brewery_website(brewery_name_jp: str, session: PoliteSession) -> str | None:
    """
    嘗試找到酒造官網。
    這個函式預設留空 — 自動找官網涉及搜尋引擎抓取,容易被封。
    建議使用者在 data/brewery_websites.csv 中手動維護官網對照表。
    """
    websites_file = DATA_DIR / "brewery_websites.csv"
    if not websites_file.exists():
        return None

    with websites_file.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("brewery_name_jp") == brewery_name_jp:
                return row.get("website") or None
    return None


def fetch_specs_for_product(
    brewery_name_jp: str,
    product_name_jp: str,
    session: PoliteSession,
) -> dict:
    """嘗試為單一產品抓規格。回傳找到的欄位 dict (可能為空)。"""
    website = find_brewery_website(brewery_name_jp, session)
    if not website:
        return {"_status": "no_website"}

    # 抓首頁,從中找產品連結
    resp = session.get(website)
    if not resp:
        return {"_status": "homepage_failed"}

    soup = BeautifulSoup(resp.text, "html.parser")

    # 簡單策略:在頁面文字中直接尋找產品名,若有則嘗試從附近段落萃取
    page_text = soup.get_text(separator="\n", strip=True)

    if product_name_jp in page_text:
        # 找到產品名,取前後 1000 字元的段落
        idx = page_text.find(product_name_jp)
        snippet = page_text[max(0, idx - 200):idx + 1500]
        specs = extract_spec_from_text(snippet)
        if specs:
            specs["_status"] = "ok_homepage"
            specs["_source"] = website
            return specs

    # 二次策略:找包含產品名的連結,逐一探訪
    for link in soup.find_all("a", href=True):
        link_text = link.get_text(strip=True)
        if product_name_jp in link_text or product_name_jp in link["href"]:
            link_url = urljoin(website, link["href"])
            sub = session.get(link_url)
            if sub:
                sub_soup = BeautifulSoup(sub.text, "html.parser")
                sub_text = sub_soup.get_text(separator="\n", strip=True)
                specs = extract_spec_from_text(sub_text)
                if specs:
                    specs["_status"] = "ok_subpage"
                    specs["_source"] = link_url
                    return specs

    return {"_status": "no_specs_found", "_source": website}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brewery-id", type=int, help="只處理特定酒造 ID")
    parser.add_argument("--dry-run", action="store_true", help="只列出預計處理的清單")
    parser.add_argument("--max", type=int, default=0, help="最多處理 N 筆 (0 = 全部)")
    args = parser.parse_args()

    products_path = DATA_DIR / "products.csv"
    if not products_path.exists():
        print(f"ERROR: {products_path} 不存在,請先跑 normalize.py", file=sys.stderr)
        return 1

    with products_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        products = list(reader)

    # 篩選需要處理的產品 (規格欄位幾乎全空的)
    needs_specs = []
    for p in products:
        if args.brewery_id and str(p.get("brewery_id")) != str(args.brewery_id):
            continue
        spec_fields = ["rice_variety", "seimaibuai", "yeast", "abv", "smv"]
        empty_count = sum(1 for f in spec_fields if not p.get(f, "").strip())
        if empty_count >= 3:  # 5 個關鍵欄位有 3 個以上空白才處理
            needs_specs.append(p)

    if args.max > 0:
        needs_specs = needs_specs[: args.max]

    print(f"Total products: {len(products)}")
    print(f"Needs spec fetch: {len(needs_specs)}")

    if args.dry_run:
        for p in needs_specs[:20]:
            print(f"  {p['brewery_name_jp']} / {p['name_jp']}")
        if len(needs_specs) > 20:
            print(f"  ... and {len(needs_specs) - 20} more")
        return 0

    if not needs_specs:
        print("沒有需要處理的產品")
        return 0

    # 檢查 brewery_websites.csv 是否存在
    websites_file = DATA_DIR / "brewery_websites.csv"
    if not websites_file.exists():
        print(f"\n⚠️  {websites_file} 不存在")
        print("此檔案應包含酒造官網對照,格式:")
        print("  brewery_name_jp,website")
        print("  獺祭酒造,https://www.asahishuzo.ne.jp/")
        print("\n沒有官網對照表時,本腳本只能標記為 no_website")
        print("建議手動建立此檔案後再跑,或跳過此步驟使用 Sakenowa 風味資料即可\n")

    session = PoliteSession()
    failures = []
    successes = []

    for i, product in enumerate(needs_specs, 1):
        print(f"\n[{i}/{len(needs_specs)}] {product['brewery_name_jp']} / {product['name_jp']}")
        try:
            specs = fetch_specs_for_product(
                product["brewery_name_jp"],
                product["name_jp"],
                session,
            )
            status = specs.pop("_status", "unknown")
            source = specs.pop("_source", "")
            if status.startswith("ok") and specs:
                # 寫回 product 記錄
                for k, v in specs.items():
                    product[k] = v
                product["updated_at"] = datetime.now(timezone.utc).isoformat()
                successes.append((product, source))
                print(f"  ✓ {status}: {specs}")
            else:
                failures.append((product, status))
                print(f"  - {status}")
        except Exception as e:
            failures.append((product, f"exception: {e}"))
            print(f"  ✗ exception: {e}")

    # 寫回 products.csv
    if successes:
        fieldnames = list(products[0].keys())
        with products_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)

        # 同步 JSON
        json_path = DATA_DIR / "products.json"
        json_path.write_text(
            json.dumps(products, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 失敗報告
    failures_path = DATA_DIR / "_spec_failures.txt"
    with failures_path.open("w", encoding="utf-8") as f:
        f.write(f"Spec fetch failures (generated {datetime.now(timezone.utc).isoformat()})\n")
        f.write("=" * 60 + "\n")
        for p, reason in failures:
            f.write(f"{p['brewery_name_jp']} / {p['name_jp']}: {reason}\n")

    print(f"\n{'=' * 60}")
    print(f"Successes: {len(successes)}")
    print(f"Failures: {len(failures)}")
    print(f"Failure log: {failures_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
