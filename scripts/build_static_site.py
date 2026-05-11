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


# ===== 情境圖 / CSS 卡片配色邏輯 =====
# 用 Unsplash 的「日本酒/酒場/和食」情境圖 (CC0 / Unsplash License,可商用)
# 注意:這些不是「特定酒款的圖片」,只是視覺氛圍素材
UNSPLASH_HERO_IMAGES = {
    "default": "https://images.unsplash.com/photo-1579952516518-12c1d8f3a05a?w=1600&q=80",  # 酒杯特寫
    "sake_bottle": "https://images.unsplash.com/photo-1627042942554-23bdac68f5f9?w=1200&q=80",  # 酒瓶
    "izakaya": "https://images.unsplash.com/photo-1554998171-89445e31c52b?w=1200&q=80",  # 居酒屋
    "tasting": "https://images.unsplash.com/photo-1607301406259-dfb186e15de8?w=1200&q=80",  # 品飲
}


def classify_sake_visual(product: dict) -> dict:
    """根據酒類型 + 風味雷達,決定卡片的配色主題。
    完全基於規格資料,不抓任何外部圖片(避開著作權)。"""
    sake_type = (product.get("sake_type") or "").strip()

    # 主題色系優先級:酒類型 > 風味雷達主軸 > 預設
    themes = {
        "daiginjo": {  # 大吟釀類 - 金 / 米白系
            "primary": "#C9A961",
            "secondary": "#8B7355",
            "bg_gradient": "linear-gradient(135deg, #FAF6E8 0%, #E8D9B0 100%)",
            "accent": "#722F37",
            "label": "大吟釀",
        },
        "ginjo": {  # 吟釀類 - 淡綠 / 春芽
            "primary": "#6B8E5A",
            "secondary": "#4A6741",
            "bg_gradient": "linear-gradient(135deg, #F0F4E8 0%, #C8D4B0 100%)",
            "accent": "#3D5233",
            "label": "吟釀",
        },
        "junmai": {  # 純米 - 深紅 / 米色
            "primary": "#8B3A3A",
            "secondary": "#5C2828",
            "bg_gradient": "linear-gradient(135deg, #F5E8E0 0%, #D4B5A8 100%)",
            "accent": "#3D1818",
            "label": "純米",
        },
        "honjozo": {  # 本釀造 - 藍 / 清爽
            "primary": "#2C5F7C",
            "secondary": "#1E4258",
            "bg_gradient": "linear-gradient(135deg, #E8F0F5 0%, #B0C8D8 100%)",
            "accent": "#0F2A3D",
            "label": "本釀造",
        },
        "namazake": {  # 生酒 - 翠綠 / 清新
            "primary": "#5BA85B",
            "secondary": "#3D7A3D",
            "bg_gradient": "linear-gradient(135deg, #E8F5E8 0%, #B0D8B0 100%)",
            "accent": "#1F4D1F",
            "label": "生酒",
        },
        "koshu": {  # 古酒 - 深褐 / 琥珀
            "primary": "#8B4513",
            "secondary": "#5C2E0D",
            "bg_gradient": "linear-gradient(135deg, #F0E5D0 0%, #C9A878 100%)",
            "accent": "#3D1E08",
            "label": "古酒",
        },
        "default": {  # 預設 - 和風摩登
            "primary": "#722F37",
            "secondary": "#5C2528",
            "bg_gradient": "linear-gradient(135deg, #FAF7F0 0%, #E5D5C5 100%)",
            "accent": "#1A1A1A",
            "label": "日本酒",
        },
    }

    # 偵測類型 (日文漢字匹配)
    theme_key = "default"
    if any(k in sake_type for k in ["大吟醸", "大吟釀"]):
        theme_key = "daiginjo"
    elif any(k in sake_type for k in ["吟醸", "吟釀"]):
        theme_key = "ginjo"
    elif "古酒" in sake_type:
        theme_key = "koshu"
    elif any(k in sake_type for k in ["生酒", "生原酒", "無濾過"]):
        theme_key = "namazake"
    elif "純米" in sake_type:
        theme_key = "junmai"
    elif "本醸造" in sake_type or "本釀造" in sake_type:
        theme_key = "honjozo"
    else:
        # 沒有酒類型?用風味雷達推斷
        try:
            f1 = float(product.get("flavor_f1_華やか", 0) or 0)
            f3 = float(product.get("flavor_f3_重厚", 0) or 0)
            f5 = float(product.get("flavor_f5_ドライ", 0) or 0)
            if f1 > 0.6:
                theme_key = "daiginjo"
            elif f3 > 0.5:
                theme_key = "junmai"
            elif f5 > 0.6:
                theme_key = "honjozo"
        except (ValueError, TypeError):
            pass

    return themes[theme_key]


def get_hero_image(brewery_id: str, region: str = "") -> str:
    """為酒造/地區頁挑一張情境圖 (用 ID 雜湊穩定挑選)。"""
    # 用 brewery_id 做穩定雜湊,讓同一個酒造每次都拿到同一張圖
    images = list(UNSPLASH_HERO_IMAGES.values())
    if not brewery_id:
        return images[0]
    try:
        h = int(brewery_id) % len(images)
    except (ValueError, TypeError):
        h = hash(brewery_id) % len(images)
    return images[h]


def has_authorized_image(product_id: str) -> str | None:
    """檢查是否有手動上傳的授權圖片 (放在 static/sake-images/{product_id}.jpg)。
    回傳相對路徑或 None。"""
    if not product_id:
        return None
    # 檢查多種格式
    for ext in ["jpg", "jpeg", "png", "webp"]:
        path = STATIC_DIR / "sake-images" / f"{product_id}.{ext}"
        if path.exists():
            return f"sake-images/{product_id}.{ext}"
    return None


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
        # 為每個 product 附加視覺主題 + 授權圖檢查
        p["_theme"] = classify_sake_visual(p)
        p["_authorized_image"] = has_authorized_image(p.get("product_id", ""))
        p["_hero_image"] = get_hero_image(p.get("brewery_id", ""))
        products_by_brewery[p["brewery_id"]].append(p)

    # 按 region 分組
    regions = defaultdict(lambda: defaultdict(list))
    for brewery in breweries:
        # 為每個酒造附加 hero image
        brewery["_hero_image"] = get_hero_image(brewery.get("brewery_id", ""))
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
