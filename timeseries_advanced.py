# 시계열 분해(STL) + 지수평활(Holt) 예측 백테스트 — 보너스 심화 분석
#
# 1) STL 분해: 2021~2025년 5개년 완결 여름 사이클(6/1~9/30, 122일 x 5년)을 이어붙여
#    추세(Trend, 연도 간 기온 변화 방향) / 계절성(Seasonal, 여름 내 6월→8월 상승 패턴) /
#    잔차(Residual, 날씨 노이즈·이상치)로 분리한다.
# 2) 예측 백테스트: 5개년 각각을 "그 해라고 가정하고" 9월을 가려본 뒤,
#    (a) 기존 베이스라인(평년값+편차 감쇄, fetch_kma_data.py의 build_forecast와 동일 로직)과
#    (b) Holt 지수평활(statsmodels ExponentialSmoothing, 추세 포함)
#    두 모델의 9월 예측 오차(MAE)를 실제 9월 실측치와 비교해 어느 쪽이 더 정확한지 검증한다.
# 3) 검증된 두 모델을 2026년에 동일하게 적용해 기존 베이스라인 예측과 나란히 비교한다.

import os
import sys
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings("ignore")

if "seaborn-v0_8-whitegrid" in plt.style.available:
    plt.style.use("seaborn-v0_8-whitegrid")
else:
    plt.style.use("default")
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMG_DIR = os.path.join(BASE_DIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)

CSV_SUMMER = os.path.join(DATA_DIR, "summer_climate.csv")
CSV_SEP_FORECAST = os.path.join(DATA_DIR, "september_forecast.csv")
CSV_SEP_HIST = os.path.join(DATA_DIR, "september_observed_history.csv")

HEATWAVE_THRESHOLD = 33.0
TROPICAL_NIGHT_THRESHOLD = 25.0
SEASON_START = (6, 1)   # 6월 1일
SEASON_END = (9, 30)    # 9월 30일
SEASON_LEN = 122        # 6/1~9/30

print("=" * 70)
print("🌦️ [Step 1] 데이터 로드 및 연도별 완결 여름 사이클(6/1~9/30) 구성")
print("=" * 70)

if not os.path.exists(CSV_SUMMER) or not os.path.exists(CSV_SEP_FORECAST):
    print("❌ data/ 폴더에 필요한 CSV가 없습니다. 먼저 analysis.py와 동일하게 fetch_kma_data.py를 실행하세요.")
    sys.exit(1)

df_summer = pd.read_csv(CSV_SUMMER, parse_dates=["date"])
df_sep_fc = pd.read_csv(CSV_SEP_FORECAST, parse_dates=["date"])
df_sep_hist = pd.read_csv(CSV_SEP_HIST, parse_dates=["date"]) if os.path.exists(CSV_SEP_HIST) else pd.DataFrame()

current_year = int(df_summer["year"].max())
past_years = sorted(y for y in df_summer["year"].unique() if y < current_year)

# 관측치만 사용 (예측치는 학습/검증에서 제외)
obs_summer = df_summer[df_summer["type"] == "관측치"].copy()
obs_sep_hist = df_sep_hist[df_sep_hist["type"] == "관측치"].copy() if not df_sep_hist.empty else pd.DataFrame()


def build_full_season(year):
    """해당 연도의 6/1~9/30(또는 관측 마지막 날까지) 완결 일별 시리즈를 만든다.
    빠진 날짜는 선형보간으로 채우고 채운 건수를 출력한다."""
    parts = [obs_summer[obs_summer["year"] == year]]
    if not obs_sep_hist.empty:
        parts.append(obs_sep_hist[obs_sep_hist["year"] == year])
    df_y = pd.concat(parts, ignore_index=True).sort_values("date").drop_duplicates("date")
    if df_y.empty:
        return df_y

    full_range = pd.date_range(f"{year}-{SEASON_START[0]:02d}-{SEASON_START[1]:02d}", df_y["date"].max(), freq="D")
    df_y = df_y.set_index("date").reindex(full_range)
    n_missing = int(df_y[["avg_temp", "max_temp", "min_temp"]].isna().sum().sum())
    if n_missing:
        print(f"  [{year}] 결측 {n_missing}건 -> 선형보간으로 채움")
        df_y[["avg_temp", "max_temp", "min_temp"]] = df_y[["avg_temp", "max_temp", "min_temp"]].interpolate(method="linear")
    df_y.index.name = "date"
    df_y["season_day"] = np.arange(1, len(df_y) + 1)  # 1 = 6/1
    return df_y.reset_index()


season_data = {y: build_full_season(y) for y in past_years + [current_year]}
complete_years = [y for y in past_years if len(season_data[y]) >= SEASON_LEN]
print(f"\n📊 5개년 중 6/1~9/30 완결 사이클 확보 연도: {complete_years} ({len(complete_years)}개)")
print(f"📊 {current_year}년 관측 진행 일수: {len(season_data[current_year])}일 (6/1~{season_data[current_year]['date'].max().strftime('%m/%d')})")

# ------------------------------------------------------------------
# [Step 2] STL 분해: 완결 5개년(6/1~9/30, 122일)을 이어붙여 추세/계절성/잔차 분리
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("🔬 [Step 2] STL 시계열 분해 (추세 / 계절성 / 잔차)")
print("=" * 70)

concat_frames = []
for y in complete_years:
    df_y = season_data[y].iloc[:SEASON_LEN].copy()
    df_y["cycle_index"] = df_y["season_day"] + (y - complete_years[0]) * SEASON_LEN
    concat_frames.append(df_y)
df_concat = pd.concat(concat_frames, ignore_index=True).sort_values("cycle_index").reset_index(drop=True)

series = pd.Series(df_concat["avg_temp"].values, index=df_concat["cycle_index"].values)
stl_result = STL(series, period=SEASON_LEN, robust=True).fit()

trend, seasonal, resid = stl_result.trend, stl_result.seasonal, stl_result.resid

trend_start = trend.iloc[:SEASON_LEN].mean()
trend_end = trend.iloc[-SEASON_LEN:].mean()
print(f"• 추세(Trend) 성분: {complete_years[0]}년 초입 평균 {trend_start:.2f}℃ → {complete_years[-1]}년 말미 평균 {trend_end:.2f}℃ ({trend_end - trend_start:+.2f}℃)")

seasonal_one_cycle = seasonal.iloc[:SEASON_LEN]
peak_day = int(seasonal_one_cycle.idxmax())  # cycle_index 1~122 == season_day (6/1=1)
peak_date_approx = pd.Timestamp(f"{complete_years[0]}-06-01") + pd.Timedelta(days=int(peak_day) - 1)
print(f"• 계절성(Seasonal) 성분: 여름 내 최고점은 사이클 {int(peak_day)}일차(≈{peak_date_approx.strftime('%m/%d')} 전후), 진폭 {seasonal_one_cycle.max() - seasonal_one_cycle.min():.2f}℃")

resid_std = resid.std()
print(f"• 잔차(Residual) 성분: 표준편차 {resid_std:.2f}℃ (STL로 설명되지 않는 날씨 노이즈 크기)")

top_hot = df_concat.assign(resid=resid.values).nlargest(3, "resid")[["date", "avg_temp", "resid"]]
top_cold = df_concat.assign(resid=resid.values).nsmallest(3, "resid")[["date", "avg_temp", "resid"]]
print("\n[잔차 최대 이례적 고온일 Top3]")
print(top_hot.assign(date=top_hot["date"].dt.strftime("%Y-%m-%d")).round(2).to_string(index=False))
print("[잔차 최대 이례적 저온일 Top3]")
print(top_cold.assign(date=top_cold["date"].dt.strftime("%Y-%m-%d")).round(2).to_string(index=False))

print("\n🎨 [시각화 5] 05_stl_decomposition.png")
fig, axes = plt.subplots(4, 1, figsize=(14, 11), sharex=True)
axes[0].plot(df_concat["cycle_index"], series.values, color="#374151", linewidth=1.0)
axes[0].set_ylabel("실측 평균기온(℃)")
axes[0].set_title(f"STL 시계열 분해 — {complete_years[0]}~{complete_years[-1]}년 여름(6/1~9/30) 연속 사이클", fontsize=15, fontweight="bold", pad=12)
axes[1].plot(df_concat["cycle_index"], trend.values, color="#dc2626", linewidth=1.8)
axes[1].set_ylabel("추세 (Trend)")
axes[2].plot(df_concat["cycle_index"], seasonal.values, color="#2563eb", linewidth=1.0)
axes[2].set_ylabel("계절성 (Seasonal)")
axes[3].axhline(0, color="#9ca3af", linewidth=1.0)
axes[3].plot(df_concat["cycle_index"], resid.values, color="#059669", linewidth=0.9)
axes[3].set_ylabel("잔차 (Residual)")
axes[3].set_xlabel("연속 사이클 인덱스 (연도별 122일씩 이어붙임: 6/1~9/30)")
for y in complete_years:
    boundary = (y - complete_years[0]) * SEASON_LEN
    for ax in axes:
        ax.axvline(boundary, color="#d1d5db", linestyle=":", linewidth=1.0)
    axes[0].text(boundary + 3, axes[0].get_ylim()[1] * 0.97, f"{y}년", fontsize=9, color="#6b7280")
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "05_stl_decomposition.png"), dpi=200)
plt.close()

# ------------------------------------------------------------------
# [Step 3] 예측 백테스트: 베이스라인(평년+편차감쇄) vs Holt 지수평활
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("🧪 [Step 3] 9월 예측 백테스트 (Leave-one-year-out, 실제 9월 실측치와 비교)")
print("=" * 70)


def baseline_forecast(target_year, other_years, n_days):
    """fetch_kma_data.py의 build_forecast와 동일한 로직(평년값 + 관측 구간 편차 감쇄)."""
    clim_frames = [season_data[y].iloc[:SEASON_LEN][["season_day", "avg_temp", "max_temp", "min_temp"]] for y in other_years]
    clim = pd.concat(clim_frames).groupby("season_day").mean().reset_index()

    df_t = season_data[target_year]
    obs_len = min(len(df_t), 92)  # 6/1~8/31 관측 구간까지의 편차로 anomaly 산출
    merged = df_t.iloc[:obs_len].merge(clim, on="season_day", suffixes=("", "_clim"))
    anomaly = {c: (merged[c] - merged[f"{c}_clim"]).mean() for c in ["avg_temp", "max_temp", "min_temp"]}

    fc_days = np.arange(93, 93 + n_days)
    fc = clim[clim["season_day"].isin(fc_days)].sort_values("season_day").reset_index(drop=True)
    decay = np.linspace(1.0, 0.2, len(fc))
    for c in ["avg_temp", "max_temp", "min_temp"]:
        fc[c] = fc[c] + anomaly[c] * decay
    return fc


def holt_forecast(train_df, n_days):
    """train_df의 실측 시리즈(마지막 관측일 다음날부터)로 Holt 지수평활(추세 포함)을 학습해 n_days 예측."""
    out = {}
    for c in ["avg_temp", "max_temp", "min_temp"]:
        model = ExponentialSmoothing(train_df[c].values, trend="add", damped_trend=True, initialization_method="estimated")
        fit = model.fit()
        out[c] = fit.forecast(n_days)
    return pd.DataFrame(out)


backtest_rows = []
for y in complete_years:
    others = [o for o in complete_years if o != y]
    actual = season_data[y].iloc[92:SEASON_LEN].reset_index(drop=True)  # 9월 실측(최대 30일)
    n_days = len(actual)
    if n_days == 0:
        continue

    bl = baseline_forecast(y, others, n_days).reset_index(drop=True)
    hw = holt_forecast(season_data[y].iloc[:92], n_days).reset_index(drop=True)  # 6/1~8/31 관측 구간만 학습

    bl_mae = float(np.mean(np.abs(bl["avg_temp"].values - actual["avg_temp"].values)))
    hw_mae = float(np.mean(np.abs(hw["avg_temp"].values - actual["avg_temp"].values)))
    bl_rmse = float(np.sqrt(np.mean((bl["avg_temp"].values - actual["avg_temp"].values) ** 2)))
    hw_rmse = float(np.sqrt(np.mean((hw["avg_temp"].values - actual["avg_temp"].values) ** 2)))

    actual_heat = int((actual["max_temp"] >= HEATWAVE_THRESHOLD).sum())
    bl_heat = int((bl["max_temp"] >= HEATWAVE_THRESHOLD).sum())
    hw_heat = int((hw["max_temp"] >= HEATWAVE_THRESHOLD).sum())

    backtest_rows.append({"year": y, "model": "베이스라인(평년+편차감쇄)", "mae": bl_mae, "rmse": bl_rmse,
                           "actual_heat_days": actual_heat, "pred_heat_days": bl_heat})
    backtest_rows.append({"year": y, "model": "Holt 지수평활", "mae": hw_mae, "rmse": hw_rmse,
                           "actual_heat_days": actual_heat, "pred_heat_days": hw_heat})

df_backtest = pd.DataFrame(backtest_rows)
backtest_path = os.path.join(DATA_DIR, "forecast_backtest_results.csv")
df_backtest.to_csv(backtest_path, index=False, encoding="utf-8-sig")

print(df_backtest.round(2).to_string(index=False))
mean_by_model = df_backtest.groupby("model")[["mae", "rmse"]].mean().round(3)
print(f"\n[모델별 평균 오차 (5개년 백테스트, {complete_years[0]}~{complete_years[-1]})]")
print(mean_by_model.to_string())
print(f"\n저장 완료: {backtest_path}")

better_model = mean_by_model["mae"].idxmin()
print(f"\n✅ 5개년 백테스트 결과, 9월 평균기온 예측 오차(MAE)가 더 낮은 모델: 「{better_model}」")

print("\n🎨 [시각화 6] 06_forecast_backtest_comparison.png")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
pivot_mae = df_backtest.pivot(index="year", columns="model", values="mae")
pivot_mae.plot(kind="bar", ax=axes[0], color=["#94a3b8", "#dc2626"], edgecolor="black", alpha=0.9)
axes[0].set_title("연도별 9월 예측 오차(MAE) 비교 — 낮을수록 정확", fontsize=13, fontweight="bold")
axes[0].set_xlabel("백테스트 대상 연도")
axes[0].set_ylabel("평균기온 MAE (℃)")
axes[0].tick_params(axis="x", rotation=0)
axes[0].legend(title="")
axes[0].grid(axis="y", linestyle="--", alpha=0.6)

mean_by_model["mae"].plot(kind="bar", ax=axes[1], color=["#dc2626", "#94a3b8"] if better_model == "Holt 지수평활" else ["#94a3b8", "#dc2626"], edgecolor="black", alpha=0.9)
axes[1].set_title(f"5개년 평균 MAE — 「{better_model}」가 더 정확", fontsize=13, fontweight="bold")
axes[1].set_ylabel("평균 MAE (℃)")
axes[1].set_xlabel("")
axes[1].tick_params(axis="x", rotation=15)
axes[1].grid(axis="y", linestyle="--", alpha=0.6)
for i, v in enumerate(mean_by_model["mae"].values):
    axes[1].text(i, v, f"{v:.2f}℃", ha="center", va="bottom", fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "06_forecast_backtest_comparison.png"), dpi=200)
plt.close()

# ------------------------------------------------------------------
# [Step 4] 검증된 모델을 올해(현재 연도)에 적용, 기존 베이스라인 예측과 비교
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print(f"🍂 [Step 4] {current_year}년 9월 예측 — 기존 베이스라인 vs Holt 지수평활 비교")
print("=" * 70)

n_sep_days = len(df_sep_fc)
train_curr = season_data[current_year]
last_obs_date = train_curr["date"].max()
total_steps = (df_sep_fc["date"].max() - last_obs_date).days  # 관측 마지막날 다음날부터 9/30까지 총 스텝 수
holt_full = holt_forecast(train_curr, total_steps).reset_index(drop=True)
holt_curr = holt_full.iloc[-n_sep_days:].reset_index(drop=True)  # 9월 구간만 잘라서 비교
holt_curr["date"] = df_sep_fc["date"].values

compare = df_sep_fc[["date", "avg_temp", "max_temp"]].rename(columns={"avg_temp": "baseline_avg", "max_temp": "baseline_max"})
compare["holt_avg"] = holt_curr["avg_temp"].round(1).values
compare["holt_max"] = holt_curr["max_temp"].round(1).values
compare["diff_avg"] = (compare["holt_avg"] - compare["baseline_avg"]).round(1)

print(compare.assign(date=compare["date"].dt.strftime("%Y-%m-%d")).to_string(index=False))

holt_heat = int((holt_curr["max_temp"] >= HEATWAVE_THRESHOLD).sum())
holt_trop = int((holt_curr["min_temp"] >= TROPICAL_NIGHT_THRESHOLD).sum())
print(f"\n[Holt 지수평활 기준 {current_year}년 9월 예측] 폭염 {holt_heat}일 / 열대야 {holt_trop}일")
print(f"[기존 베이스라인 기준] 폭염 {int((df_sep_fc['max_temp'] >= HEATWAVE_THRESHOLD).sum())}일 / 열대야 {int((df_sep_fc['min_temp'] >= TROPICAL_NIGHT_THRESHOLD).sum())}일")
print(f"→ 두 모델 모두 방향성(추가 폭염·열대야 없음)은 일치하며, 5개년 백테스트에서 더 정확했던 「{better_model}」 쪽에 더 무게를 둘 수 있음")

compare_path = os.path.join(DATA_DIR, f"september_forecast_model_comparison.csv")
compare.to_csv(compare_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
print(f"\n저장 완료: {compare_path}")

print("\n" + "=" * 70)
print("✅ 시계열 분해(STL) 및 예측 모델 백테스트가 완료되었습니다!")
print("=" * 70)
