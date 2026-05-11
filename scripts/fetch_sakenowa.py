#!/usr/bin/env python3
"""
fetch_sakenowa.py
從 Sakenowa Data Project API 抓取所有公開資料,儲存為 raw JSON。

API 文件: https://muro.sakenowa.com/sakenowa-data/
端點:
  GET /areas             - 47 都道府縣
  GET /breweries         - 全部酒造 (1500+ 家)
  GET /brands            - 全部銘柄/品牌 (5000+)
  GET /flavor-charts     - 風味雷達圖數據 (6 軸: f1-f6)
  GET /flavor-tags       - 風味標籤主表
  GET /brand-flavor-tags - 每個銘柄的風味標籤
  GET /rankings          - 排名

輸出:
  data/raw/{endpoint}.json (每個端點一個 JSON 檔)
  data/raw/_meta.json     (抓取時間戳)
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import requests

API_BASE = "https://muro.sakenowa.com/sakenowa-data/api"
ENDPOINTS = [
    "areas",
    "breweries",
    "brands",
    "flavor-charts",
    "flavor-tags",
    "brand-flavor-tags",
    "rankings",
]

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"


def fetch_endpoint(name: str, retries: int = 3, backoff: float = 2.0) -> dict:
    """抓單一端點,有重試機制。"""
    url = f"{API_BASE}/{name}"
    last_error = None

    for attempt in range(retries):
        try:
            print(f"  GET {url} (attempt {attempt + 1}/{retries})", flush=True)
            response = requests.get(
                url,
                timeout=30,
                headers={
                    "User-Agent": "sakego-data-collector/1.0 (https://www.sakego.com.tw)",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data
        except (requests.RequestException, ValueError) as e:
            last_error = e
            print(f"    error: {e}", flush=True)
            if attempt < retries - 1:
                sleep_time = backoff ** attempt
                print(f"    retrying in {sleep_time}s...", flush=True)
                time.sleep(sleep_time)

    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts: {last_error}")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching Sakenowa API data → {OUTPUT_DIR}")
    print("=" * 60)

    meta = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "endpoints": {},
    }

    for endpoint in ENDPOINTS:
        print(f"\n[{endpoint}]")
        try:
            data = fetch_endpoint(endpoint)
            output_path = OUTPUT_DIR / f"{endpoint}.json"
            output_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            # 統計筆數 (Sakenowa 各端點都是 {endpoint_name: [...]} 結構)
            count = 0
            if isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        count = max(count, len(v))

            meta["endpoints"][endpoint] = {
                "count": count,
                "file": output_path.name,
            }
            print(f"  ✓ saved {count} records → {output_path.name}")
            time.sleep(1.0)  # 對 API 有禮貌

        except Exception as e:
            print(f"  ✗ FAILED: {e}", flush=True)
            meta["endpoints"][endpoint] = {"error": str(e)}

    meta_path = OUTPUT_DIR / "_meta.json"
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print(f"Done. Meta written to {meta_path.name}")

    failed = [k for k, v in meta["endpoints"].items() if "error" in v]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
