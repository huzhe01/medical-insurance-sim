"""退休后 职工医保 vs 居民医保 自付金额模拟。

参数为"全国代表性取值"（三级医院、退休人员），各地差异很大，改 PLANS 即可重算。
金额单位：元。运行：python3 simulate.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).parent

# ---------- 1. 假设 ----------
SAVINGS = 500_000      # 60 岁时的积蓄
RATE = 0.02            # 年利息

PLANS = {
    "职工医保（退休）": dict(
        color="#2a78d6",
        premium=0, premium_growth=0,      # 缴满年限后退休不再缴费
        account=1000,                     # 个人账户每年划入（约 80 元/月）
        op_deduct=200, op_rate=0.65, op_cap=6000,          # 普通门诊统筹
        ip_deduct=800, ip_rate=0.88, ip_cap=300_000,       # 住院基本统筹（基金支付封顶）
        second="excess", s_rate=0.85, s_cap=400_000,       # 大额医疗补助：超封顶线部分报 85%
    ),
    "居民医保": dict(
        color="#eb6834",
        premium=400, premium_growth=20,   # 个人缴费，每年约涨 20 元
        account=0,
        op_deduct=200, op_rate=0.50, op_cap=1000,
        ip_deduct=1200, ip_rate=0.62, ip_cap=200_000,
        second="burden", s_threshold=15_000, s_rate=0.60, s_cap=300_000,  # 大病保险
    ),
}


# ---------- 2. 报销模型 ----------
def outpatient(cost, alpha, p):
    """普通门诊：返回 (个人自付, 基金支付)。alpha = 目录外自费占比。"""
    elig = cost * (1 - alpha)
    pay = min(max(elig - p["op_deduct"], 0) * p["op_rate"], p["op_cap"])
    return cost - pay, pay


def inpatient(cost, alpha, p):
    """住院/大病：一个年度内的总费用 cost。返回 dict 明细。"""
    elig = cost * (1 - alpha)                      # 政策范围内费用
    base = min(max(elig - p["ip_deduct"], 0) * p["ip_rate"], p["ip_cap"])
    if p["second"] == "excess":                    # 职工：超过基本封顶线的那部分费用再报
        used = p["ip_deduct"] + p["ip_cap"] / p["ip_rate"]
        second = min(max(elig - used, 0) * p["s_rate"], p["s_cap"])
    else:                                          # 居民：政策内个人负担超过起付线的部分再报
        burden = elig - base
        second = min(max(burden - p["s_threshold"], 0) * p["s_rate"], p["s_cap"])
    oop = cost - base - second
    return dict(cost=cost, out_of_list=cost * alpha, base=base, second=second, oop=oop)


def solve_bill(target_oop, alpha, p, hi=2e7):
    """自付 = target_oop 时对应的总医疗费（自付随总费用单调递增，二分即可）。"""
    lo = 0.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if inpatient(mid, alpha, p)["oop"] < target_oop:
            lo = mid
        else:
            hi = mid
    return lo


# ---------- 3. 情景 ----------
SCENARIOS = [  # (名称, 年度总费用, 目录外占比, 类型)
    ("小病：普通门诊\n一年 3 千", 3_000, 0.10, "op"),
    ("门诊较多\n一年 8 千", 8_000, 0.10, "op"),
    ("普通住院\n肺炎/胆囊手术 2 万", 20_000, 0.10, "ip"),
    ("较大手术\n心脏支架/关节置换 8 万", 80_000, 0.15, "ip"),
    ("癌症首年\n手术+化疗+靶向 30 万", 300_000, 0.25, "ip"),
    ("重症\nICU/多线抗癌 80 万", 800_000, 0.30, "ip"),
]


def scenario_oop(s, p):
    _, cost, alpha, kind = s
    return outpatient(cost, alpha, p)[0] if kind == "op" else inpatient(cost, alpha, p)["oop"]


# ---------- 4. 多年路径 ----------
def path(p, events, start=60, end=85, routine=3_000):
    """积蓄只用来付医疗（生活费假设由养老金覆盖）。events: {年龄: (费用, 目录外占比)}"""
    s, ages, bal = SAVINGS, [], []
    for i, age in enumerate(range(start, end + 1)):
        ages.append(age); bal.append(s)
        spend = p["premium"] + p["premium_growth"] * i
        spend += max(outpatient(routine, 0.10, p)[0] - p["account"], 0)
        if age in events:
            spend += inpatient(*events[age], p)["oop"]
        s = s * (1 + RATE) - spend
    return ages, bal


EVENTS = {68: (300_000, 0.25), 69: (150_000, 0.25), 70: (150_000, 0.25), 78: (800_000, 0.30)}

# ---------- 5. 画图 ----------
plt.rcParams.update({
    "font.family": "Hiragino Sans GB", "axes.unicode_minus": False,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#c9c8c2", "axes.labelcolor": "#52514e",
    "xtick.color": "#52514e", "ytick.color": "#52514e", "text.color": "#0b0b0b",
    "axes.grid": True, "grid.color": "#e9e8e3", "grid.linewidth": 0.8, "axes.axisbelow": True,
    "font.size": 11,
})
INK2 = "#52514e"
wan = lambda x: x / 1e4


def titled(fig, title, sub):
    fig.text(0.04, 0.955, title, fontsize=17, fontweight="bold", va="top")
    fig.text(0.04, 0.905, sub, fontsize=11, color=INK2, va="top")


def fig1_rules():
    rows = [
        ("", "职工医保（退休）", "居民医保"),
        ("退休后个人缴费", "0（已缴满年限）", "约 400 元/年，逐年上涨"),
        ("个人账户", "每年划入约 1000 元", "无"),
        ("普通门诊", "起付 200，报 65%，基金年封顶 6000", "起付 200，报 50%，基金年封顶 1000"),
        ("住院起付线（三级）", "800 元", "1200 元"),
        ("住院政策内报销比例", "88%", "62%"),
        ("基本统筹年封顶（基金支付）", "30 万", "20 万"),
        ("二次报销", "大额医疗补助：超封顶部分报 85%，\n再封顶 40 万", "大病保险：政策内自付超 1.5 万\n的部分报 60%，封顶 30 万"),
        ("目录外费用（进口药/耗材等）", "全部自费", "全部自费"),
    ]
    fig = plt.figure(figsize=(12, 8.6))
    titled(fig, "图 1｜模拟用的假设与报销规则",
           "积蓄 50 万、年利息 2%（约 1 万/年）、60 岁已退休；生活费假设由养老金覆盖，积蓄只用于看病。参数为代表性取值，各地不同。")
    ax = fig.add_axes([0.04, 0.2, 0.92, 0.66]); ax.axis("off")
    xs, n = [0.0, 0.30, 0.66], len(rows)
    for i, r in enumerate(rows):
        y = 1 - (i + 0.5) / n
        if i == 0:
            ax.add_patch(plt.Rectangle((0, 1 - 1 / n), 1, 1 / n, color="#efeeea", lw=0))
        ax.plot([0, 1], [1 - (i + 1) / n] * 2, color="#e1e0da", lw=0.8)
        for j, (x, t) in enumerate(zip(xs, r)):
            ax.text(x + 0.012, y, t, va="center", fontsize=11.5,
                    fontweight="bold" if i == 0 or j == 0 else "normal",
                    color="#0b0b0b" if j or i == 0 else INK2)
    for x, name in zip(xs[1:], PLANS):
        ax.add_patch(plt.Rectangle((x, 1 - 1 / n), 0.006, 1 / n, color=PLANS[name]["color"], lw=0))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.text(0.04, 0.155, "推导公式（一个年度内）", fontsize=12.5, fontweight="bold")
    fig.text(0.04, 0.125,
             "① 政策内费用 = 总费用 ×（1 - 目录外占比）\n"
             "② 基本统筹支付 = min[（政策内费用 - 起付线）× 报销比例， 封顶线 ]\n"
             "③ 二次报销 = 职工：超出封顶线对应费用 × 85%（有上限）；居民：（政策内自付 - 1.5 万）× 60%（有上限）\n"
             "④ 个人自付 = 总费用 - ② - ③      ⑤ 击穿点 = 令 个人自付 = 50 万，反解总费用",
             fontsize=11, color=INK2, va="top", linespacing=1.7)
    fig.savefig(OUT / "fig1_假设与规则.png", dpi=170); plt.close(fig)


def fig2_scenarios():
    fig = plt.figure(figsize=(12, 8.2))
    titled(fig, "图 2｜六个看病情景：同样的账单，各自要掏多少钱",
           "条形 = 个人自付金额（万元）；括号内 = 自付占总费用的比例。右侧灰字 = 居民医保比职工医保多掏的钱。")
    ax = fig.add_axes([0.21, 0.09, 0.62, 0.74])
    h = 0.36
    for i, s in enumerate(SCENARIOS):
        vals = []
        for k, (name, p) in enumerate(PLANS.items()):
            v = scenario_oop(s, p); vals.append(v)
            y = i + (k - 0.5) * (h + 0.04)
            ax.barh(y, wan(v), height=h, color=p["color"], label=name if i == 0 else None)
            ax.text(wan(v) + 0.5, y, f"{wan(v):.2f} 万（{v / s[1]:.0%}）", va="center", fontsize=10.5)
        ax.text(1.02, i, f"多掏 {wan(vals[1] - vals[0]):.2f} 万", transform=ax.get_yaxis_transform(),
                va="center", fontsize=11, color=INK2)
    ax.set_yticks(range(len(SCENARIOS)), [s[0] for s in SCENARIOS], fontsize=11, color="#0b0b0b")
    ax.invert_yaxis(); ax.grid(axis="y", visible=False)
    ax.set_xlabel("个人自付（万元）"); ax.set_xlim(0, 48)
    ax.legend(loc="upper right", frameon=False)
    fig.savefig(OUT / "fig2_六个情景.png", dpi=170); plt.close(fig)


def fig3_curve(alpha=0.25):
    fig = plt.figure(figsize=(12, 7.6))
    titled(fig, "图 3｜一年总医疗费涨到多少，会把 50 万积蓄击穿",
           f"横轴 = 一年内的总医疗费，纵轴 = 个人自付；目录外自费占比取 {alpha:.0%}（大病常见水平）。曲线变陡的地方 = 报销封顶。")
    ax = fig.add_axes([0.07, 0.1, 0.88, 0.72])
    xs = np.linspace(0, 1_600_000, 801)
    for name, p in PLANS.items():
        ys = [inpatient(x, alpha, p)["oop"] for x in xs]
        ax.plot(wan(xs), wan(np.array(ys)), color=p["color"], lw=2.4, label=name)
        t = solve_bill(SAVINGS, alpha, p)
        ax.plot([wan(t)], [50], "o", ms=9, color=p["color"], mec="#fcfcfb", mew=2, zorder=5)
        ax.annotate(f"{name}\n击穿点 ≈ {wan(t):.0f} 万", (wan(t), 50),
                    xytext=(wan(t) + (8 if "职工" in name else -6), 38 if "职工" in name else 66),
                    ha="left" if "职工" in name else "right", fontsize=11.5,
                    arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.axhline(50, color="#0b0b0b", lw=1, ls=(0, (4, 3)))
    ax.text(2, 51.2, "积蓄 50 万", fontsize=11)
    ax.plot(wan(xs), wan(xs), color="#b5b4ad", lw=1, ls=":")
    ax.text(72, 76, "完全没医保", color=INK2, fontsize=10, rotation=33)
    ax.set_xlim(0, 160); ax.set_ylim(0, 90)
    ax.set_xlabel("一年内总医疗费（万元）"); ax.set_ylabel("个人自付（万元）")
    ax.legend(loc="lower right", frameon=False)
    fig.savefig(OUT / "fig3_击穿曲线.png", dpi=170); plt.close(fig)


def fig4_thresholds():
    alphas = [0.10, 0.20, 0.30, 0.40]
    fig = plt.figure(figsize=(12, 7.2))
    titled(fig, "图 4｜击穿点对「目录外自费占比」的敏感度",
           "左：一年总医疗费到多少会花光 50 万。右：只靠每年 1 万利息（不动本金）能扛多大的账单。单位：万元。")
    for col, (target, ttl) in enumerate([(SAVINGS, "花光 50 万积蓄的总医疗费"),
                                         (SAVINGS * RATE, "只用 1 万利息能付的总医疗费")]):
        ax = fig.add_axes([0.07 + col * 0.48, 0.12, 0.41, 0.66])
        w = 0.36
        for k, (name, p) in enumerate(PLANS.items()):
            vals = [wan(solve_bill(target, a, p)) for a in alphas]
            x = np.arange(len(alphas)) + (k - 0.5) * (w + 0.03)
            ax.bar(x, vals, width=w, color=p["color"], label=name)
            for xi, v in zip(x, vals):
                ax.text(xi, v + max(vals) * 0.015, f"{v:.0f}" if v >= 20 else f"{v:.1f}",
                        ha="center", fontsize=10.5)
        ax.set_xticks(range(len(alphas)), [f"目录外 {a:.0%}" for a in alphas])
        ax.grid(axis="x", visible=False); ax.set_title(ttl, fontsize=12.5, loc="left", pad=10)
        if col == 0:
            ax.legend(frameon=False, loc="upper right")
    fig.text(0.07, 0.035, "两段封顶都用完后：击穿点 = 50 万积蓄 + 医保年度最高支付（职工 30+40=70 万；居民 20+30=50 万），所以左图前几组不随目录外占比变化。", fontsize=10.5, color=INK2)
    fig.savefig(OUT / "fig4_阈值敏感度.png", dpi=170); plt.close(fig)


def fig5_path():
    fig = plt.figure(figsize=(12, 7.6))
    titled(fig, "图 5｜60–85 岁积蓄余额：只有小病 vs. 中途两次大病",
           "实线 = 每年只有 3000 元门诊；虚线 = 68–70 岁癌症（30+15+15 万）且 78 岁重症 80 万。积蓄按 2% 生息，只用于医疗。")
    ax = fig.add_axes([0.07, 0.1, 0.8, 0.72])
    for name, p in PLANS.items():
        for ev, ls in [({}, "-"), (EVENTS, (0, (5, 3)))]:
            ages, bal = path(p, ev)
            ax.plot(ages, wan(np.array(bal)), color=p["color"], lw=2.2, ls=ls)
            tag = "只有小病" if not ev else "两次大病"
            ax.text(85.4, wan(bal[-1]), f"{name[:4]}·{tag}\n{wan(bal[-1]):.0f} 万", va="center", fontsize=10.5)
    ax.axhline(0, color="#0b0b0b", lw=1)
    for a, t in [(68, "68 岁 癌症"), (78, "78 岁 重症")]:
        ax.axvline(a, color="#c9c8c2", lw=1, ls=":"); ax.text(a + 0.2, 4, t, color=INK2, fontsize=10)
    ax.set_xlim(60, 85); ax.set_xlabel("年龄"); ax.set_ylabel("积蓄余额（万元）")
    ax.plot([], [], color=INK2, lw=2.2, label="只有小病"); ax.plot([], [], color=INK2, lw=2.2, ls=(0, (5, 3)), label="两次大病")
    for name, p in PLANS.items():
        ax.plot([], [], color=p["color"], lw=2.2, label=name)
    ax.legend(frameon=False, loc="upper left", ncols=2)
    fig.savefig(OUT / "fig5_多年路径.png", dpi=170); plt.close(fig)


if __name__ == "__main__":
    print("== 情景自付（元） ==")
    for s in SCENARIOS:
        v = [scenario_oop(s, p) for p in PLANS.values()]
        print(f"{s[0].replace(chr(10), ' '):<28} 职工 {v[0]:>9,.0f} ({v[0]/s[1]:.0%})  居民 {v[1]:>9,.0f} ({v[1]/s[1]:.0%})  差 {v[1]-v[0]:>9,.0f}")
    print("== 阈值（万元）: 目录外占比 -> 击穿50万 / 只用利息1万 ==")
    for a in (0.10, 0.20, 0.25, 0.30, 0.40):
        print(f"α={a:.0%}", {n[:2]: (round(wan(solve_bill(SAVINGS, a, p)), 1), round(wan(solve_bill(SAVINGS * RATE, a, p)), 2)) for n, p in PLANS.items()})
    print("== 85 岁余额（万元） ==")
    for n, p in PLANS.items():
        print(n, [round(wan(path(p, ev)[1][-1]), 1) for ev in ({}, EVENTS)])
    for f in (fig1_rules, fig2_scenarios, fig3_curve, fig4_thresholds, fig5_path):
        f()
    print("图片已写入", OUT)
