"""Write site/data/calendar.json: the dates the daily poem cares about.

Holds, for 2026-2036, the start date of every solar term (节气), the date of each
traditional festival, and the first day of every lunar month (so the page can
show today's lunar date without a lunar-calendar library).
"""

import datetime
import json
import os

from lunar_python import Solar

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site/data/calendar.json")
FIRST, LAST = datetime.date(2026, 1, 1), datetime.date(2036, 12, 31)

TERMS = {
    "立春": "lichun", "雨水": "yushui", "惊蛰": "jingzhe", "春分": "chunfen", "清明": "qingming", "谷雨": "guyu",
    "立夏": "lixia", "小满": "xiaoman", "芒种": "mangzhong", "夏至": "xiazhi", "小暑": "xiaoshu", "大暑": "dashu",
    "立秋": "liqiu", "处暑": "chushu", "白露": "bailu", "秋分": "qiufen", "寒露": "hanlu", "霜降": "shuangjiang",
    "立冬": "lidong", "小雪": "xiaoxue", "大雪": "daxue", "冬至": "dongzhi", "小寒": "xiaohan", "大寒": "dahan",
}
FESTIVALS = {
    "春节": "spring-festival", "元宵节": "lantern", "端午节": "duanwu", "七夕节": "qixi", "中秋节": "midautumn",
    "重阳节": "chongyang", "除夕": "new-year-eve",
}


def main():
    terms, festivals, months = [], [], []
    d = FIRST
    while d <= LAST:
        lunar = Solar.fromYmd(d.year, d.month, d.day).getLunar()
        iso = d.isoformat()
        jq = lunar.getJieQi()
        if jq in TERMS:
            terms.append([iso, TERMS[jq], jq])
            if jq == "清明":
                # Cold Food Day (寒食) is the day before Qingming.
                festivals.append([(d - datetime.timedelta(days=1)).isoformat(), "hanshi", "寒食"])
        for f in lunar.getFestivals():
            if f in FESTIVALS:
                festivals.append([iso, FESTIVALS[f], f])
        if lunar.getDay() == 1:
            months.append([iso, lunar.getMonth(), lunar.getMonthInChinese() + "月"])
        d += datetime.timedelta(days=1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"terms": terms, "festivals": sorted(festivals), "months": months}, f, ensure_ascii=False,
                  separators=(",", ":"))
    print(f"{len(terms)} terms, {len(festivals)} festivals, {len(months)} lunar months")


if __name__ == "__main__":
    main()
