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
st.caption(
    f"괄호 안은 과거 {len(past)}개년({past_years[0]}\\~{past_years[-1]}) 평균 대비 증감입니다. "
    "폭염·열대야는 과거보다 **적을수록**(초록 하향 화살표) 온건한 여름이었다는 뜻이라 델타 색상을 반대로 표시했습니다."
)

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
        st.caption(
            "**읽는 법**: x축은 6월 1일을 0으로 놓은 '여름 경과 일수'라, 서로 다른 해를 같은 기준으로 겹쳐 비교할 수 있습니다. "
            "빨간 점선(33℃)을 넘는 구간이 폭염일입니다. 범례를 클릭해 특정 연도를 껐다 켜면서, 고온 구간이 "
            "다른 해보다 이르거나 늦게 왔는지, 짧고 뾰족했는지(단기 스파이크) 길게 이어졌는지(장기 지속)를 비교해보세요. "
            f"굵은 빨간 선이 {current_year}년으로, 8월 초(경과일 약 60\\~70일 부근)에 고온이 몰려 있는 것을 확인할 수 있습니다."
        )

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
        st.caption(
            "**읽는 법**: 실선(빨강=최고기온, 파랑=최저기온)은 관측 마지막 날까지의 실측치이고, 그 뒤로 이어지는 "
            "점선이 9월 예측(베이스라인 모델)입니다. 보라색 점선은 참고용으로 함께 그린 Holt 모델 예측인데, "
            "9월 하순으로 갈수록 베이스라인(하강)과 반대로 계속 올라가는 것이 보입니다 — 아래 'Holt 모델이 왜 이렇게 예측했나' 설명 참고. "
            "가로 점선 두 개는 각각 폭염(33℃)·열대야(25℃) 판정 기준선입니다."
        )
        with st.expander("ℹ️ 베이스라인 모델 vs Holt 모델이란?"):
            st.markdown(
                "**베이스라인(평년값 + 편차감쇄)**: 예측하려는 날짜의 '평년값'(과거 연도들의 같은 날짜 평균기온)에서 출발해, "
                "올해 실측 구간이 평년보다 얼마나 덥거나 서늘했는지(편차)를 더하되, 예측일이 멀어질수록 그 편차의 영향력을 "
                "점점 줄여갑니다(감쇄). 평년값 자체에 '9월엔 기온이 내려간다'는 계절 패턴이 이미 반영되어 있는 것이 핵심입니다.\n\n"
                "**Holt 지수평활(Holt's Exponential Smoothing)**: 최근 관측치들로부터 '현재 수준(level)'과 '추세(trend, 기울기)'를 "
                "동시에 추정해, `예측값 = 마지막 수준 + 스텝 수 × 추세`로 미래를 연장하는 모델입니다(`statsmodels`의 감쇠추세 옵션 사용). "
                "다만 계절성 성분이 없어서, 6\\~8월의 '상승 국면'을 그대로 추세로 인식해 9월에도 계속 오르는 것으로 잘못 연장합니다 — "
                "그래서 위 그래프에서 보라색 점선이 실제로는 내려가야 할 9월에도 계속 올라가는 것입니다. "
                "5개년 백테스트에서도 이 때문에 베이스라인(MAE 1.64℃)보다 부정확(MAE 2.73℃)했습니다. 자세한 검증 과정은 "
                "🔬 STL 분해 & 예측 백테스트 탭을 참고하세요."
            )

with tab2:
    st.subheader("analysis.py가 생성한 4대 정적 차트")
    img_col1, img_col2 = st.columns(2)
    charts = {
        "01_extreme_weather_by_year.png": (
            "연도별 폭염·열대야 일수 비교",
            "빨간 막대는 폭염일수, 파란 막대는 열대야일수입니다. 2021년 18일 → 2022년 10일(최저) → 2023년 19일 → "
            "**2024\\~2025년 27일(정점)** → 2026년 15일로, 매년 꾸준히 늘어난 게 아니라 **2024년에 계단식으로 뛰었다가 "
            "2026년에 다시 내려온** 패턴입니다. 열대야도 2024년 35일, 2025년 44일(정점)로 급증했다가 2026년 22일로 하락했습니다.",
        ),
        "02_timeline_and_forecast.png": (
            f"{current_year}년 실측 타임라인 + 9월 예측",
            "실선은 실측(6/1\\~8/24), 점선은 베이스라인 예측(8/25\\~9/30)입니다. 6월엔 서늘하게 출발했다가 6/16·6/19에 "
            "일시적으로 폭염 기준을 넘었고, 7월은 폭염일이 단 2일뿐으로 잠잠했습니다. 반면 **8/1\\~8/11 사이 9일 연속 "
            "33\\~38℃대 고온**이 이어져(8/7 38.0℃로 6년 통틀어 공동 최고) 여름 폭염일수의 상당수가 이 짧은 구간에 몰렸습니다. "
            "노란 음영은 예측이 시작되는 구간을 표시합니다.",
        ),
        "03_monthly_anomaly_heatmap.png": (
            "월별 평년 대비 기온 편차 히트맵",
            "각 셀은 그 달의 평균기온이 평년(과거 5개년 같은 달 평균)보다 얼마나 높았는지(+, 빨강)/낮았는지(-, 파랑)를 "
            "나타냅니다. **2024년 8월(+2.06℃)·9월(+1.97℃)**이 가장 짙은 빨강(이상고온), **2022년 8월(-1.53℃)**이 가장 "
            "짙은 파랑(이상저온)입니다. 2026년은 6월(+0.42℃)·8월(+0.45℃)은 옅은 빨강, **7월(-0.58℃)은 옅은 파랑**으로 "
            "'고르게 더운 해'가 아니라 '월별로 엇갈린 해'였음을 보여줍니다.",
        ),
        "04_cumulative_heatwave_pace.png": (
            "연도별 누적 폭염일수 페이스",
            "여름 시작(6/1)부터 폭염일수를 누적해서 그린 선 그래프로, 계단이 가파를수록 그 시기에 폭염이 몰렸다는 뜻입니다. "
            "2024\\~2025년(진한 주황/빨강)은 여름 중반부터 가파르게 상승해 27일에 도달했고, **2026년(굵은 실선)은 8월 초"
            "(8/1\\~8/11) 구간에서만 집중적으로 오르고** 이후 평평하게 이어지다 15일에서 멈췄습니다. 점선은 9월 예측 구간으로, "
            "추가 상승이 없어 수평으로 이어집니다(9월 폭염 0일 예측).",
        ),
    }
    for i, (fname, (caption, detail)) in enumerate(charts.items()):
        path = os.path.join(IMG_DIR, fname)
        col = img_col1 if i % 2 == 0 else img_col2
        if os.path.exists(path):
            col.image(path, caption=caption, use_container_width=True)
            col.caption(detail)
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
        st.caption(
            "5개년(2021\\~2025) 여름 사이클(6/1\\~9/30, 122일씩)을 이어붙여 4단으로 분해했습니다(회색 점선=연도 경계). "
            "**추세(2번째 패널)**: 2021년 초입 평균 24.84℃ → 2025년 말미 평균 25.99℃로 **+1.15℃** 상승 — 5년 사이 "
            "여름철 기저 기온이 완만히 올랐다는 뜻이지만, 표본이 6년뿐이라 장기 온난화로 단정할 수는 없습니다. "
            "**계절성(3번째 패널)**: 사이클 54일차(≈7/24 전후)에서 정점을 찍는 진폭 **12.34℃**짜리 패턴 — 매년 반복되는 "
            "'6월 서늘 → 7월 말 정점 → 9월 하강' 곡선입니다. **잔차(4번째 패널)**: 표준편차 **1.67℃**로, 추세·계절성으로 "
            "설명 안 되는 순수 날씨 노이즈(폭염 스파이크, 갑작스러운 냉각 등)의 크기입니다."
        )
    else:
        st.warning("05_stl_decomposition.png 이(가) 없습니다 — ./run.sh timeseries 를 먼저 실행하세요.")

    with st.expander("ℹ️ Holt 지수평활이란? (베이스라인과 무엇이 다른가)"):
        st.markdown(
            "**Holt 지수평활(Holt's Exponential Smoothing)**은 단순 지수평활에 '추세(trend)' 추정을 더한 시계열 예측 모델입니다. "
            "매 시점마다 ① 현재 수준(level)과 ② 추세(기울기)를 최근 관측치 위주로 갱신하고, "
            "`예측값 = 마지막 수준 + 미래 스텝 수 × 추세`로 미래를 연장합니다. 저희는 감쇠추세(damped trend) 옵션을 써서 "
            "먼 미래로 갈수록 추세 영향력이 줄어들게 했습니다(`statsmodels.tsa.holtwinters.ExponentialSmoothing`).\n\n"
            "**핵심 한계**: 계절성 성분이 없는 순수 추세 모델이라, 6\\~8월의 '상승 국면'을 그대로 추세로 오인해 "
            "9월에도 계속 오를 것으로 잘못 연장합니다. 반면 베이스라인(평년값+편차감쇄)은 '그 날짜의 평년값' 자체에 "
            "9월 하강 패턴이 이미 반영되어 있어 구조적으로 유리합니다. 이 차이가 아래 백테스트 결과로 나타납니다."
        )

    bt_col1, bt_col2 = st.columns([1, 1])
    with bt_col1:
        backtest_path = os.path.join(IMG_DIR, "06_forecast_backtest_comparison.png")
        if os.path.exists(backtest_path):
            st.image(backtest_path, caption="연도별·모델별 9월 예측 오차(MAE) 비교", use_container_width=True)
            st.caption(
                "5개년(2021\\~2025) 각각을 '그 해라고 가정'하고 6\\~8월 실측만 보여준 뒤 9월을 예측시켜, 실제 9월 실측치와의 "
                "평균절대오차(MAE, ℃)를 비교했습니다(leave-one-year-out 백테스트). 막대가 낮을수록 정확합니다. "
                "오른쪽 차트처럼 5개년 중 4개년에서 베이스라인(빨강)이 Holt(회색)보다 오차가 작았습니다."
            )
    with bt_col2:
        if not df_backtest.empty:
            st.markdown("**5개년 백테스트 원본 결과**")
            st.dataframe(df_backtest.round(2), use_container_width=True, hide_index=True)
            st.caption(
                "`mae`(평균절대오차)·`rmse`(평균제곱근오차)는 낮을수록 정확합니다. `actual_heat_days`는 그 해 9월에 "
                "실제 관측된 폭염일수, `pred_heat_days`는 해당 모델이 예측한 폭염일수입니다."
            )
            mean_by_model = df_backtest.groupby("model")[["mae", "rmse"]].mean().round(3)
            better_model = mean_by_model["mae"].idxmin()
            st.success(f"5개년 평균 MAE 기준 더 정확한 모델: **{better_model}** ({mean_by_model.loc[better_model, 'mae']:.2f}℃)")
            st.caption(
                "더 '정교해 보이는' Holt 모델이 오히려 부정확했다는 것이 이 백테스트의 핵심 결론입니다 — 모델의 정교함보다 "
                "'문제의 구조(계절 전환점을 지나는 예측)에 모델의 가정이 맞는지'가 더 중요함을 보여주는 사례입니다."
            )
        else:
            st.warning("백테스트 결과 CSV가 없습니다 — ./run.sh timeseries 를 먼저 실행하세요.")

with tab4:
    st.subheader("원본 데이터 탐색")
    dataset_name = st.selectbox("데이터셋 선택", ["여름 관측/예측 (summer_climate)", "9월 예측 (september_forecast)", "9월 과거 실측 (september_observed_history)"])
    dataset_notes = {
        "여름 관측/예측 (summer_climate)": (
            f"{past_years[0]}\\~{current_year}년 6\\~8월 일별 기후 데이터입니다(관측 마지막 날 이후 8월 말까지의 예측 일부 포함). "
            "`is_heatwave`는 그날 최고기온이 33℃ 이상인지, `is_tropical_night`는 최저기온이 25℃ 이상인지를 나타냅니다."
        ),
        "9월 예측 (september_forecast)": (
            f"{current_year}년 9월 1\\~30일의 베이스라인(평년값+편차감쇄) 예측치입니다. 실제 수치예보가 아닌 통계적 추정치이며, "
            "🔬 탭에서 Holt 모델과 비교한 결과도 함께 참고하세요."
        ),
        "9월 과거 실측 (september_observed_history)": (
            f"{past_years[0]}\\~{past_years[-1]}년 9월의 실제 관측 데이터입니다. STL 분해와 예측 백테스트(🔬 탭)에서 "
            "'실제 정답'으로 사용된 데이터가 바로 이것입니다."
        ),
    }
    if dataset_name.startswith("여름"):
        st.dataframe(df_summer, use_container_width=True, height=420)
    elif dataset_name.startswith("9월 예측"):
        st.dataframe(df_sep_fc, use_container_width=True, height=420)
    else:
        st.dataframe(df_sep_hist, use_container_width=True, height=420)
    st.caption(dataset_notes[dataset_name])
    st.caption("공통: `type` 컬럼으로 관측치/예측치를 구분합니다. 결측치는 기상청 API 수집 단계에서 선형보간으로 이미 처리되었습니다.")

st.markdown("---")
st.caption("이 대시보드는 학습 미션의 보너스 심화 과제로 제작되었으며, 9월 예측은 실제 수치예보가 아닌 통계적 baseline 추정입니다.")
