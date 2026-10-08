"""从 Open-Meteo 历史接口（ERA5 再分析）下载 2020-2024 年每日日照时长、可照时长和逐时总云量。"""
import json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "raw", "sun")
os.makedirs(OUT, exist_ok=True)
for c in json.load(open(os.path.join(HERE, "stations.json"))):
    path = os.path.join(OUT, c["station"] + ".json")
    if os.path.exists(path):
        continue
    url = ("https://archive-api.open-meteo.com/v1/archive?latitude=%s&longitude=%s&start_date=2020-01-01&end_date=2024-12-31"
           "&daily=sunshine_duration,daylight_duration&hourly=cloud_cover&timezone=auto" % (c["lat"], c["lon"]))
    for attempt in range(5):
        try:
            data = urllib.request.urlopen(url, timeout=120).read()
            break
        except Exception as e:
            print("retry", c["zh"], e); time.sleep(30)
    open(path, "wb").write(data)
    print(c["zh"], len(data))
    time.sleep(1)
