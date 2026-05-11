#!/usr/bin/env python3
"""
normalize.py
讀取 data/raw/*.json,過濾出 config/target_breweries.txt 中的目標酒造,
合併為結構化的 breweries.csv / products.csv (以及對應 JSON)。

輸入:
  data/raw/areas.json
  data/raw/breweries.json
  data/raw/brands.json
  data/raw/flavor-charts.json
  data/raw/brand-flavor-tags.json
  data/raw/flavor-tags.json
  data/regions_zhtw.json
  config/target_breweries.txt

輸出:
  data/breweries.csv / data/breweries.json
  data/products.csv  / data/products.json
  data/_match_report.txt   (顯示哪些目標酒造在 Sakenowa 找到/找不到)
"""

import csv
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_target_breweries(path: Path) -> list[dict]:
    """讀取 config/target_breweries.txt,回傳 [{brand_jp, brewery_jp, area_jp}, ...]"""
    targets = []
    for line_num, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            print(f"  warn: line {line_num} malformed, skipped: {line}", file=sys.stderr)
            continue
        targets.append({
            "brand_jp": parts[0],
            "brewery_jp": parts[1],
            "area_jp": parts[2],
        })
    return targets


def build_indexes(raw: dict) -> dict:
    """把 raw JSON 整理成快速查找的索引。"""
    areas_by_id = {a["id"]: a for a in raw["areas"]["areas"]}
    breweries_by_id = {b["id"]: b for b in raw["breweries"]["breweries"]}
    breweries_by_name = {b["name"]: b for b in raw["breweries"]["breweries"]}
    brands_by_id = {b["id"]: b for b in raw["brands"]["brands"]}
    brands_by_name = {}
    for b in raw["brands"]["brands"]:
        brands_by_name.setdefault(b["name"], []).append(b)

    flavor_charts_by_brand = {
        fc["brandId"]: fc for fc in raw["flavor-charts"]["flavorCharts"]
    }

    flavor_tags_by_id = {t["id"]: t["tag"] for t in raw["flavor-tags"]["tags"]}

    brand_flavor_tags = {}
    for entry in raw["brand-flavor-tags"]["brandFlavorTags"]:
        brand_flavor_tags[entry["brandId"]] = entry.get("tagIds", [])

    return {
        "areas_by_id": areas_by_id,
        "breweries_by_id": breweries_by_id,
        "breweries_by_name": breweries_by_name,
        "brands_by_id": brands_by_id,
        "brands_by_name": brands_by_name,
        "flavor_charts_by_brand": flavor_charts_by_brand,
        "flavor_tags_by_id": flavor_tags_by_id,
        "brand_flavor_tags": brand_flavor_tags,
    }


def normalize_brewery_name(name: str) -> str:
    """酒造名標準化:去空白、去括號、統一全半形。"""
    name = re.sub(r"[\s　]+", "", name)
    name = name.replace("(", "(").replace(")", ")")
    return name


def match_target(target: dict, idx: dict) -> dict | None:
    """嘗試在 Sakenowa 索引中找到目標酒造對應的記錄。

    匹配優先級:
    1. brand_jp 精準匹配 → 用該銘柄的 breweryId 找酒造
    2. brewery_jp 精準匹配 → 該酒造下所有銘柄
    3. brewery_jp 標準化後匹配
    """
    brand_name = target["brand_jp"]
    brewery_name = target["brewery_jp"]

    # 路徑 1: 用銘柄名找
    candidate_brands = idx["brands_by_name"].get(brand_name, [])
    if candidate_brands:
        # 用酒造名 + 都道府縣再做二次驗證 (避免同名銘柄)
        for brand in candidate_brands:
            brewery = idx["breweries_by_id"].get(brand["breweryId"])
            if not brewery:
                continue
            area = idx["areas_by_id"].get(brewery["areaId"])
            if not area:
                continue
            if (normalize_brewery_name(brewery["name"]) ==
                normalize_brewery_name(brewery_name)
                or area["name"] == target["area_jp"]):
                return {
                    "brand": brand,
                    "brewery": brewery,
                    "area": area,
                    "match_method": "brand_name_exact",
                }
        # 退而求其次:銘柄名對得上,即使酒造名對不上也接受第一個
        brand = candidate_brands[0]
        brewery = idx["breweries_by_id"].get(brand["breweryId"])
        area = idx["areas_by_id"].get(brewery["areaId"]) if brewery else None
        if brewery and area:
            return {
                "brand": brand,
                "brewery": brewery,
                "area": area,
                "match_method": "brand_name_fallback",
            }

    # 路徑 2: 用酒造名找
    brewery = idx["breweries_by_name"].get(brewery_name)
    if brewery:
        area = idx["areas_by_id"].get(brewery["areaId"])
        # 找該酒造下所有銘柄,優先選名稱接近的
        all_brands_for_brewery = [
            b for b in idx["brands_by_id"].values()
            if b["breweryId"] == brewery["id"]
        ]
        if all_brands_for_brewery:
            return {
                "brand": all_brands_for_brewery[0],  # 第一個,後續會把全部產出
                "brewery": brewery,
                "area": area,
                "all_brands": all_brands_for_brewery,
                "match_method": "brewery_name_exact",
            }

    # 路徑 3: 酒造名標準化匹配
    target_norm = normalize_brewery_name(brewery_name)
    for b in idx["breweries_by_id"].values():
        if normalize_brewery_name(b["name"]) == target_norm:
            area = idx["areas_by_id"].get(b["areaId"])
            all_brands_for_brewery = [
                br for br in idx["brands_by_id"].values()
                if br["breweryId"] == b["id"]
            ]
            return {
                "brand": all_brands_for_brewery[0] if all_brands_for_brewery else None,
                "brewery": b,
                "area": area,
                "all_brands": all_brands_for_brewery,
                "match_method": "brewery_name_normalized",
            }

    return None


def build_brewery_row(match: dict, regions: dict) -> dict:
    """產生 breweries.csv 一筆。"""
    brewery = match["brewery"]
    area = match["area"]
    region_meta = regions.get(str(area["id"]), {}) if area else {}

    return {
        "brewery_id": brewery["id"],
        "name_jp": brewery["name"],
        "name_zhtw": "",  # 留空,人工填或之後 AI 補
        "area_id": area["id"] if area else "",
        "area_jp": area["name"] if area else "",
        "area_zhtw": region_meta.get("zhtw", ""),
        "region_zhtw": region_meta.get("region_zhtw", ""),
        "address": "",  # Sakenowa 沒提供
        "founded_year": "",  # Sakenowa 沒提供
        "website": "",  # 之後由 fetch_brewery_specs.py 補
        "phone": "",
        "latitude": "",
        "longitude": "",
        "sakenowa_brewery_url": f"https://sakenowa.com/breweries/{brewery['id']}",
        "match_method": match["match_method"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_product_rows(match: dict, idx: dict, regions: dict) -> list[dict]:
    """產生 products.csv 多筆 (該酒造下所有銘柄)。"""
    brewery = match["brewery"]
    area = match["area"]

    # 列出此酒造的所有銘柄
    if "all_brands" in match and match["all_brands"]:
        brands = match["all_brands"]
    else:
        brands = [match["brand"]] if match["brand"] else []

    rows = []
    for brand in brands:
        if not brand:
            continue
        brand_id = brand["id"]
        flavor = idx["flavor_charts_by_brand"].get(brand_id, {})
        tag_ids = idx["brand_flavor_tags"].get(brand_id, [])
        tags = [idx["flavor_tags_by_id"].get(t, "") for t in tag_ids]
        tags = [t for t in tags if t]

        rows.append({
            "product_id": f"sn_{brand_id}",
            "brewery_id": brewery["id"],
            "brewery_name_jp": brewery["name"],
            "name_jp": brand["name"],
            "name_zhtw": "",  # 留空
            "area_jp": area["name"] if area else "",
            "area_zhtw": regions.get(str(area["id"]), {}).get("zhtw", "") if area else "",

            # === 規格欄位 (Sakenowa 沒有,需 fetch_brewery_specs 補) ===
            "sake_type": "",
            "rice_variety": "",
            "rice_origin": "",
            "seimaibuai": "",
            "yeast": "",
            "abv": "",
            "smv": "",
            "acidity": "",
            "amino_acid": "",

            # === Sakenowa 風味雷達 (6 軸: 0~1) ===
            "flavor_f1_華やか": flavor.get("f1", ""),
            "flavor_f2_芳醇": flavor.get("f2", ""),
            "flavor_f3_重厚": flavor.get("f3", ""),
            "flavor_f4_穏やか": flavor.get("f4", ""),
            "flavor_f5_ドライ": flavor.get("f5", ""),
            "flavor_f6_軽快": flavor.get("f6", ""),
            "flavor_tags": ",".join(tags),

            "sakenowa_brand_id": brand_id,
            "sakenowa_brand_url": f"https://sakenowa.com/brands/{brand_id}",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        print(f"  warn: no rows to write to {path.name}", file=sys.stderr)
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig for Excel
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict]) -> None:
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    print(f"Loading raw data from {RAW_DIR}")
    try:
        raw = {
            name: load_json(RAW_DIR / f"{name}.json")
            for name in ["areas", "breweries", "brands",
                         "flavor-charts", "flavor-tags", "brand-flavor-tags"]
        }
    except FileNotFoundError as e:
        print(f"ERROR: {e}\nRun fetch_sakenowa.py first.", file=sys.stderr)
        return 1

    print("Building indexes...")
    idx = build_indexes(raw)
    print(f"  {len(idx['breweries_by_id'])} breweries / "
          f"{len(idx['brands_by_id'])} brands in Sakenowa")

    print(f"Loading regions translation: {DATA_DIR / 'regions_zhtw.json'}")
    regions = load_json(DATA_DIR / "regions_zhtw.json")

    print(f"Loading targets: {CONFIG_DIR / 'target_breweries.txt'}")
    targets = parse_target_breweries(CONFIG_DIR / "target_breweries.txt")
    print(f"  {len(targets)} targets")

    brewery_rows = []
    product_rows = []
    seen_brewery_ids = set()
    matched = []
    unmatched = []

    print("\nMatching...")
    for target in targets:
        match = match_target(target, idx)
        if not match:
            unmatched.append(target)
            continue

        matched.append((target, match))
        bid = match["brewery"]["id"]
        if bid not in seen_brewery_ids:
            seen_brewery_ids.add(bid)
            brewery_rows.append(build_brewery_row(match, regions))

        product_rows.extend(build_product_rows(match, idx, regions))

    print(f"  matched: {len(matched)} targets → "
          f"{len(brewery_rows)} unique breweries / "
          f"{len(product_rows)} products")
    print(f"  unmatched: {len(unmatched)}")

    # 輸出
    DATA_DIR.mkdir(exist_ok=True)
    write_csv(DATA_DIR / "breweries.csv", brewery_rows)
    write_csv(DATA_DIR / "products.csv", product_rows)
    write_json(DATA_DIR / "breweries.json", brewery_rows)
    write_json(DATA_DIR / "products.json", product_rows)

    # match report
    report_lines = [
        f"Match report (generated {datetime.now(timezone.utc).isoformat()})",
        "=" * 60,
        f"Targets: {len(targets)}",
        f"Matched: {len(matched)}",
        f"Unique breweries: {len(brewery_rows)}",
        f"Total products: {len(product_rows)}",
        f"Unmatched: {len(unmatched)}",
        "",
        "── Unmatched targets (need manual review) ──",
    ]
    for t in unmatched:
        report_lines.append(f"  {t['brand_jp']:20s} | {t['brewery_jp']:20s} | {t['area_jp']}")

    report_lines.append("")
    report_lines.append("── Match method breakdown ──")
    methods = {}
    for _, m in matched:
        methods[m["match_method"]] = methods.get(m["match_method"], 0) + 1
    for method, count in sorted(methods.items()):
        report_lines.append(f"  {method}: {count}")

    (DATA_DIR / "_match_report.txt").write_text("\n".join(report_lines), encoding="utf-8")

    print(f"\n✓ wrote {DATA_DIR / 'breweries.csv'}")
    print(f"✓ wrote {DATA_DIR / 'products.csv'}")
    print(f"✓ wrote {DATA_DIR / 'breweries.json'}")
    print(f"✓ wrote {DATA_DIR / 'products.json'}")
    print(f"✓ wrote {DATA_DIR / '_match_report.txt'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
