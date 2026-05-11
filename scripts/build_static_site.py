#!/usr/bin/env python3
"""
build_static_site.py
讀取 data/breweries.csv 與 data/products.csv (或 products_with_content.csv),
產出靜態 HTML 網站到 dist/。

頁面結構:
  dist/
  ├── index.html                    首頁 (按地區大區塊分類)
  ├── styles.css                    樣式
  ├── regions/
  │   ├── 近畿/index.html            地區頁 (列出該地區酒造)
  │   ├── 東北/index.html
  │   └── ...
  ├── breweries/
  │   ├── {brewery_id}.html          酒造詳細頁 (列出旗下所有酒款)
  │   └── ...
  └── products/
      ├── {product_id}.html          產品詳細頁 (規格表 + 介紹)
      └── ...

用法:
  python scripts/build_static_site.py
  python scripts/build_static_site.py --output-dir public  # 自訂輸出目錄
"""

import argparse
import csv
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def safe_id(s: str) -> str:
    """把任意字串轉成可用於檔名/URL 的 ID。"""
    if not s:
        return "unknown"
    return str(s).strip().replace("/", "-").replace(" ", "_")


def build_data_model() -> dict:
    """從 CSV 建立巢狀資料結構: region → area → brewery → products"""
    breweries = load_csv(DATA_DIR / "breweries.csv")

    # 優先用有內容的版本,沒有再退回原版
    products_with_content_path = DATA_DIR / "products_with_content.csv"
    if products_with_content_path.exists():
        products = load_csv(products_with_content_path)
    else:
        products = load_csv(DATA_DIR / "products.csv")

    if not breweries:
        print("ERROR: data/breweries.csv 不存在或是空的,請先跑 normalize.py", file=sys.stderr)
        sys.exit(1)

    # 索引
    brewery_by_id = {b["brewery_id"]: b for b in breweries}
    products_by_brewery = defaultdict(list)
    for p in products:
        products_by_brewery[p["brewery_id"]].append(p)

    # 按 region 分組
    regions = defaultdict(lambda: defaultdict(list))
    for brewery in breweries:
        region = brewery.get("region_zhtw", "其他")
        area = brewery.get("area_zhtw") or brewery.get("area_jp", "未分類")
        regions[region][area].append(brewery)

    # 排序:地區大類照固定順序,內部按筆數
    region_order = ["北海道", "東北", "關東", "中部", "近畿", "中國", "四國", "九州", "沖繩", "其他"]
    sorted_regions = []
    for region_name in region_order:
        if region_name not in regions:
            continue
        areas = regions[region_name]
        # 縣內酒造按 name 排
        areas_sorted = {
            area: sorted(brews, key=lambda b: b.get("name_jp", ""))
            for area, brews in sorted(areas.items())
        }
        sorted_regions.append({
            "name": region_name,
            "areas": areas_sorted,
            "brewery_count": sum(len(b) for b in areas_sorted.values()),
        })

    return {
        "regions": sorted_regions,
        "breweries": breweries,
        "brewery_by_id": brewery_by_id,
        "products": products,
        "products_by_brewery": dict(products_by_brewery),
        "total_breweries": len(breweries),
        "total_products": len(products),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def render_pages(data: dict, output_dir: Path, env: Environment) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "regions").mkdir(exist_ok=True)
    (output_dir / "breweries").mkdir(exist_ok=True)
    (output_dir / "products").mkdir(exist_ok=True)

    # 複製 static 檔案
    if STATIC_DIR.exists():
        for f in STATIC_DIR.iterdir():
            if f.is_file():
                shutil.copy(f, output_dir / f.name)

    # === 首頁 ===
    tpl = env.get_template("index.html.j2")
    (output_dir / "index.html").write_text(
        tpl.render(**data, page_path=""),
        encoding="utf-8",
    )
    print(f"  ✓ index.html")

    # === 地區頁 ===
    tpl = env.get_template("region.html.j2")
    for region in data["regions"]:
        region_dir = output_dir / "regions" / safe_id(region["name"])
        region_dir.mkdir(exist_ok=True)
        (region_dir / "index.html").write_text(
            tpl.render(
                region=region,
                products_by_brewery=data["products_by_brewery"],
                generated_at=data["generated_at"],
                page_path="../../",
            ),
            encoding="utf-8",
        )
    print(f"  ✓ {len(data['regions'])} 個地區頁")

    # === 酒造頁 ===
    tpl = env.get_template("brewery.html.j2")
    for brewery in data["breweries"]:
        brewery_products = data["products_by_brewery"].get(brewery["brewery_id"], [])
        out = output_dir / "breweries" / f"{safe_id(brewery['brewery_id'])}.html"
        out.write_text(
            tpl.render(
                brewery=brewery,
                products=brewery_products,
                generated_at=data["generated_at"],
                page_path="../",
            ),
            encoding="utf-8",
        )
    print(f"  ✓ {len(data['breweries'])} 個酒造頁")

    # === 產品頁 ===
    tpl = env.get_template("product.html.j2")
    for product in data["products"]:
        brewery = data["brewery_by_id"].get(product.get("brewery_id"), {})
        out = output_dir / "products" / f"{safe_id(product['product_id'])}.html"
        out.write_text(
            tpl.render(
                product=product,
                brewery=brewery,
                generated_at=data["generated_at"],
                page_path="../",
            ),
            encoding="utf-8",
        )
    print(f"  ✓ {len(data['products'])} 個產品頁")

    # === 搜尋用 JSON (給 client-side 搜尋用) ===
    search_data = []
    for p in data["products"]:
        search_data.append({
            "id": p.get("product_id"),
            "name_jp": p.get("name_jp", ""),
            "name_zhtw": p.get("name_zhtw", ""),
            "brewery": p.get("brewery_name_jp", ""),
            "area": p.get("area_zhtw") or p.get("area_jp", ""),
            "url": f"products/{safe_id(p['product_id'])}.html",
        })
    (output_dir / "search.json").write_text(
        json.dumps(search_data, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  ✓ search.json ({len(search_data)} 筆)")

    # === .nojekyll (告訴 GitHub Pages 不要用 Jekyll 處理) ===
    (output_dir / ".nojekyll").write_text("")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="dist", help="輸出目錄 (預設 dist/)")
    args = parser.parse_args()

    output_dir = ROOT / args.output_dir

    # 清空舊輸出
    if output_dir.exists():
        shutil.rmtree(output_dir)

    if not TEMPLATES_DIR.exists():
        print(f"ERROR: {TEMPLATES_DIR} 不存在", file=sys.stderr)
        return 1

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # 自訂 filter: 空值顯示為 "—"
    def empty_as_dash(value):
        if value is None or str(value).strip() in ("", "N/A", "nan"):
            return "—"
        return value
    env.filters["dash"] = empty_as_dash

    # 自訂 filter: safe_id 給模板用
    env.filters["safe_id"] = safe_id

    print(f"Building static site → {output_dir}")
    print("=" * 60)
    data = build_data_model()
    print(f"Loaded: {data['total_breweries']} breweries / {data['total_products']} products")
    print()

    render_pages(data, output_dir, env)

    print()
    print(f"✓ Done. Open {output_dir}/index.html in browser to preview.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
