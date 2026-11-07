import json
import statistics
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
queries = ["皮卡", "Pikachu", "Mega Female", "Galarian Zen Mode", "25"]
results = {}
for q in queries:
    times = []
    for i in range(4):
        start = time.perf_counter()
        with urllib.request.urlopen(
            base
            + "/api/v1/pokemon?"
            + urllib.parse.urlencode({"q": q, "locale": "zh-Hans", "pageSize": 48}),
            timeout=60,
        ) as response:
            data = json.load(response)
        times.append(round((time.perf_counter() - start) * 1000, 2))
    results[q] = {
        "ms": times,
        "median_ms": statistics.median(times),
        "total": data["total"],
        "ids": [p["id"] for p in data["items"]],
    }
print(json.dumps(results, ensure_ascii=False, indent=2))
