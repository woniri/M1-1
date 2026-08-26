# 서울 여름(6~9월) 기후 비교 분석 및 9월 늦더위 전이 예측 스크립트
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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

print("=" * 70)
print("🌦️ [Step 1] 데이터 로드")
print("=" * 70)

if not os.path.exists(CSV_SUMMER) or not os.path.exists(CSV_SEP_FORECAST):
    print("❌ data/ 폴더에 필요한 CSV가 없습니다. 먼저 아래를 실행하세요:")
    print('   export KMA_SERVICE_KEY="발급받은_인증키" && python fetch_kma_data.py')
    sys.exit(1)

df_summer = pd.read_csv(CSV_SUMMER, parse_dates=["date"])
df_sep = pd.read_csv(CSV_SEP_FORECAST, parse_dates=["date"])
df_sep_hist = pd.read_csv(CSV_SEP_HIST, parse_dates=["date"]) if os.path.exists(CSV_SEP_HIST) else pd.DataFrame()

current_year = int(df_summer["year"].max())
past_years = sorted(y for y in df_summer["year"].unique() if y < current_year)

print(f"📊 여름철(6~8월) 레코드 수: {len(df_summer)}개 (연도: {past_years} + {current_year})")
print(f"📊 {current_year}년 9월 예측 레코드 수: {len(df_sep)}개")

print("\n" + "=" * 70)
print("📈 [Step 2] 연도별 통계 집계 및 비교")
print("=" * 70)

summary = df_summer.groupby("year").agg(
    avg_temp=("avg_temp", "mean"),
    heatwave_days=("is_heatwave", "sum"),
    tropical_nights=("is_tropical_night", "sum"),
).reset_index()
print(summary.round(2).to_string(index=False))

past = summary[summary["year"] < current_year]
curr = summary[summary["year"] == current_year].iloc[0]

past_avg_temp = past["avg_temp"].mean()
past_heat = past["heatwave_days"].mean()
past_trop = past["tropical_nights"].mean()

print(f"\n🔥 [{current_year}년 vs 과거 {len(past)}개년 평균]")
print(f"• 평균기온: {curr['avg_temp']:.2f}℃ vs {past_avg_temp:.2f}℃ (편차 {curr['avg_temp'] - past_avg_temp:+.2f}℃)")
print(f"• 폭염일수: {int(curr['heatwave_days'])}일 vs {past_heat:.1f}일 (증감 {curr['heatwave_days'] - past_heat:+.1f}일)")
print(f"• 열대야일수: {int(curr['tropical_nights'])}일 vs {past_trop:.1f}일 (증감 {curr['tropical_nights'] - past_trop:+.1f}일)")

sep_heat = int(df_sep["is_heatwave"].sum())
sep_trop = int(df_sep["is_tropical_night"].sum())
sep_first_half = df_sep.sort_values("date").head(len(df_sep) // 2)
sep_second_half = df_sep.sort_values("date").tail(len(df_sep) - len(df_sep) // 2)
print(f"\n🍂 [9월 늦더위 전이 예측] 폭염 {sep_heat}일 / 열대야 {sep_trop}일 예측")
print(f"• 9월 상순 평균 최고기온 예측: {sep_first_half['max_temp'].mean():.1f}℃")
print(f"• 9월 하순 평균 최고기온 예측: {sep_second_half['max_temp'].mean():.1f}℃")

# ------------------------------------------------------------------
# 시각화 1: 연도별 폭염/열대야 일수 비교 막대그래프
# ------------------------------------------------------------------
print("\n🎨 [시각화 1] 01_extreme_weather_by_year.png")
fig, ax = plt.subplots(figsize=(11, 6))
x = np.arange(len(summary))
width = 0.35
rects1 = ax.bar(x - width / 2, summary["heatwave_days"], width, label="폭염 일수 (최고기온 ≥33℃)", color="#ef4444", alpha=0.88, edgecolor="#b91c1c")
rects2 = ax.bar(x + width / 2, summary["tropical_nights"], width, label="열대야 일수 (최저기온 ≥25℃)", color="#3b82f6", alpha=0.88, edgecolor="#1d4ed8")
rects1[-1].set_linewidth(2.0)
rects2[-1].set_linewidth(2.0)
ax.set_title(f"연도별 여름(6~8월) 폭염·열대야 일수 비교 ({past_years[0]}~{current_year})", fontsize=15, fontweight="bold", pad=15)
ax.set_xlabel("연도")
ax.set_ylabel("발생 일수 (일)")
ax.set_xticks(x)
ax.set_xticklabels([f"{y}년" if y != current_year else f"★ {y}년(올해)" for y in summary["year"]], fontweight="bold")
ax.legend()
ax.grid(axis="y", linestyle="--", alpha=0.6)
for rect in rects1:
    ax.annotate(f"{int(rect.get_height())}일", xy=(rect.get_x() + rect.get_width() / 2, rect.get_height()), xytext=(0, 4), textcoords="offset points", ha="center", fontweight="bold", color="#991b1b")
for rect in rects2:
    ax.annotate(f"{int(rect.get_height())}일", xy=(rect.get_x() + rect.get_width() / 2, rect.get_height()), xytext=(0, 4), textcoords="offset points", ha="center", fontweight="bold", color="#1e40af")
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "01_extreme_weather_by_year.png"), dpi=200)
plt.close()

# ------------------------------------------------------------------
# 시각화 2: 올해 실측 기온 타임라인 + 9월 예측
# ------------------------------------------------------------------
print("🎨 [시각화 2] 02_timeline_and_forecast.png")
fig, ax = plt.subplots(figsize=(14, 7))
df_curr_summer = df_summer[df_summer["year"] == current_year]
df_curr_obs = df_curr_summer[df_curr_summer["type"] == "관측치"]
df_curr_fc_tail = df_curr_summer[df_curr_summer["type"] == "예측치"]

ax.plot(df_curr_obs["date"], df_curr_obs["max_temp"], color="#ef4444", linewidth=2.0, label="실측 최고기온")
ax.plot(df_curr_obs["date"], df_curr_obs["avg_temp"], color="#f59e0b", linewidth=1.8, label="실측 평균기온")
ax.plot(df_curr_obs["date"], df_curr_obs["min_temp"], color="#3b82f6", linewidth=1.5, label="실측 최저기온")

df_fc_all = pd.concat([df_curr_fc_tail, df_sep]).sort_values("date")
ax.plot(df_fc_all["date"], df_fc_all["max_temp"], color="#dc2626", linestyle="--", linewidth=2.0, label="예측 최고기온")
ax.plot(df_fc_all["date"], df_fc_all["avg_temp"], color="#d97706", linestyle="--", linewidth=1.8, label="예측 평균기온")
ax.plot(df_fc_all["date"], df_fc_all["min_temp"], color="#2563eb", linestyle="--", linewidth=1.5, label="예측 최저기온")

ax.axhline(33.0, color="#dc2626", linestyle=":", linewidth=1.5, label="폭염 기준선 (33℃)")
ax.axhline(25.0, color="#2563eb", linestyle=":", linewidth=1.5, label="열대야 기준선 (25℃)")

if not df_fc_all.empty:
    fc_start, fc_end = df_fc_all["date"].min(), df_fc_all["date"].max()
    ax.axvspan(fc_start, fc_end, color="#fef3c7", alpha=0.35, label=f"예측 구간 ({fc_start.strftime('%m/%d')}~{fc_end.strftime('%m/%d')})")

ax.set_title(f"{current_year}년 여름 실측 기온 및 늦더위 전이 예측 타임라인 (6월~9월)", fontsize=15, fontweight="bold", pad=15)
ax.set_xlabel("날짜")
ax.set_ylabel("기온 (℃)")
ax.legend(loc="lower left", ncol=3, fontsize=9.5)
ax.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "02_timeline_and_forecast.png"), dpi=200)
plt.close()

# ------------------------------------------------------------------
# 시각화 3: 월별 평년 대비 기온 편차 히트맵
# ------------------------------------------------------------------
print("🎨 [시각화 3] 03_monthly_anomaly_heatmap.png")
monthly_avg = df_summer.groupby(["year", "month"])["avg_temp"].mean().unstack()
monthly_avg.loc[current_year, 9] = df_sep["avg_temp"].mean()
if not df_sep_hist.empty:
    for y, val in df_sep_hist.groupby("year")["avg_temp"].mean().items():
        monthly_avg.loc[y, 9] = val

climatology = monthly_avg.loc[past_years].mean()
anomaly_matrix = monthly_avg.sub(climatology, axis=1).sort_index()

fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(anomaly_matrix, annot=True, fmt="+.2f", cmap="coolwarm", center=0,
            cbar_kws={"label": "평년 대비 기온 편차 (℃)"}, linewidths=1.2, linecolor="white",
            annot_kws={"size": 12, "weight": "bold"}, ax=ax)
ax.set_title(f"월별(6~9월) 평년 대비 평균기온 편차 히트맵 ({past_years[0]}~{current_year})", fontsize=14, fontweight="bold", pad=15)
ax.set_xlabel("월")
ax.set_ylabel("연도")
ax.set_xticklabels(["6월", "7월", "8월", "9월(예측포함)"])
ax.set_yticklabels([f"{y}년" for y in anomaly_matrix.index], rotation=0)
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "03_monthly_anomaly_heatmap.png"), dpi=200)
plt.close()

# ------------------------------------------------------------------
# 시각화 4: 연도별 누적 폭염일수 페이스 비교
# ------------------------------------------------------------------
print("🎨 [시각화 4] 04_cumulative_heatwave_pace.png")
fig, ax = plt.subplots(figsize=(12, 6.5))
all_years = past_years + [current_year]
cmap = plt.get_cmap("YlOrRd")
colors = {y: cmap(0.35 + 0.5 * i / max(len(past_years) - 1, 1)) for i, y in enumerate(past_years)}
colors[current_year] = "#7f1d1d"

for year in all_years:
    df_y = df_summer[df_summer["year"] == year].sort_values("day_of_year").copy()
    df_y["cum_heat"] = df_y["is_heatwave"].cumsum()
    days = np.arange(1, len(df_y) + 1)
    if year == current_year:
        df_sep_sorted = df_sep.sort_values("day_of_year")
        sep_cum = df_y["cum_heat"].iloc[-1] + df_sep_sorted["is_heatwave"].cumsum()
        ax.plot(days, df_y["cum_heat"], color=colors[year], linewidth=3.0, label=f"{year}년 여름 (총 {int(df_y['cum_heat'].iloc[-1])}일)", zorder=10)
        sep_days = np.arange(len(df_y) + 1, len(df_y) + len(df_sep) + 1)
        ax.plot(sep_days, sep_cum, color=colors[year], linestyle="--", linewidth=2.5, label=f"{year}년 9월 예측 연장 (최종 {int(sep_cum.iloc[-1])}일)", zorder=9)
    else:
        ax.plot(days, df_y["cum_heat"], color=colors[year], linewidth=1.6, alpha=0.85, label=f"{year}년 (총 {int(df_y['cum_heat'].iloc[-1])}일)")

ax.set_title("연도별 여름 시즌 누적 폭염일수 페이스 비교 (6월 1일~9월 30일)", fontsize=15, fontweight="bold", pad=15)
ax.set_xlabel("여름 경과 일수 (1일=6/1, 31일=7/1, 62일=8/1, 93일=9/1)")
ax.set_ylabel("누적 폭염 일수 (일)")
ax.axvline(92, color="#6b7280", linestyle=":", label="여름 종료선 (8/31)")
ax.legend(loc="upper left", fontsize=9.5)
ax.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "04_cumulative_heatwave_pace.png"), dpi=200)
plt.close()

# ------------------------------------------------------------------
# 분석: 이동평균(Moving Average) & 변화율(Rate of Change)
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("📉 [Step 3] 이동평균 & 변화율 분석")
print("=" * 70)

df_curr_obs = df_summer[(df_summer["year"] == current_year) & (df_summer["type"] == "관측치")].sort_values("date").reset_index(drop=True)
df_curr_obs["ma7"] = df_curr_obs["avg_temp"].rolling(window=7, min_periods=1, center=True).mean()
df_curr_obs["change_rate_pct"] = df_curr_obs["max_temp"].pct_change() * 100

print("[이동평균] 7일 이동평균을 평균기온에 적용 — 하루하루의 날씨 노이즈를 눌러서 그 밑에 깔린 "
      "'며칠 단위로 지속되는 흐름'(더워지는 중인지 식는 중인지)을 드러내기 위함")
print("[변화율] 전일 대비 최고기온 변화율(%)을 계산 — 완만한 변화와 급격한 승온/냉각 시점을 구분하기 위함")

biggest_rise = df_curr_obs.loc[df_curr_obs["change_rate_pct"].idxmax()]
biggest_drop = df_curr_obs.loc[df_curr_obs["change_rate_pct"].idxmin()]
print(f"• 가장 급격한 승온일: {biggest_rise['date'].strftime('%Y-%m-%d')} (전일 대비 {biggest_rise['change_rate_pct']:+.1f}%, "
      f"{biggest_rise['max_temp']:.1f}℃)")
print(f"• 가장 급격한 냉각일: {biggest_drop['date'].strftime('%Y-%m-%d')} (전일 대비 {biggest_drop['change_rate_pct']:+.1f}%, "
      f"{biggest_drop['max_temp']:.1f}℃)")

print("\n🎨 [시각화 5] 05_moving_average_change_rate.png")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), sharex=True)

ax1.plot(df_curr_obs["date"], df_curr_obs["avg_temp"], color="#cbd5e1", linewidth=1.2, label="일별 평균기온(실측)")
ax1.plot(df_curr_obs["date"], df_curr_obs["ma7"], color="#059669", linewidth=2.5, label="7일 이동평균")
ax1.set_title(f"{current_year}년 일별 평균기온 vs 7일 이동평균", fontsize=14, fontweight="bold", pad=12)
ax1.set_ylabel("평균기온(℃)")
ax1.legend(loc="upper left")
ax1.grid(True, linestyle="--", alpha=0.6)

colors_rate = ["#ef4444" if v >= 0 else "#3b82f6" for v in df_curr_obs["change_rate_pct"].fillna(0)]
ax2.bar(df_curr_obs["date"], df_curr_obs["change_rate_pct"], color=colors_rate, width=0.8)
ax2.axhline(0, color="#6b7280", linewidth=1)
ax2.set_title("전일 대비 최고기온 변화율(%) — 급격한 승온(빨강)·냉각(파랑) 시점", fontsize=14, fontweight="bold", pad=12)
ax2.set_xlabel("날짜")
ax2.set_ylabel("변화율 (%)")
ax2.grid(True, linestyle="--", alpha=0.6)

plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "05_moving_average_change_rate.png"), dpi=200)
plt.close()

print("\n" + "=" * 70)
print("✅ 모든 분석 및 시각화가 완료되었습니다!")
print("=" * 70)
