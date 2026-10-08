#!/bin/sh
# 下载 aqicn 开放数据平台的逐日空气质量数据（2020-2024），只保留 PM2.5 行
cd "$(dirname "$0")" && mkdir -p raw/aq
for y in 2020 2021 2022 2023 2024; do for q in 1 2 3 4; do
  curl -s -A "Mozilla/5.0" "https://aqicn.org/data-platform/covid19/report/39374-7694ec07/${y}Q$q" | grep ',pm25,' > raw/aq/$y$q.csv
done; done
