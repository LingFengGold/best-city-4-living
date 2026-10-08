"""为每个城市挑选 NOAA ISD 气象站并下载 2020-2024 年 ISD-Lite 逐时观测。"""
import csv, gzip, io, json, math, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from cities import CITIES

YEARS = range(2020, 2025)
RAW = os.path.join(os.path.dirname(__file__), "raw", "isd")
os.makedirs(RAW, exist_ok=True)

def dist(a, b, c, d):
    p = math.radians
    return 6371 * 2 * math.asin(math.sqrt(math.sin(p(c - a) / 2) ** 2 + math.cos(p(a)) * math.cos(p(c)) * math.sin(p(d - b) / 2) ** 2))

def fetch(sid, year):
    path = os.path.join(RAW, f"{sid}-{year}.gz")
    if not os.path.exists(path):
        try:
            data = urllib.request.urlopen(f"https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/{year}/{sid}-{year}.gz", timeout=60).read()
        except Exception:
            data = b""
        open(path, "wb").write(data)
    data = open(path, "rb").read()
    return gzip.decompress(data).decode() if data else ""

def coverage(sid):
    """3 小时一档的 UTC 时段中有温度+露点观测的比例。"""
    slots = set()
    for y in YEARS:
        for line in fetch(sid, y).splitlines():
            f = line.split()
            if int(f[3]) % 3 == 0 and f[4] != "-9999" and f[5] != "-9999":
                slots.add((f[0], f[1], f[2], f[3]))
    return len(slots) / (len(YEARS) * 365.25 * 8)

hist = list(csv.DictReader(open(sys.argv[1])))
out = []
for zh, aq, cc, lat, lon, region in CITIES:
    cands = []
    for h in hist:
        if not h["LAT"] or h["BEGIN"] > "20200101" or h["END"] < "20241231" or h["WBAN"] != "99999" and h["CTRY"] != "US":
            continue
        d = dist(lat, lon, float(h["LAT"]), float(h["LON"]))
        if d < 60:
            cands.append((d, h))
    cands.sort(key=lambda x: x[0])
    best = None
    with ThreadPoolExecutor(8) as ex:
        covs = list(ex.map(lambda c: coverage(c[1]["USAF"] + "-" + c[1]["WBAN"]), cands[:12]))
    for (d, h), cov in zip(cands[:12], covs):
        if cov >= 0.8:  # 取最近的、覆盖率 ≥80% 的站
            best = (d, h, cov)
            break
    if not best:  # 退而求其次：覆盖率最高且 ≥50% 的站
        ok = [(c[0], c[1], v) for c, v in zip(cands[:12], covs) if v >= 0.5]
        best = max(ok, key=lambda x: x[2]) if ok else None
    if not best:
        print("NONE", zh, [(c[1]["STATION NAME"], round(c[0]), round(v, 2)) for c, v in zip(cands, covs)])
        continue
    d, h, cov = best
    out.append(dict(zh=zh, aq=aq, cc=cc, region=region, lat=lat, lon=lon, station=h["USAF"] + "-" + h["WBAN"],
                    sname=h["STATION NAME"].title(), dist=round(d, 1), elev=float(h["ELEV(M)"] or 0), coverage=round(cov, 3)))
    print(zh, out[-1]["station"], out[-1]["sname"], out[-1]["dist"], "km", out[-1]["coverage"])
json.dump(out, open(os.path.join(os.path.dirname(__file__), "stations.json"), "w"), ensure_ascii=False, indent=1)
