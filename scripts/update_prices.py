"""Pull livestock prices from the USDA AMS MyMarketNews (MARS) API.

Runs in GitHub Actions. The API key comes from the USDA_API_KEY secret and is
never written to disk or printed.

  python scripts/update_prices.py          # refresh docs/prices.json
  python scripts/update_prices.py --probe  # save raw report samples to samples/
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://marsapi.ams.usda.gov/services/v1.2/reports"
ROOT = Path(__file__).resolve().parent.parent
PRICES_FILE = ROOT / "docs" / "prices.json"
SAMPLES_DIR = ROOT / "samples"

# USDA report IDs (slug IDs). View any of them at
# https://mymarketnews.ams.usda.gov/viewReport/<id>
REPORTS = {
    "hogs": 3458,          # LM_HG218 Daily Direct Prior Day Hog Report
    "fed_cattle": 2477,    # LM_CT150 5 Area Weekly Weighted Avg Direct Slaughter Cattle
    "feeder_pigs": 2810,   # National Direct Feeder Pig Report (weekly)
    "feeder_cattle": 3233, # Weekly National Feeder & Stocker Cattle Summary
}


def api_get(path):
    key = os.environ.get("USDA_API_KEY", "").strip()
    if not key:
        sys.exit("USDA_API_KEY is not set.")
    token = base64.b64encode(f"{key}:".encode()).decode()
    req = urllib.request.Request(
        f"{API}/{path}",
        headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def trim(value, depth=0):
    """Shorten long lists so samples stay small and readable."""
    if isinstance(value, list):
        return [trim(v, depth + 1) for v in value[:40]]
    if isinstance(value, dict):
        return {k: trim(v, depth + 1) for k, v in value.items()}
    return value


def probe():
    SAMPLES_DIR.mkdir(exist_ok=True)
    for name, slug in REPORTS.items():
        out = {"slug": slug, "requests": {}}
        for query in ("", "?lastReports=1", "?lastReports=1&allSections=true"):
            try:
                out["requests"][query or "(none)"] = trim(api_get(f"{slug}{query}"))
            except urllib.error.HTTPError as e:
                out["requests"][query or "(none)"] = {"error": e.code, "body": e.read().decode(errors="replace")[:500]}
            except Exception as e:  # keep probing the other reports
                out["requests"][query or "(none)"] = {"error": repr(e)}
        (SAMPLES_DIR / f"{name}.json").write_text(json.dumps(out, indent=2))
        print(f"saved samples/{name}.json")


def main():
    if "--probe" in sys.argv:
        probe()
        return
    sys.exit("Price parsing is not written yet. Run with --probe first.")


if __name__ == "__main__":
    main()
