"""Quick check: is Chrome CDP reachable on port 9222?"""
import urllib.request
import json
import time

time.sleep(2)

try:
    r = urllib.request.urlopen("http://localhost:9222/json", timeout=5)
    tabs = json.loads(r.read())
    print(f"Chrome CDP reachable! Open tabs: {len(tabs)}")
    for t in tabs[:5]:
        print(f"  - {t.get('title', 'untitled')}: {t.get('url', '')}")
except Exception as e:
    print(f"Chrome not reachable: {e}")
