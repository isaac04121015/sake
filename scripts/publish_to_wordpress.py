#!/usr/bin/env python3
"""
publish_to_wordpress.py
將 products_with_content.csv 同步到 WordPress (sakego.com.tw)。

預設策略:
- 自訂文章類型 (Custom Post Type) "sake_product"
- 自訂分類法 (Custom Taxonomy) "sake_region" / "sake_brewery"
- 用 sakenowa_brand_id 當作冪等鍵 (meta key),避免重複建立

需求:
  1. WordPress 安裝 Application Password (使用者個人資料頁面)
  2. 安裝外掛或主題 functions.php 註冊 CPT "sake_product"
  3. 環境變數:
       WP_BASE_URL=https://www.sakego.com.tw
       WP_USERNAME=admin_username
       WP_APP_PASSWORD=xxxx xxxx xxxx xxxx

用法:
  python publish_to_wordpress.py --dry-run        # 列出要做什麼
  python publish_to_wordpress.py --max 5          # 只發 5 筆 (測試)
  python publish_to_wordpress.py                  # 全部同步
  python publish_to_wordpress.py --status draft   # 以草稿狀態發布

注意:
  本腳本會檢查 sakenowa_brand_id meta,有則更新、無則新增。
  不會刪除 WordPress 上現有但 CSV 中沒有的文章 (避免誤刪)。
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

CPT_SLUG = "sake_product"  # 自訂文章類型 slug
TAXONOMY_REGION = "sake_region"
TAXONOMY_BREWERY = "sake_brewery"


def get_or_create_term(
    session: requests.Session,
    base_url: str,
    taxonomy: str,
    name: str,
    cache: dict,
) -> int | None:
    if not name:
        return None
    cache_key = f"{taxonomy}:{name}"
    if cache_key in cache:
        return cache[cache_key]

    # 搜尋
    r = session.get(
        f"{base_url}/wp-json/wp/v2/{taxonomy}",
        params={"search": name, "per_page": 100},
    )
    if r.ok:
        for term in r.json():
            if term.get("name") == name:
                cache[cache_key] = term["id"]
                return term["id"]

    # 沒找到就建立
    r = session.post(
        f"{base_url}/wp-json/wp/v2/{taxonomy}",
        json={"name": name},
    )
    if r.ok:
        term_id = r.json()["id"]
        cache[cache_key] = term_id
        return term_id

    print(f"    failed to create term {taxonomy}/{name}: {r.status_code} {r.text[:200]}")
    return None


def find_existing_post(
    session: requests.Session,
    base_url: str,
    sakenowa_brand_id: str,
) -> int | None:
    """根據 sakenowa_brand_id meta 找既有文章。"""
    r = session.get(
        f"{base_url}/wp-json/wp/v2/{CPT_SLUG}",
        params={
            "meta_key": "sakenowa_brand_id",
            "meta_value": sakenowa_brand_id,
            "per_page": 1,
            "status": "any",
        },
    )
    if r.ok:
        results = r.json()
        if results:
            return results[0]["id"]
    return None


def build_post_payload(product: dict, region_id: int | None, brewery_id: int | None,
                       status: str) -> dict:
    title_zhtw = product.get("name_zhtw") or product.get("name_jp", "")
    title_jp = product.get("name_jp", "")
    brewery_name = product.get("brewery_name_jp", "")

    title = f"{title_zhtw}｜{brewery_name}" if title_zhtw and brewery_name else title_zhtw or title_jp

    description = product.get("description", "").strip()
    tasting = product.get("tasting_note", "").strip()
    pairing = product.get("pairing", "").strip()

    # 內容區段
    content_parts = []
    if description:
        content_parts.append(f"<h2>關於這款酒</h2>\n<p>{description}</p>")
    if tasting:
        content_parts.append(f"<h2>品飲建議</h2>\n<p>{tasting}</p>")
    if pairing:
        content_parts.append(f"<h2>搭餐建議</h2>\n<p>{pairing}</p>")

    # 規格表
    spec_rows = []
    spec_map = [
        ("酒造", product.get("brewery_name_jp")),
        ("產地", product.get("area_zhtw") or product.get("area_jp")),
        ("酒類型", product.get("sake_type")),
        ("使用米", product.get("rice_variety")),
        ("米產地", product.get("rice_origin")),
        ("精米步合", f"{product.get('seimaibuai')}%" if product.get("seimaibuai") else ""),
        ("酵母", product.get("yeast")),
        ("酒精度", f"{product.get('abv')}%" if product.get("abv") else ""),
        ("日本酒度", product.get("smv")),
        ("酸度", product.get("acidity")),
    ]
    for label, value in spec_map:
        if value and str(value).strip():
            spec_rows.append(f"<tr><th>{label}</th><td>{value}</td></tr>")
    if spec_rows:
        content_parts.append(
            "<h2>規格</h2>\n<table class=\"sake-specs\">\n" +
            "\n".join(spec_rows) +
            "\n</table>"
        )

    payload = {
        "title": title,
        "content": "\n\n".join(content_parts),
        "status": status,
        "meta": {
            "sakenowa_brand_id": product.get("sakenowa_brand_id", ""),
            "sake_brewery_jp": product.get("brewery_name_jp", ""),
            "sake_brewery_id": product.get("brewery_id", ""),
            "sake_name_jp": product.get("name_jp", ""),
            "sake_area_jp": product.get("area_jp", ""),
            "sake_type": product.get("sake_type", ""),
            "sake_rice_variety": product.get("rice_variety", ""),
            "sake_seimaibuai": product.get("seimaibuai", ""),
            "sake_yeast": product.get("yeast", ""),
            "sake_abv": product.get("abv", ""),
            "sake_smv": product.get("smv", ""),
            "sake_acidity": product.get("acidity", ""),
            "sakenowa_brand_url": product.get("sakenowa_brand_url", ""),
        },
    }

    taxonomies = {}
    if region_id:
        taxonomies[TAXONOMY_REGION] = [region_id]
    if brewery_id:
        taxonomies[TAXONOMY_BREWERY] = [brewery_id]
    payload.update(taxonomies)

    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max", type=int, default=0)
    parser.add_argument("--status", default="draft", choices=["draft", "publish", "private"])
    parser.add_argument("--source", default="products_with_content.csv",
                        help="CSV 檔名 (預設 products_with_content.csv)")
    args = parser.parse_args()

    base_url = os.environ.get("WP_BASE_URL", "").rstrip("/")
    username = os.environ.get("WP_USERNAME")
    password = os.environ.get("WP_APP_PASSWORD")

    if not args.dry_run and not all([base_url, username, password]):
        print("ERROR: 請設定環境變數 WP_BASE_URL / WP_USERNAME / WP_APP_PASSWORD",
              file=sys.stderr)
        return 1

    source_path = DATA_DIR / args.source
    if not source_path.exists():
        print(f"ERROR: {source_path} 不存在,請先跑 generate_content.py", file=sys.stderr)
        return 1

    with source_path.open(encoding="utf-8-sig") as f:
        products = list(csv.DictReader(f))

    if args.max > 0:
        products = products[: args.max]

    print(f"Source: {source_path}")
    print(f"Records: {len(products)}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else f'PUBLISH (status={args.status})'}")
    print(f"Target: {base_url or '(dry-run)'}")
    print()

    if args.dry_run:
        for p in products[:10]:
            print(f"  [{p.get('area_zhtw')}] {p.get('brewery_name_jp')} / {p.get('name_jp')}"
                  f" → CPT post (sakenowa_id={p.get('sakenowa_brand_id')})")
        if len(products) > 10:
            print(f"  ... and {len(products) - 10} more")
        return 0

    session = requests.Session()
    session.auth = HTTPBasicAuth(username, password)
    session.headers.update({"User-Agent": "sakego-publisher/1.0"})

    term_cache: dict = {}
    created = updated = failed = 0

    for i, product in enumerate(products, 1):
        sn_id = product.get("sakenowa_brand_id", "")
        if not sn_id:
            print(f"[{i}] skip: no sakenowa_brand_id")
            continue

        print(f"[{i}/{len(products)}] {product.get('brewery_name_jp')} / {product.get('name_jp')}")

        # taxonomies
        region_term = get_or_create_term(
            session, base_url, TAXONOMY_REGION,
            product.get("area_zhtw") or product.get("area_jp", ""),
            term_cache,
        )
        brewery_term = get_or_create_term(
            session, base_url, TAXONOMY_BREWERY,
            product.get("brewery_name_jp", ""),
            term_cache,
        )

        payload = build_post_payload(product, region_term, brewery_term, args.status)

        # upsert
        existing_id = find_existing_post(session, base_url, sn_id)
        try:
            if existing_id:
                r = session.post(
                    f"{base_url}/wp-json/wp/v2/{CPT_SLUG}/{existing_id}",
                    json=payload,
                )
                if r.ok:
                    updated += 1
                    print(f"  ✓ updated post #{existing_id}")
                else:
                    failed += 1
                    print(f"  ✗ update failed: {r.status_code} {r.text[:200]}")
            else:
                r = session.post(
                    f"{base_url}/wp-json/wp/v2/{CPT_SLUG}",
                    json=payload,
                )
                if r.ok:
                    created += 1
                    print(f"  ✓ created post #{r.json()['id']}")
                else:
                    failed += 1
                    print(f"  ✗ create failed: {r.status_code} {r.text[:200]}")
        except requests.RequestException as e:
            failed += 1
            print(f"  ✗ exception: {e}")

        time.sleep(0.5)  # 對 WP API 有禮貌

    print(f"\n{'=' * 60}")
    print(f"Created: {created}  Updated: {updated}  Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
