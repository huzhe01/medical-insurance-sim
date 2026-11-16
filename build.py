"""把 Artifact 版 index.html（无 doctype）包成可独立打开的 docs/index.html，供 GitHub Pages 发布。
用法：python3 build.py
"""
from pathlib import Path

root = Path(__file__).parent
body = (root / "index.html").read_text(encoding="utf-8")
title_end = body.index("</title>") + len("</title>")
head = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="按江西九江、河南开封的医保参数，模拟退休后职工医保与居民医保的自付差别，以及加买惠民保前后多大的医疗账单会花光积蓄。">
{body[:title_end].strip()}
<style>html{{color-scheme:light}}body{{margin:0}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
</head>
<body>
"""
out = root / "docs" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(head + body[title_end:].strip() + "\n</body>\n</html>\n", encoding="utf-8")
print("wrote", out, out.stat().st_size, "bytes")
