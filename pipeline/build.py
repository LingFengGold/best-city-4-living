"""用法: python3 build.py <aqicn pm25 csv 目录>

把 ISD-Lite 气象观测和 aqicn PM2.5 日数据压缩成网页使用的 data.json。

每个城市只保留 UTC 0/3/6/.../21 点的观测（中国站点只有这 8 个时次，统一口径），
时间换算成当地时间（含夏令时），温度/露点精度 0.5°C，风速精度 0.5 m/s。
另附 Open-Meteo（ERA5）每日白天平均总云量，用来判定晴天。
"""
import base64, csv, glob, gzip, json, os, sys
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
YEARS = range(2020, 2025)
START = date(2020, 1, 1)
NDAYS = (date(2024, 12, 31) - START).days + 1

TZ = {"CN": "Asia/Shanghai", "HK": "Asia/Hong_Kong", "MO": "Asia/Macau", "TW": "Asia/Taipei", "JP": "Asia/Tokyo",
      "KR": "Asia/Seoul", "SG": "Asia/Singapore", "TH": "Asia/Bangkok", "MY": "Asia/Kuala_Lumpur", "VN": "Asia/Ho_Chi_Minh",
      "LK": "Asia/Colombo", "IN": "Asia/Kolkata", "AE": "Asia/Dubai", "ZA": "Africa/Johannesburg", "KE": "Africa/Nairobi",
      "NZ": "Pacific/Auckland", "CO": "America/Bogota", "PE": "America/Lima", "EC": "America/Guayaquil",
      "BR": "America/Sao_Paulo", "AR": "America/Argentina/Buenos_Aires", "MX": "America/Mexico_City", "CA": "America/Vancouver",
      "PT": "Europe/Lisbon", "FR": "Europe/Paris", "GB": "Europe/London", "IT": "Europe/Rome", "GR": "Europe/Athens",
      "TR": "Europe/Istanbul", "DE": "Europe/Berlin", "ES": "Europe/Madrid"}
TZ_CITY = {"雅加达": "Asia/Jakarta", "巴厘岛": "Asia/Makassar", "悉尼": "Australia/Sydney", "墨尔本": "Australia/Melbourne",
           "布里斯班": "Australia/Brisbane", "珀斯": "Australia/Perth", "檀香山": "Pacific/Honolulu",
           "洛杉矶": "America/Los_Angeles", "圣迭戈": "America/Los_Angeles", "旧金山": "America/Los_Angeles",
           "西雅图": "America/Los_Angeles", "纽约": "America/New_York", "迈阿密": "America/New_York",
           "奥斯汀": "America/Chicago", "丰沙尔(马德拉)": "Atlantic/Madeira", "大加那利": "Atlantic/Canary",
           "特内里费": "Atlantic/Canary",
           "亚特兰大": "America/New_York", "夏洛特": "America/New_York", "罗利": "America/New_York",
           "纳什维尔": "America/Chicago", "孟菲斯": "America/Chicago", "华盛顿": "America/New_York",
           "巴尔的摩": "America/New_York", "费城": "America/New_York", "波士顿": "America/New_York",
           "芝加哥": "America/Chicago", "底特律": "America/Detroit", "明尼阿波利斯": "America/Chicago",
           "丹佛": "America/Denver", "盐湖城": "America/Denver", "博伊西": "America/Boise",
           "凤凰城": "America/Phoenix", "图森": "America/Phoenix", "拉斯维加斯": "America/Los_Angeles",
           "阿尔伯克基": "America/Denver", "埃尔帕索": "America/Denver", "达拉斯": "America/Chicago",
           "休斯顿": "America/Chicago", "圣安东尼奥": "America/Chicago", "俄克拉荷马城": "America/Chicago",
           "新奥尔良": "America/Chicago", "杰克逊维尔": "America/New_York", "塔拉哈西": "America/New_York",
           "奥兰多": "America/New_York", "坦帕": "America/New_York", "萨克拉门托": "America/Los_Angeles",
           "圣何塞": "America/Los_Angeles", "弗雷斯诺": "America/Los_Angeles", "波特兰": "America/Los_Angeles",
           "多伦多": "America/Toronto", "蒙特利尔": "America/Toronto", "渥太华": "America/Toronto",
           "卡尔加里": "America/Edmonton", "埃德蒙顿": "America/Edmonton", "维多利亚": "America/Vancouver",
           "哈利法克斯": "America/Halifax", "温尼伯": "America/Winnipeg"}

def half_month(d):
    return (d.month - 1) * 2 + (1 if d.day > 15 else 0)

def load_cloud(station):
    """每天当地 8-17 时（白天 10 个小时）ERA5 平均总云量，0-100；255 = 缺测。"""
    d = json.load(open(os.path.join(HERE, "raw", "sun", station + ".json")))
    cc = d["hourly"]["cloud_cover"]
    out = bytearray([255]) * NDAYS
    for i in range(min(NDAYS, len(cc) // 24)):
        v = [x for x in cc[i * 24 + 8:i * 24 + 18] if x is not None]
        if v:
            out[i] = round(sum(v) / len(v))
    return out

def load_aq():
    aq = {}
    for path in sorted(glob.glob(os.path.join(sys.argv[1], "*.csv"))):
        for row in csv.reader(open(path, encoding="utf-8")):
            day, cc, city, _, count, _, _, median = row[:8]
            d = (date.fromisoformat(day) - START).days
            if 0 <= d < NDAYS:
                aq.setdefault((cc, city), {})[d] = float(median)
    return aq

def main():
    stations = json.load(open(os.path.join(HERE, "stations.json")))
    aq = load_aq()
    out, blob = [], bytearray()
    for s in stations:
        tz = ZoneInfo(TZ_CITY.get(s["zh"]) or TZ[s["cc"]])
        hm, hr, t, td, ws, cl = bytearray(), bytearray(), bytearray(), bytearray(), bytearray(), bytearray()
        cloud = load_cloud(s["station"])
        for y in YEARS:
            raw = open(os.path.join(HERE, "raw", "isd", f"{s['station']}-{y}.gz"), "rb").read()
            for line in gzip.decompress(raw).decode().splitlines() if raw else []:
                f = line.split()
                if int(f[3]) % 3 or f[4] == "-9999" or f[5] == "-9999":
                    continue
                local = datetime(int(f[0]), int(f[1]), int(f[2]), int(f[3]), tzinfo=timezone.utc).astimezone(tz)
                hm.append(half_month(local)); hr.append(local.hour)
                di = (local.date() - START).days
                cl.append(cloud[di] if 0 <= di < NDAYS else 255)  # 观测所在当地日期的白天云量
                t.append(max(-127, min(127, round(int(f[4]) / 5))) & 0xFF)     # 0.5°C 精度
                td.append(max(-127, min(127, round(int(f[5]) / 5))) & 0xFF)
                ws.append(255 if f[8] == "-9999" else min(254, round(int(f[8]) / 5)))  # 0.5 m/s 精度
        days = aq.get((s["cc"], s["aq"]), {}) if s["aq"] else {}
        pm = [round(days[d]) if d in days else -1 for d in range(NDAYS)]
        blob.extend(hm + hr + t + td + ws + cl + cloud)
        if days:
            blob.extend(b"".join((v if v >= 0 else 0xFFFF).to_bytes(2, "little") for v in pm))
        out.append({k: s[k] for k in ("zh", "cc", "region", "station", "sname", "dist", "elev", "coverage", "aq")} |
                   {"tz": tz.key, "n": len(t), "hasAq": bool(days), "aqDays": len(days)})
        print(s["zh"], len(t), "obs,", len(days), "AQ days")
    # 二进制布局（按城市顺序拼接）：半月序号[n] 当地小时[n] 温度×2[n] 露点×2[n] 风速×2[n] 当日白天云量[n]，
    # 每日白天云量[ndays]，若有空气质量数据再接 PM2.5 AQI 日中位数 uint16[ndays]（0xFFFF=缺测）
    meta = {"start": START.isoformat(), "ndays": NDAYS, "cities": out}
    json.dump(meta | {"blob": base64.b64encode(gzip.compress(bytes(blob), 9)).decode()},
              open(os.path.join(HERE, "data.json"), "w"), ensure_ascii=False, separators=(",", ":"))

main()
