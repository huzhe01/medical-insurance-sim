# 九江开封医保击穿点

按江西九江、河南开封的医保参数，模拟退休后职工医保与居民医保的自付差别，以及加买惠民保前后多大的医疗账单会花光积蓄。

在线查看：https://huzhe01.github.io/medical-insurance-sim/

- `index.html`：页面源文件（模型在 `<script id="model">` 的 `CITIES` 字典里，换城市改这里）
- `build.py`：生成 `docs/index.html`（GitHub Pages 从 `/docs` 发布）
- `simulate.py`：第一版，用全国代表性参数画静态图

参数来自公开政策文件和媒体报道，部分未经官方原文核实（页面内标 †）。仅为估算，不构成参保或投保建议，办理前请以当地医保局和保险条款为准。
