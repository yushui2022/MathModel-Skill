import json
import sys
from pathlib import Path
import requests
import pandas as pd
import time
import random

# Base paths
BASE_DIR = Path.cwd()
OUTPUT_DIR = BASE_DIR / "crawled_data"
CONFIG_FILE = BASE_DIR / "data_requirements.json"

OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
(OUTPUT_DIR / "raw").mkdir(exist_ok=True)
(OUTPUT_DIR / "processed").mkdir(exist_ok=True)

def load_config():
    """Load or create the data configuration file."""
    if not CONFIG_FILE.exists():
        print(f"ℹ️ {CONFIG_FILE.name} not found. Creating a template...")
        template = {
            "tasks": [
                {
                    "type": "direct_download",
                    "url": "https://example.com/data.csv",
                    "save_name": "example_data.csv",
                    "active": False
                },
                {
                    "type": "scrape_tables",
                    "url": "https://en.wikipedia.org/wiki/List_of_countries_by_GDP_(nominal)",
                    "save_prefix": "gdp_table",
                    "active": False
                },
                {
                    "type": "manual_search",
                    "query": "2023年全球半导体产量统计",
                    "notes": "Need to find authoritative report manually if API fails",
                    "active": False
                }
            ]
        }
        CONFIG_FILE.write_text(json.dumps(template, indent=4, ensure_ascii=False), encoding="utf-8")
        return template
    
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️ Error reading config: {e}")
        return {"tasks": []}

def task_direct_download(task):
    url = task.get("url")
    name = task.get("save_name", "downloaded_file.dat")
    if not url: return
    
    print(f"⬇️ Downloading: {url}...")
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            p = OUTPUT_DIR / "raw" / name
            p.write_bytes(resp.content)
            print(f"   ✅ Saved to {p}")
        else:
            print(f"   ❌ Failed with status {resp.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def task_scrape_tables(task):
    url = task.get("url")
    prefix = task.get("save_prefix", "table")
    if not url: return
    
    print(f"🕸️ Scraping tables from: {url}...")
    try:
        # Use pandas to extract tables
        dfs = pd.read_html(url)
        print(f"   ✅ Found {len(dfs)} tables.")
        for i, df in enumerate(dfs):
            p = OUTPUT_DIR / "processed" / f"{prefix}_{i}.csv"
            df.to_csv(p, index=False, encoding="utf-8-sig")
            print(f"      Saved table {i} to {p}")
    except Exception as e:
        print(f"   ❌ Error scraping tables (missing lxml/html5lib?): {e}")

def main():
    print("=== Authoritative Data Harvester (Customizable) ===")
    config = load_config()
    tasks = config.get("tasks", [])
    
    active_tasks = [t for t in tasks if t.get("active", False)]
    
    if not active_tasks:
        print(f"⚠️ No active tasks found in {CONFIG_FILE.name}.")
        print(f"👉 Please edit {CONFIG_FILE.name} to add your custom data sources (URL, API, etc.).")
        print("   Set 'active': true for tasks you want to run.")
        return
    
    print(f"🚀 Found {len(active_tasks)} active tasks.")
    for task in active_tasks:
        ttype = task.get("type")
        if ttype == "direct_download":
            task_direct_download(task)
        elif ttype == "scrape_tables":
            task_scrape_tables(task)
        elif ttype == "manual_search":
            print(f"🔍 [Manual Search Reminder] Please search for: {task.get('query')}")
        else:
            print(f"❓ Unknown task type: {ttype}")
        
        # Polite delay
        time.sleep(random.uniform(1, 2))

if __name__ == "__main__":
    main()
