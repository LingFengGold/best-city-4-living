# 宜居半月计算器

用 2020–2024 年 141 个城市的真实观测，统计每半个月里有多少比例的时刻"舒服"、有多少晴天。温度、露点、湿度、风速、时段、晴天和雾霾规则都可以在网页上自己定义。

灵感来自小红书帖子《号外！最宜居城市最客观计算结果！》，默认设定复刻了原帖的个人偏好。

## 数据来源

- **气象**：NOAA [ISD-Lite](https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/) 逐时地面观测（公有领域）
- **云量**：[Open-Meteo](https://open-meteo.com/) 历史天气接口，ERA5 再分析（CC BY 4.0）
- **空气质量**：[aqicn 开放数据平台](https://aqicn.org/data-platform/covid19/)逐日 PM2.5，使用须遵守其[条款](https://aqicn.org/data-platform/tos/)

## 重新生成

```sh
cd pipeline
mkdir -p raw && curl -s https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv -o raw/isd-history.csv
./fetch_aq.sh                              # 空气质量
python3 fetch_weather.py raw/isd-history.csv  # 选站并下载气象
python3 fetch_sun.py                       # 云量
python3 build.py raw/aq                    # 打包成 data.json
python3 make_page.py                       # 生成 ../index.html
```

增加城市：在 `pipeline/cities.py` 里加一行；如果不在中国、港澳台、美国和加拿大，还要在 `build.py` 的 `TZ` / `TZ_CITY` 里补上时区。
