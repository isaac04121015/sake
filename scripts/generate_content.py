#!/usr/bin/env python3
"""
generate_content.py
基於 products.csv 的「事實規格」與你的品牌語調 (config/brand_voice.md),
用 Claude API 生成繁中介紹、風味描述、搭餐建議。

重要:此腳本 *不* 翻譯任何外部網站的內容,而是基於結構化規格從零撰寫。

輸入:
  data/breweries.csv
  data/products.csv
  config/brand_voice.md (你自己撰寫的品牌語調指引)

輸出:
  data/products_with_content.csv  (加上 description / pairing 欄位)
  data/products_with_content.json

用法:
  export ANTHROPIC_API_KEY=sk-ant-...
  python generate_content.py                # 處理全部
  python generate_content.py --max 5        # 只處理 5 筆 (測試用)
  python generate_content.py --regenerate   # 強制重新生成,覆蓋既有內容
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import anthropic

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1500


def load_brand_voice() -> str:
    path = CONFIG_DIR / "brand_voice.md"
    if not path.exists():
        return DEFAULT_BRAND_VOICE
    return path.read_text(encoding="utf-8")


DEFAULT_BRAND_VOICE = """\
# 品牌語調預設值

語氣: 專業但親切,像懂行的朋友介紹
受眾: 對日本酒有興趣的台灣消費者,從入門到進階都有
長度: 每段 80-150 字
用詞: 繁體中文,專有名詞首次出現附日文原文 (例如「山田錦 (山田錦)」)
避免: 過度文藝、空泛形容詞 (如「餘韻無窮」「絕妙平衡」)
強調: 具體可感的描述,搭餐建議要說明「為什麼這樣搭」
"""


PROMPT_TEMPLATE = """\
你是 sakego.com.tw 的日本酒專欄作者。請基於以下「事實規格」,撰寫一段繁體中文產品介紹。

# 品牌語調指引
{brand_voice}

# 產品事實規格
- 酒造名 (日文): {brewery_name_jp}
- 酒造名 (繁中): {brewery_name_zhtw}
- 銘柄/產品名 (日文): {product_name_jp}
- 所在地: {area_zhtw} ({area_jp})
- 酒類型: {sake_type}
- 使用米: {rice_variety}
- 米產地: {rice_origin}
- 精米步合: {seimaibuai}
- 酵母: {yeast}
- 酒精度: {abv}
- 日本酒度 (SMV): {smv}
- 酸度: {acidity}

# Sakenowa 風味雷達數據 (0~1,越高越強)
- 華やか (華麗): {flavor_f1}
- 芳醇 (濃醇): {flavor_f2}
- 重厚 (厚重): {flavor_f3}
- 穏やか (穩重): {flavor_f4}
- ドライ (辛口): {flavor_f5}
- 軽快 (輕快): {flavor_f6}

# 風味標籤 (來自 Sakenowa 用戶整體評價)
{flavor_tags}

# 撰寫要求
請輸出 JSON 格式,包含三個欄位:

```json
{{
  "description": "120-180 字的產品介紹。基於上述規格,描述酒造特色 (若資料不足則只簡述地區風土) + 此款的釀造特點 + 風味輪廓。不要編造未提供的資訊。",
  "tasting_note": "60-100 字的品飲建議,涵蓋:適飲溫度、香氣輪廓、口感、尾韻。基於風味雷達與標籤推導,不要憑空想像。",
  "pairing": "60-100 字的搭餐建議。給 2-3 種具體餐點,並說明『為什麼這樣搭』 (例如酒體輕快搭白身魚、芳醇厚實搭烤物)。"
}}
```

# 重要規則
1. 若某欄位是空白或 "N/A",在文中**省略該資訊**,不要寫「資料不詳」
2. 不要用「絕妙」「無與倫比」「巔峰之作」等空泛形容
3. 不要編造創業年、得獎紀錄、家族故事等未提供的事實
4. 直接回 JSON,不要加 markdown 程式碼框,不要前言後語
"""


def build_prompt(product: dict, brewery: dict, brand_voice: str) -> str:
    def fmt(val, suffix=""):
        if val is None or str(val).strip() in ("", "N/A", "nan"):
            return "(未提供)"
        return f"{val}{suffix}"

    return PROMPT_TEMPLATE.format(
        brand_voice=brand_voice,
        brewery_name_jp=product.get("brewery_name_jp", ""),
        brewery_name_zhtw=brewery.get("name_zhtw", "") or product.get("brewery_name_jp", ""),
        product_name_jp=product.get("name_jp", ""),
        area_jp=product.get("area_jp", ""),
        area_zhtw=product.get("area_zhtw", ""),
        sake_type=fmt(product.get("sake_type")),
        rice_variety=fmt(product.get("rice_variety")),
        rice_origin=fmt(product.get("rice_origin")),
        seimaibuai=fmt(product.get("seimaibuai"), "%"),
        yeast=fmt(product.get("yeast")),
        abv=fmt(product.get("abv"), "%"),
        smv=fmt(product.get("smv")),
        acidity=fmt(product.get("acidity")),
        flavor_f1=fmt(product.get("flavor_f1_華やか")),
        flavor_f2=fmt(product.get("flavor_f2_芳醇")),
        flavor_f3=fmt(product.get("flavor_f3_重厚")),
        flavor_f4=fmt(product.get("flavor_f4_穏やか")),
        flavor_f5=fmt(product.get("flavor_f5_ドライ")),
        flavor_f6=fmt(product.get("flavor_f6_軽快")),
        flavor_tags=product.get("flavor_tags", "") or "(無)",
    )


def parse_response(text: str) -> dict:
    """從 Claude 回應中萃取 JSON。"""
    text = text.strip()
    # 移除可能的 markdown 程式碼框
    if text.startswith("```"):
        lines = text.split("\n")
        # 砍掉首尾的 ``` 行
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def generate_for_product(
    client: anthropic.Anthropic,
    product: dict,
    brewery: dict,
    brand_voice: str,
) -> dict:
    prompt = build_prompt(product, brewery, brand_voice)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    return parse_response(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=0, help="最多處理 N 筆")
    parser.add_argument("--regenerate", action="store_true", help="強制重新生成")
    parser.add_argument("--brewery-id", type=int, help="只處理特定酒造")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: 請設定環境變數 ANTHROPIC_API_KEY", file=sys.stderr)
        return 1

    products_path = DATA_DIR / "products.csv"
    breweries_path = DATA_DIR / "breweries.csv"
    if not products_path.exists():
        print(f"ERROR: {products_path} 不存在", file=sys.stderr)
        return 1

    with products_path.open(encoding="utf-8-sig") as f:
        products = list(csv.DictReader(f))
    with breweries_path.open(encoding="utf-8-sig") as f:
        breweries_list = list(csv.DictReader(f))
    breweries_by_id = {b["brewery_id"]: b for b in breweries_list}

    # 讀既有的內容檔 (若有)
    output_path = DATA_DIR / "products_with_content.csv"
    existing_content = {}
    if output_path.exists() and not args.regenerate:
        with output_path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                existing_content[row["product_id"]] = row

    brand_voice = load_brand_voice()
    print(f"Brand voice loaded: {len(brand_voice)} chars")

    # 篩選需處理的
    todo = []
    for p in products:
        if args.brewery_id and str(p.get("brewery_id")) != str(args.brewery_id):
            continue
        if not args.regenerate and p["product_id"] in existing_content:
            existing = existing_content[p["product_id"]]
            if existing.get("description", "").strip():
                continue
        todo.append(p)

    if args.max > 0:
        todo = todo[: args.max]

    print(f"Total products: {len(products)}")
    print(f"To generate: {len(todo)}")
    if not todo:
        print("沒有要生成的內容")
        return 0

    client = anthropic.Anthropic(api_key=api_key)
    results = list(existing_content.values()) if existing_content else []
    results_by_id = {r["product_id"]: r for r in results}

    for i, product in enumerate(todo, 1):
        brewery = breweries_by_id.get(product.get("brewery_id", ""), {})
        print(f"\n[{i}/{len(todo)}] {product.get('brewery_name_jp')} / {product.get('name_jp')}")

        for attempt in range(3):
            try:
                content = generate_for_product(client, product, brewery, brand_voice)
                merged = dict(product)
                merged["description"] = content.get("description", "")
                merged["tasting_note"] = content.get("tasting_note", "")
                merged["pairing"] = content.get("pairing", "")
                merged["content_generated_at"] = datetime.now(timezone.utc).isoformat()
                merged["content_model"] = MODEL
                results_by_id[product["product_id"]] = merged
                print(f"  ✓ description: {len(merged['description'])} chars")
                break
            except json.JSONDecodeError as e:
                print(f"  attempt {attempt + 1}: JSON parse error: {e}")
                if attempt == 2:
                    print(f"  ✗ giving up after 3 attempts")
            except anthropic.APIError as e:
                print(f"  attempt {attempt + 1}: API error: {e}")
                time.sleep(2 ** attempt)
                if attempt == 2:
                    print(f"  ✗ giving up after 3 attempts")
            except Exception as e:
                print(f"  attempt {attempt + 1}: unexpected error: {e}")
                if attempt == 2:
                    raise

        # 每處理 10 筆就存一次檔 (容錯)
        if i % 10 == 0:
            save_results(list(results_by_id.values()), output_path)
            print(f"  (autosaved at {i})")

    # 最終存檔
    save_results(list(results_by_id.values()), output_path)
    print(f"\n✓ wrote {output_path}")
    print(f"✓ wrote {output_path.with_suffix('.json')}")
    return 0


def save_results(results: list[dict], csv_path: Path) -> None:
    if not results:
        return
    # 統一所有欄位
    all_keys = set()
    for r in results:
        all_keys.update(r.keys())
    fieldnames = list(results[0].keys())
    for k in all_keys:
        if k not in fieldnames:
            fieldnames.append(k)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    json_path = csv_path.with_suffix(".json")
    json_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
