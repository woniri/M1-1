# 서울 여름 기후 분석 — 인터랙티브 대시보드 (보너스 심화 2/2)
# ./run.sh dashboard 로 실행 후 http://localhost:8501 접속

import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMG_DIR = os.path.join(BASE_DIR, "images")

HEATWAVE_THRESHOLD = 33.0
TROPICAL_NIGHT_THRESHOLD = 25.0

st.set_page_config(page_title="서울 여름 기후 분석 대시보드", page_icon="🌦️", layout="wide")


@st.cache_data
def load_data():
    df_summer = pd.read_csv(os.path.join(DATA_DIR, "summer_climate.csv"), parse_dates=["date"])
    df_sep_fc = pd.read_csv(os.path.join(DATA_DIR, "september_forecast.csv"), parse_dates=["date"])
    sep_hist_path = os.path.join(DATA_DIR, "september_observed_history.csv")
    df_sep_hist = pd.read_csv(sep_hist_path, parse_dates=["date"]) if os.path.exists(sep_hist_path) else pd.DataFrame()
    backtest_path = os.path.join(DATA_DIR, "forecast_backtest_results.csv")
    df_backtest = pd.read_csv(backtest_path) if os.path.exists(backtest_path) else pd.DataFrame()
    compare_path = os.path.join(DATA_DIR, "september_forecast_model_comparison.csv")
    df_compare = pd.read_csv(compare_path, parse_dates=["date"]) if os.path.exists(compare_path) else pd.DataFrame()
    return df_summer, df_sep_fc, df_sep_hist, df_backtest, df_compare


df_summer, df_sep_fc, df_sep_hist, df_backtest, df_compare = load_data()

current_year = int(df_summer["year"].max())
past_years = sorted(y for y in df_summer["year"].unique() if y < current_year)
all_years = past_years + [current_year]

summary = df_summer.groupby("year").agg(
    avg_temp=("avg_temp", "mean"),
    heatwave_days=("is_heatwave", "sum"),
    tropical_nights=("is_tropical_night", "sum"),
).reset_index()

# ------------------------------------------------------------------
# 헤더
# ------------------------------------------------------------------
st.title("🌦️ 서울 여름 기후 분석 & 9월 늦더위 전이 예측")
st.caption(
    f"분석 대상: 서울특별시(기상청 ASOS 108) · 관측 {past_years[0]}\\~{current_year}년 6\\~8월 · "
    f"예측 {current_year}년 9월 · 데이터 출처: [공공데이터포털](https://www.data.go.kr) 기상청_지상(종관, ASOS) 일자료 조회서비스"
)

# ------------------------------------------------------------------
# 사이드바 — 연도 선택
# ------------------------------------------------------------------
st.sidebar.header("🔧 필터")
selected_years = st.sidebar.multiselect("타임라인에 표시할 연도", all_years, default=[current_year] + past_years[-2:])
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**산출물**\n"
    "- `docs/REPORT.md` 최종 리포트\n"
    "- `docs/ANALYSIS_EXPLANATION.md` 방법론 해설\n"
    "- `docs/LEARNING_GUIDE.md` 학습서\n"
)
st.sidebar.markdown("이 대시보드는 `data/*.csv`를 읽기만 하며, 재계산이 필요하면 `./run.sh analyze` / `./run.sh timeseries`를 다시 실행하세요.")

# ------------------------------------------------------------------
# KPI 카드 — 올해 vs 과거 평균
# ------------------------------------------------------------------
past = summary[summary["year"] < current_year]
curr = summary[summary["year"] == current_year].iloc[0]
past_avg_temp = past["avg_temp"].mean()
past_heat = past["heatwave_days"].mean()
past_trop = past["tropical_nights"].mean()

col1, col2, col3 = st.columns(3)
col1.metric(f"{current_year}년 평균기온", f"{curr['avg_temp']:.2f}℃", f"{curr['avg_temp'] - past_avg_temp:+.2f}℃ (과거 {len(past)}개년 평균 대비)")
col2.metric(f"{current_year}년 폭염일수", f"{int(curr['heatwave_days'])}일", f"{curr['heatwave_days'] - past_heat:+.1f}일 (과거 평균 {past_heat:.1f}일)", delta_color="inverse")
col3.metric(f"{current_year}년 열대야일수", f"{int(curr['tropical_nights'])}일", f"{curr['tropical_nights'] - past_trop:+.1f}일 (과거 평균 {past_trop:.1f}일)", delta_color="inverse")

st.markdown("---")

# ------------------------------------------------------------------
# 탭 구성
# ------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📈 인터랙티브 타임라인", "📊 연도별 정적 차트", "🔬 STL 분해 & 예측 백테스트", "🗂️ 데이터 탐색"])

with tab1:
    st.subheader("연도 선택형 기온 타임라인 (마우스 오버로 값 확인, 범례 클릭으로 켜고 끄기)")
    if not selected_years:
        st.info("사이드바에서 표시할 연도를 하나 이상 선택하세요.")
    else:
        fig = go.Figure()
        cmap = {y: c for y, c in zip(all_years, ["#94a3b8", "#60a5fa", "#34d399", "#fbbf24", "#f97316", "#dc2626", "#7f1d1d"])}
        for y in sorted(selected_years):
            df_y = df_summer[(df_summer["year"] == y) & (df_summer["type"] == "관측치")].sort_values("date")
            fig.add_trace(go.Scatter(
                x=df_y["day_of_year"] - df_y["day_of_year"].min(), y=df_y["max_temp"],
                name=f"{y}년 최고기온", mode="lines",
                line=dict(color=cmap.get(y, "#333"), width=2.5 if y == current_year else 1.4),
            ))
        fig.add_hline(y=HEATWAVE_THRESHOLD, line_dash="dot", line_color="#dc2626", annotation_text="폭염 기준 33℃")
        fig.update_layout(
            xaxis_title="여름 경과 일수 (0 = 6월 1일)", yaxis_title="최고기온(℃)",
            height=480, hovermode="x unified", legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader(f"{current_year}년 실측 + 9월 예측 (베이스라인)")
        fig2 = go.Figure()
        df_curr_obs = df_summer[(df_summer["year"] == current_year) & (df_summer["type"] == "관측치")]
        df_curr_fc = pd.concat([df_summer[(df_summer["year"] == current_year) & (df_summer["type"] == "예측치")], df_sep_fc]).sort_values("date")
        fig2.add_trace(go.Scatter(x=df_curr_obs["date"], y=df_curr_obs["max_temp"], name="실측 최고기온", line=dict(color="#dc2626", width=2)))
        fig2.add_trace(go.Scatter(x=df_curr_obs["date"], y=df_curr_obs["min_temp"], name="실측 최저기온", line=dict(color="#2563eb", width=2)))
        fig2.add_trace(go.Scatter(x=df_curr_fc["date"], y=df_curr_fc["max_temp"], name="예측 최고기온(베이스라인)", line=dict(color="#dc2626", width=2, dash="dash")))
        fig2.add_trace(go.Scatter(x=df_curr_fc["date"], y=df_curr_fc["min_temp"], name="예측 최저기온(베이스라인)", line=dict(color="#2563eb", width=2, dash="dash")))
        if not df_compare.empty:
            fig2.add_trace(go.Scatter(x=df_compare["date"], y=df_compare["holt_max"], name="예측 최고기온(Holt, 참고용)", line=dict(color="#a855f7", width=1.6, dash="dot")))
        fig2.add_hline(y=HEATWAVE_THRESHOLD, line_dash="dot", line_color="#dc2626")
        fig2.add_hline(y=TROPICAL_NIGHT_THRESHOLD, line_dash="dot", line_color="#2563eb")
        fig2.update_layout(xaxis_title="날짜", yaxis_title="기온(℃)", height=480, hovermode="x unified", legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Holt 모델은 5개년 백테스트에서 베이스라인보다 부정확했던 참고용 비교선입니다 (🔬 탭 참고).")

with tab2:
    st.subheader("analysis.py가 생성한 4대 정적 차트")
    img_col1, img_col2 = st.columns(2)
    captions = {
        "01_extreme_weather_by_year.png": "연도별 폭염·열대야 일수 비교",
        "02_timeline_and_forecast.png": f"{current_year}년 실측 타임라인 + 9월 예측",
        "03_monthly_anomaly_heatmap.png": "월별 평년 대비 기온 편차 히트맵",
        "04_cumulative_heatwave_pace.png": "연도별 누적 폭염일수 페이스",
    }
    for i, (fname, caption) in enumerate(captions.items()):
        path = os.path.join(IMG_DIR, fname)
        col = img_col1 if i % 2 == 0 else img_col2
        if os.path.exists(path):
            col.image(path, caption=caption, use_container_width=True)
        else:
            col.warning(f"{fname} 이(가) 없습니다 — ./run.sh analyze 를 먼저 실행하세요.")

with tab3:
    st.subheader("(보너스) STL 시계열 분해 및 예측 모델 백테스트")
    st.markdown(
        "5개년(2021\\~2025) 여름 사이클을 이어붙여 **추세/계절성/잔차**로 분해하고, "
        "기존 베이스라인(평년+편차감쇄) 예측 모델을 통계적으로 더 정교한 **Holt 지수평활** 모델과 "
        "5개년 leave-one-year-out 백테스트로 정면 비교했습니다."
    )
    stl_path = os.path.join(IMG_DIR, "05_stl_decomposition.png")
    if os.path.exists(stl_path):
        st.image(stl_path, caption="STL 시계열 분해 — 실측 / 추세 / 계절성 / 잔차", use_container_width=True)
    else:
        st.warning("05_stl_decomposition.png 이(가) 없습니다 — ./run.sh timeseries 를 먼저 실행하세요.")

    bt_col1, bt_col2 = st.columns([1, 1])
    with bt_col1:
        backtest_path = os.path.join(IMG_DIR, "06_forecast_backtest_comparison.png")
        if os.path.exists(backtest_path):
            st.image(backtest_path, caption="연도별·모델별 9월 예측 오차(MAE) 비교", use_container_width=True)
    with bt_col2:
        if not df_backtest.empty:
            st.markdown("**5개년 백테스트 원본 결과**")
            st.dataframe(df_backtest.round(2), use_container_width=True, hide_index=True)
            mean_by_model = df_backtest.groupby("model")[["mae", "rmse"]].mean().round(3)
            better_model = mean_by_model["mae"].idxmin()
            st.success(f"5개년 평균 MAE 기준 더 정확한 모델: **{better_model}** ({mean_by_model.loc[better_model, 'mae']:.2f}℃)")
        else:
            st.warning("백테스트 결과 CSV가 없습니다 — ./run.sh timeseries 를 먼저 실행하세요.")

with tab4:
    st.subheader("원본 데이터 탐색")
    dataset_name = st.selectbox("데이터셋 선택", ["여름 관측/예측 (summer_climate)", "9월 예측 (september_forecast)", "9월 과거 실측 (september_observed_history)"])
    if dataset_name.startswith("여름"):
        st.dataframe(df_summer, use_container_width=True, height=420)
    elif dataset_name.startswith("9월 예측"):
        st.dataframe(df_sep_fc, use_container_width=True, height=420)
    else:
        st.dataframe(df_sep_hist, use_container_width=True, height=420)
    st.caption("`type` 컬럼으로 관측치/예측치를 구분합니다. 결측치는 기상청 API 수집 단계에서 선형보간으로 이미 처리되었습니다.")

st.markdown("---")
st.caption("이 대시보드는 학습 미션의 보너스 심화 과제로 제작되었으며, 9월 예측은 실제 수치예보가 아닌 통계적 baseline 추정입니다.")
