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
    """把 raw JSON 整理成快速查找的索引。

    Sakenowa 各端點回傳的 JSON 結構都是 {外層 key: [...資料]}。
    但外層 key 的命名不一致 (有的駝峰、有的連字號),所以這裡用容錯方式
    自動找出第一個 list 型別的 value 來用。
    """
    def first_list(payload, hint_keys=None):
        """從 dict 中找出第一個 list 型別的 value。
        hint_keys 是優先嘗試的 key 名稱清單。"""
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []
        # 先試提示的 key
        if hint_keys:
            for k in hint_keys:
                if k in payload and isinstance(payload[k], list):
                    return payload[k]
        # 退而求其次:找第一個是 list 的 value
        for v in payload.values():
            if isinstance(v, list):
                return v
        return []

    areas_list = first_list(raw["areas"], ["areas"])
    breweries_list = first_list(raw["breweries"], ["breweries"])
    brands_list = first_list(raw["brands"], ["brands"])
    flavor_charts_list = first_list(raw["flavor-charts"], ["flavorCharts"])
    flavor_tags_list = first_list(raw["flavor-tags"], ["tags", "flavorTags"])
    brand_flavor_tags_list = first_list(
        raw["brand-flavor-tags"],
        ["brandFlavorTags", "flavorTags", "tags"],
    )

    areas_by_id = {a["id"]: a for a in areas_list}
    breweries_by_id = {b["id"]: b for b in breweries_list}
    breweries_by_name = {b["name"]: b for b in breweries_list}
    brands_by_id = {b["id"]: b for b in brands_list}
    brands_by_name = {}
    for b in brands_list:
        brands_by_name.setdefault(b["name"], []).append(b)

    flavor_charts_by_brand = {
        fc["brandId"]: fc for fc in flavor_charts_list if "brandId" in fc
    }

    # flavor tags: 主表是 {id, tag} 或 {id, name},兩個都支援
    flavor_tags_by_id = {}
    for t in flavor_tags_list:
        tag_name = t.get("tag") or t.get("name") or ""
        flavor_tags_by_id[t["id"]] = tag_name

    # brand-flavor-tags: 每筆是 {brandId, tagIds} 或變體
    brand_flavor_tags = {}
    for entry in brand_flavor_tags_list:
        if "brandId" not in entry:
            continue
        # tagIds 也可能叫別的名字
        tag_ids = entry.get("tagIds") or entry.get("tags") or []
        brand_flavor_tags[entry["brandId"]] = tag_ids

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


def build_product_rows(match: dict, idx: dict, regions: dict, tag_translations: dict = None) -> list[dict]:
    """產生 products.csv 多筆 (該酒造下所有銘柄)。

    tag_translations: 日文→繁中對照表 (dict),若有則自動翻譯 flavor_tags
    """
    brewery = match["brewery"]
    area = match["area"]

    # 列出此酒造的所有銘柄
    if "all_brands" in match and match["all_brands"]:
        brands = match["all_brands"]
    else:
        brands = [match["brand"]] if match["brand"] else []

    tag_translations = tag_translations or {}

    rows = []
    for brand in brands:
        if not brand:
            continue
        # 跳過空名稱銘柄
        brand_name = (brand.get("name") or "").strip()
        if not brand_name:
            continue
        brand_id = brand["id"]
        flavor = idx["flavor_charts_by_brand"].get(brand_id, {})
        tag_ids = idx["brand_flavor_tags"].get(brand_id, [])
        tags_jp = [idx["flavor_tags_by_id"].get(t, "") for t in tag_ids]
        tags_jp = [t for t in tags_jp if t]
        # 套用翻譯:有對照就用繁中,沒有就保留日文
        tags_zhtw = [tag_translations.get(t, t) for t in tags_jp]

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
            "flavor_tags": ",".join(tags_zhtw),
            "flavor_tags_jp": ",".join(tags_jp),

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


def build_all_rows(idx: dict, regions: dict, tag_translations: dict = None) -> tuple[list[dict], list[dict]]:
    """全抓模式:遍歷 Sakenowa 全部資料,產出 breweries + products。
    自動跳過名稱為空的酒造(Sakenowa 偶爾有空殼資料)。"""
    brewery_rows = []
    product_rows = []
    skipped_empty = 0  # 跳過的空名稱酒造數

    # 全部酒造
    for brewery in idx["breweries_by_id"].values():
        # 過濾掉名稱為空字串、None、或只有空白的酒造
        name = (brewery.get("name") or "").strip()
        if not name:
            skipped_empty += 1
            continue

        area = idx["areas_by_id"].get(brewery["areaId"])
        if not area:
            continue
        # 建 match 結構讓既有 build_brewery_row / build_product_rows 能用
        all_brands = [
            b for b in idx["brands_by_id"].values()
            if b["breweryId"] == brewery["id"]
        ]
        match = {
            "brand": all_brands[0] if all_brands else None,
            "brewery": brewery,
            "area": area,
            "all_brands": all_brands,
            "match_method": "all_mode",
        }
        brewery_rows.append(build_brewery_row(match, regions))
        product_rows.extend(build_product_rows(match, idx, regions, tag_translations))

    if skipped_empty:
        print(f"  skipped {skipped_empty} brewery with empty name")

    return brewery_rows, product_rows


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["all", "targets"],
        default="all",
        help="all = 抓 Sakenowa 全部資料 (預設); targets = 只抓 config/target_breweries.txt 清單",
    )
    args = parser.parse_args()

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

    # 載入風味標籤翻譯表 (可選,沒有也不影響運作,只是會保留日文)
    tag_translations_path = DATA_DIR / "flavor_tags_zhtw.json"
    tag_translations = {}
    if tag_translations_path.exists():
        raw_translations = load_json(tag_translations_path)
        # 跳過 _comment / _usage 等說明欄位
        tag_translations = {k: v for k, v in raw_translations.items() if not k.startswith("_")}
        print(f"  loaded {len(tag_translations)} flavor tag translations")
    else:
        print(f"  no flavor tag translations file (will keep Japanese tags)")

    if args.mode == "all":
        print("\nMode: ALL (抓取 Sakenowa 全部資料)")
        brewery_rows, product_rows = build_all_rows(idx, regions, tag_translations)
        unmatched = []
        matched_count = len(brewery_rows)
        targets_count = len(brewery_rows)
    else:
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
            product_rows.extend(build_product_rows(match, idx, regions, tag_translations))

        matched_count = len(matched)
        targets_count = len(targets)

    print(f"\n  produced: {len(brewery_rows)} breweries / {len(product_rows)} products")
    if unmatched:
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
        f"Mode: {args.mode}",
        "=" * 60,
        f"Sakenowa total: {len(idx['breweries_by_id'])} breweries / {len(idx['brands_by_id'])} brands",
        f"Produced: {len(brewery_rows)} breweries / {len(product_rows)} products",
    ]
    if args.mode == "targets":
        report_lines += [
            f"Targets: {targets_count}",
            f"Matched: {matched_count}",
            f"Unmatched: {len(unmatched)}",
            "",
            "── Unmatched targets (need manual review) ──",
        ]
        for t in unmatched:
            report_lines.append(f"  {t['brand_jp']:20s} | {t['brewery_jp']:20s} | {t['area_jp']}")

    (DATA_DIR / "_match_report.txt").write_text("\n".join(report_lines), encoding="utf-8")

    print(f"\n✓ wrote {DATA_DIR / 'breweries.csv'}")
    print(f"✓ wrote {DATA_DIR / 'products.csv'}")
    print(f"✓ wrote {DATA_DIR / 'breweries.json'}")
    print(f"✓ wrote {DATA_DIR / 'products.json'}")
    print(f"✓ wrote {DATA_DIR / '_match_report.txt'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
