"""Build size-sorted CSV exports from apps/web/public/image-review/data.json."""

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "apps/web/public/image-review"
images = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))["images"]

HEADERS = [
    "大小排名", "文件大小(B)", "文件大小(KiB)", "物种首次登场世代", "中文名", "物种英文名",
    "图片所属", "宝可梦ID", "形态ID", "图片类型", "宽(px)", "高(px)", "卷内路径", "预览地址",
]


def write_csv(name: str, records: list[dict]) -> None:
    with (ROOT / name).open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(HEADERS)
        for rank, item in enumerate(records, 1):
            writer.writerow([
                rank,
                item["bytes"],
                f"{item['bytes'] / 1024:.2f}",
                item["generation"],
                item["chineseName"],
                item["speciesName"],
                "形态" if item["formId"] else "宝可梦",
                item["pokemonId"],
                item["formId"],
                item["kind"],
                item["width"],
                item["height"],
                item["path"],
                f"http://127.0.0.1:3000/media/{item['path']}",
            ])


write_csv("all-images-by-size.csv", images)
write_csv("venusaur-images-by-size.csv", [item for item in images if item["speciesId"] == 3])

generations = defaultdict(lambda: {"files": 0, "bytes": 0})
for item in images:
    totals = generations[item["generation"]]
    totals["files"] += 1
    totals["bytes"] += item["bytes"]
print(f"Exported {len(images)} images. Generation totals:")
for generation, totals in sorted(generations.items()):
    print(generation, totals["files"], f"{totals['bytes'] / 1024 / 1024:.1f} MiB")
