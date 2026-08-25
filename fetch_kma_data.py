# 기상청(KMA) ASOS 일자료 수집 스크립트 — 서울 여름(6~9월) 기후 데이터
#
# 사용법:
#   1) https://www.data.go.kr 에서 "기상청_지상(종관, ASOS) 일자료 조회서비스" 활용신청 후 인증키 발급
#   2) export KMA_SERVICE_KEY="발급받은키"
#   3) python fetch_kma_data.py                                    # 기본값: 서울(108), 2021~2026
#      python fetch_kma_data.py --station-id 159 --start-year 2019 --end-year 2024 --location-name 부산
#
# 인증키는 코드에 저장하지 않고 환경변수로만 전달합니다.
# 주요 지점코드: 서울 108, 부산 159, 인천 112, 대구 143, 광주 156, 대전 133, 제주 184

import os
import sys
import time
import argparse
import urllib.request
import urllib.parse
import json

import numpy as np
import pandas as pd

BASE_URL = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
HEATWAVE_THRESHOLD = 33.0
TROPICAL_NIGHT_THRESHOLD = 25.0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def parse_args():
    parser = argparse.ArgumentParser(description="기상청 ASOS 일자료 수집 (지점/기간 재사용 가능)")
    parser.add_argument("--station-id", default=os.environ.get("KMA_STATION_ID", "108"))
    parser.add_argument("--start-year", type=int, default=int(os.environ.get("KMA_START_YEAR", 2021)))
    parser.add_argument("--end-year", type=int, default=int(os.environ.get("KMA_END_YEAR", 2026)))
    parser.add_argument("--location-name", default=os.environ.get("KMA_LOCATION_NAME", "서울"))
    return parser.parse_args()


def fetch_range(service_key, station_id, start_dt, end_dt, num_of_rows=130):
    """start_dt, end_dt: 'YYYYMMDD' 형식. 반환: KMA API의 item 리스트."""
    params = {
        "serviceKey": service_key,
        "pageNo": "1",
        "numOfRows": str(num_of_rows),
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "DAY",
        "startDt": start_dt,
        "endDt": end_dt,
        "stnIds": station_id,
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    header = payload["response"]["header"]
    if header["resultCode"] != "00":
        raise RuntimeError(f"KMA API 오류 ({start_dt}~{end_dt}): {header['resultMsg']}")

    body = payload["response"]["body"]
    if body.get("totalCount", 0) == 0:
        return []
    return body["items"]["item"]


def collect_observed(service_key, station_id, start_year, end_year, today_str):
    """start_year~end_year의 6/1~9/30 실측 데이터를 수집한다.
    end_year가 진행 중인 해라면 today_str(YYYYMMDD) 전날까지만 수집한다."""
    records = []
    for year in range(start_year, end_year + 1):
        start_dt = f"{year}0601"
        end_dt = f"{year}0930"
        if year == int(today_str[:4]) and end_dt > today_str:
            yesterday = (pd.Timestamp(today_str) - pd.Timedelta(days=1)).strftime("%Y%m%d")
            end_dt = min(end_dt, yesterday)
        print(f"[수집] {year}년 {start_dt} ~ {end_dt}")
        for item in fetch_range(service_key, station_id, start_dt, end_dt):
            records.append({
                "date": item["tm"],
                "avg_temp": item["avgTa"] if item["avgTa"] != "" else np.nan,
                "max_temp": item["maxTa"] if item["maxTa"] != "" else np.nan,
                "min_temp": item["minTa"] if item["minTa"] != "" else np.nan,
            })
        time.sleep(0.2)

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    for c in ["avg_temp", "max_temp", "min_temp"]:
        df[c] = pd.to_numeric(df[c])
    df = df.sort_values("date").reset_index(drop=True)

    n_missing = int(df[["avg_temp", "max_temp", "min_temp"]].isna().sum().sum())
    if n_missing:
        print(f"[결측치 처리] {n_missing}건 발견 -> 선형보간(interpolate)으로 채움")
        df[["avg_temp", "max_temp", "min_temp"]] = df[["avg_temp", "max_temp", "min_temp"]].interpolate(method="linear")

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["day_of_year"] = df["date"].dt.dayofyear
    df["type"] = "관측치"
    return df


def build_forecast(df_observed, current_year, forecast_start, forecast_end):
    """과거 5개년 평년값(climatology)에 올해 관측 구간의 평년 대비 편차를
    감쇄(decay)시켜 더하는 방식의 baseline 예측 (실제 수치예보 아님)."""
    past = df_observed[df_observed["year"] < current_year]
    clim = past.groupby(["month", "day"])[["avg_temp", "max_temp", "min_temp"]].mean().reset_index()

    curr_obs = df_observed[df_observed["year"] == current_year]
    merged = curr_obs.merge(clim, on=["month", "day"], suffixes=("", "_clim"))
    anomaly = {
        col: (merged[col] - merged[f"{col}_clim"]).mean()
        for col in ["avg_temp", "max_temp", "min_temp"]
    }
    print(f"[예측 모델] {current_year}년 관측 구간의 평년 대비 편차: "
          f"평균 {anomaly['avg_temp']:+.2f}C / 최고 {anomaly['max_temp']:+.2f}C / 최저 {anomaly['min_temp']:+.2f}C")

    fc_dates = pd.date_range(forecast_start, forecast_end, freq="D")
    decay = np.linspace(1.0, 0.2, len(fc_dates))

    fc = pd.DataFrame({"date": fc_dates})
    fc["month"] = fc["date"].dt.month
    fc["day"] = fc["date"].dt.day
    fc = fc.merge(clim, on=["month", "day"], how="left")
    for col in ["avg_temp", "max_temp", "min_temp"]:
        fc[col] = (fc[col] + anomaly[col] * decay).round(1)
    fc["year"] = current_year
    fc["day_of_year"] = fc["date"].dt.dayofyear
    fc["type"] = "예측치"
    return fc[["date", "year", "month", "day", "day_of_year", "avg_temp", "max_temp", "min_temp", "type"]]


def main():
    args = parse_args()

    service_key = os.environ.get("KMA_SERVICE_KEY")
    if not service_key:
        print("오류: 환경변수 KMA_SERVICE_KEY가 설정되어 있지 않습니다.")
        print('  예) export KMA_SERVICE_KEY="발급받은_인증키"')
        sys.exit(1)

    print(f"[설정] 지점: {args.location_name}({args.station_id}) | 기간: {args.start_year}~{args.end_year}년 6~9월")

    today_str = pd.Timestamp.today().strftime("%Y%m%d")
    current_year = args.end_year

    df_observed = collect_observed(service_key, args.station_id, args.start_year, args.end_year, today_str)

    last_observed_date = df_observed[df_observed["year"] == current_year]["date"].max()
    forecast_start = (last_observed_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    forecast_end = f"{last_observed_date.year}-09-30"

    fc = build_forecast(df_observed, current_year=current_year, forecast_start=forecast_start, forecast_end=forecast_end)

    # summer_climate: 실측 6~8월 + 8월에 걸치는 예측분(실측이 8월 말까지 못 미친 경우 대비)
    obs_summer = df_observed[df_observed["month"].isin([6, 7, 8])].copy()
    fc_aug_tail = fc[fc["month"] == 8].copy()
    summer = pd.concat([obs_summer, fc_aug_tail], ignore_index=True).sort_values("date").reset_index(drop=True)
    summer["is_heatwave"] = summer["max_temp"] >= HEATWAVE_THRESHOLD
    summer["is_tropical_night"] = summer["min_temp"] >= TROPICAL_NIGHT_THRESHOLD
    summer = summer[["date", "year", "month", "day", "day_of_year", "avg_temp", "max_temp", "min_temp",
                      "is_heatwave", "is_tropical_night", "type"]]

    sep = fc[fc["month"] == 9].copy()
    sep["is_heatwave"] = sep["max_temp"] >= HEATWAVE_THRESHOLD
    sep["is_tropical_night"] = sep["min_temp"] >= TROPICAL_NIGHT_THRESHOLD
    sep = sep[["date", "year", "month", "day", "day_of_year", "avg_temp", "max_temp", "min_temp",
               "is_heatwave", "is_tropical_night", "type"]]

    sep_hist = df_observed[(df_observed["month"] == 9) & (df_observed["year"] < current_year)].copy()
    sep_hist["is_heatwave"] = sep_hist["max_temp"] >= HEATWAVE_THRESHOLD
    sep_hist["is_tropical_night"] = sep_hist["min_temp"] >= TROPICAL_NIGHT_THRESHOLD
    sep_hist = sep_hist[["date", "year", "month", "day", "day_of_year", "avg_temp", "max_temp", "min_temp",
                          "is_heatwave", "is_tropical_night", "type"]]

    summer_path = os.path.join(DATA_DIR, "summer_climate.csv")
    sep_path = os.path.join(DATA_DIR, "september_forecast.csv")
    sep_hist_path = os.path.join(DATA_DIR, "september_observed_history.csv")
    summer.to_csv(summer_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    sep.to_csv(sep_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    sep_hist.to_csv(sep_hist_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")

    print(f"\n저장 완료: {summer_path} ({len(summer)}행)")
    print(f"저장 완료: {sep_path} ({len(sep)}행)")
    print(f"저장 완료: {sep_hist_path} ({len(sep_hist)}행, 과거 9월 실측치)")


if __name__ == "__main__":
    main()
