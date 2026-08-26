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

DEFAULT_HEATWAVE_THRESHOLD = 33.0
DEFAULT_TROPICAL_NIGHT_THRESHOLD = 25.0

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
    stl_path = os.path.join(DATA_DIR, "stl_decomposition.csv")
    df_stl = pd.read_csv(stl_path, parse_dates=["date"]) if os.path.exists(stl_path) else pd.DataFrame()
    return df_summer, df_sep_fc, df_sep_hist, df_backtest, df_compare, df_stl


def cycle_index_ticks(df):
    """5개년 여름을 이어붙인 연속 축(cycle_index)에서, 연도당 'YYYY년' 눈금 하나(그 해 구간의 중앙)와
    연도 경계에 그릴 세로선 위치를 계산한다. 실제 조사 대상이 여름뿐이므로 겨울 공백 없이 이어붙이되,
    어디가 어느 해인지는 눈금·경계선으로 표시한다."""
    mid = df.groupby("year")["cycle_index"].apply(lambda s: s.median())
    tick_vals, tick_text = list(mid.values), [f"{y}년" for y in mid.index]
    year_max = df.groupby("year")["cycle_index"].max().sort_index()
    boundaries = [v + 0.5 for v in year_max.values[:-1]]
    return tick_vals, tick_text, boundaries


@st.cache_data
def build_full_range(df_summer, df_sep_fc, df_sep_hist):
    """6~9월 전체를 아우르는 연속 일별 데이터. 사이드바의 월 범위 슬라이더가 9월까지 다룰 수 있게
    summer_climate(6~8월, 관측+예측 모두 포함) + 9월 과거 실측 + 9월 올해 예측을 하나로 합친다."""
    cols = ["date", "year", "month", "day", "avg_temp", "max_temp", "min_temp"]
    base = df_summer[cols + ["type"]].copy()
    parts = [base]
    if not df_sep_hist.empty:
        parts.append(df_sep_hist[cols].assign(type="관측치"))
    parts.append(df_sep_fc[cols].assign(type="예측치"))
    full = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    return full


df_summer, df_sep_fc, df_sep_hist, df_backtest, df_compare, df_stl = load_data()
full_range = build_full_range(df_summer, df_sep_fc, df_sep_hist)

current_year = int(df_summer["year"].max())
past_years = sorted(y for y in df_summer["year"].unique() if y < current_year)
all_years = past_years + [current_year]

# ------------------------------------------------------------------
# 헤더
# ------------------------------------------------------------------
st.title("🌦️ 서울 여름 기후 분석 & 9월 늦더위 전이 예측")
st.caption(
    f"분석 대상: 서울특별시(기상청 ASOS 108) · 관측 {past_years[0]}\\~{current_year}년 6\\~8월 · "
    f"예측 {current_year}년 9월 · 데이터 출처: [공공데이터포털](https://www.data.go.kr) 기상청_지상(종관, ASOS) 일자료 조회서비스"
)

# ------------------------------------------------------------------
# 사이드바 — 연도 선택 + 조건(기간/임계값) 탐색 컨트롤
# ------------------------------------------------------------------
st.sidebar.header("🔧 필터")
selected_years = st.sidebar.multiselect("비교에 표시할 연도", all_years, default=all_years)
st.sidebar.caption("🎛️ 조건 탐색과 📈 인터랙티브 타임라인 탭의 연도별 비교 차트에 적용됩니다. (STL 분해는 완결된 5개년 고정, 핵심 지표는 항상 전체 과거 평균 기준)")

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ 조건 탐색")
month_range = st.sidebar.select_slider(
    "여름 정의 (월 범위)", options=[6, 7, 8, 9], value=(6, 8), format_func=lambda m: f"{m}월",
)
heat_threshold = st.sidebar.slider("폭염 기준 최고기온(℃)", 30.0, 36.0, DEFAULT_HEATWAVE_THRESHOLD, 0.5)
trop_threshold = st.sidebar.slider("열대야 기준 최저기온(℃)", 22.0, 27.0, DEFAULT_TROPICAL_NIGHT_THRESHOLD, 0.5)
st.sidebar.caption(
    "아래 핵심 지표와 🎛️ 조건 탐색 탭의 차트는 이 설정에 맞춰 즉시 재계산됩니다. 예를 들어 월 범위를 7\\~9월로 바꾸면 "
    "`docs/REPORT.md`의 '여름을 7\\~9월로 재정의하면?' 반례 검토를 여기서 직접 재현해볼 수 있습니다."
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**산출물**\n"
    "- `docs/REPORT.md` 최종 리포트\n"
    "- `docs/ANALYSIS_EXPLANATION.md` 방법론 해설\n"
    "- `docs/LEARNING_GUIDE.md` 학습서\n"
)
st.sidebar.markdown("이 대시보드는 `data/*.csv`를 읽기만 하며, 데이터 자체를 갱신하려면 `./run.sh analyze` / `./run.sh timeseries`를 다시 실행하세요.")

# ------------------------------------------------------------------
# 조건에 따른 동적 집계
# ------------------------------------------------------------------
m_start, m_end = month_range
filtered = full_range[(full_range["month"] >= m_start) & (full_range["month"] <= m_end)].copy()
filtered["is_heatwave"] = filtered["max_temp"] >= heat_threshold
filtered["is_tropical_night"] = filtered["min_temp"] >= trop_threshold
dyn_summary = filtered.groupby("year").agg(
    avg_temp=("avg_temp", "mean"),
    heatwave_days=("is_heatwave", "sum"),
    tropical_nights=("is_tropical_night", "sum"),
).reset_index()

curr_rows = dyn_summary[dyn_summary["year"] == current_year]
past_dyn = dyn_summary[dyn_summary["year"] < current_year]
uses_forecast = not filtered[(filtered["year"] == current_year) & (filtered["type"] == "예측치")].empty

# ------------------------------------------------------------------
# KPI 카드 — 사이드바 조건에 따라 실시간 재계산
# ------------------------------------------------------------------
month_label = f"{m_start}~{m_end}월" if m_start != m_end else f"{m_start}월"  # Plotly 제목 등 비-마크다운 컨텍스트용 (물결표 이스케이프 없음)
month_label_md = month_label.replace("~", "\\~")  # st.markdown/caption 등 마크다운 컨텍스트용
st.subheader(f"핵심 지표 ({month_label_md} 기준, 폭염 ≥{heat_threshold:.1f}℃ · 열대야 ≥{trop_threshold:.1f}℃)")

if curr_rows.empty or past_dyn.empty:
    st.warning("선택한 조건에 해당하는 데이터가 부족합니다. 사이드바에서 월 범위를 조정해주세요.")
else:
    curr = curr_rows.iloc[0]
    past_avg_temp = past_dyn["avg_temp"].mean()
    past_heat = past_dyn["heatwave_days"].mean()
    past_trop = past_dyn["tropical_nights"].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric(f"{current_year}년 평균기온", f"{curr['avg_temp']:.2f}℃", f"{curr['avg_temp'] - past_avg_temp:+.2f}℃ (과거 {len(past_dyn)}개년 평균 대비)")
    col2.metric(f"{current_year}년 폭염일수", f"{int(curr['heatwave_days'])}일", f"{curr['heatwave_days'] - past_heat:+.1f}일 (과거 평균 {past_heat:.1f}일)", delta_color="inverse")
    col3.metric(f"{current_year}년 열대야일수", f"{int(curr['tropical_nights'])}일", f"{curr['tropical_nights'] - past_trop:+.1f}일 (과거 평균 {past_trop:.1f}일)", delta_color="inverse")
    note = (
        f"괄호 안은 과거 {len(past_dyn)}개년({past_years[0]}\\~{past_years[-1]}) 평균 대비 증감입니다. "
        "폭염·열대야는 과거보다 **적을수록**(초록 하향 화살표) 온건한 여름이었다는 뜻이라 델타 색상을 반대로 표시했습니다."
    )
    if uses_forecast:
        note += f" ⚠️ 선택한 월 범위에 {current_year}년 9월이 포함되어 있어 그 구간은 실측이 아닌 **베이스라인 예측치**가 섞여 있습니다."
    st.caption(note)

st.markdown("---")

# ------------------------------------------------------------------
# 탭 구성
# ------------------------------------------------------------------
tab_explore, tab_timeline, tab_static, tab_stl, tab_data = st.tabs(
    ["🎛️ 조건 탐색", "📈 인터랙티브 타임라인", "📊 정적 차트 (원본)", "🔬 STL 분해 & 예측 백테스트", "🗂️ 데이터 탐색"]
)

with tab_explore:
    st.subheader("사이드바 조건에 따라 다시 그려지는 연도별 비교")
    is_default = (month_range == (6, 8)) and heat_threshold == DEFAULT_HEATWAVE_THRESHOLD and trop_threshold == DEFAULT_TROPICAL_NIGHT_THRESHOLD
    if is_default:
        st.info("현재 사이드바 설정은 미션 원본 기준(6\\~8월, 폭염 33℃, 열대야 25℃)과 동일합니다 — 왼쪽에서 값을 바꿔보세요.")
    else:
        st.success(f"원본 기준(6\\~8월·33℃·25℃)과 다른 설정으로 보는 중입니다: **{month_label_md}, 폭염 ≥{heat_threshold:.1f}℃, 열대야 ≥{trop_threshold:.1f}℃**")

    dyn_summary_view = dyn_summary[dyn_summary["year"].isin(selected_years)] if selected_years else dyn_summary.iloc[0:0]

    if not selected_years:
        st.info("사이드바에서 '비교에 표시할 연도'를 하나 이상 선택하세요.")
    elif dyn_summary_view.empty:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    else:
        fig_bar = go.Figure()
        x_labels = dyn_summary_view["year"].astype(str) + "년"
        fig_bar.add_trace(go.Bar(x=x_labels, y=dyn_summary_view["heatwave_days"], name=f"폭염일수(≥{heat_threshold:.1f}℃)", marker_color="#ef4444"))
        fig_bar.add_trace(go.Bar(x=x_labels, y=dyn_summary_view["tropical_nights"], name=f"열대야일수(≥{trop_threshold:.1f}℃)", marker_color="#3b82f6"))
        fig_bar.update_layout(
            barmode="group", xaxis_title="연도", yaxis_title="발생 일수(일)", height=440,
            legend=dict(orientation="h", y=-0.2), title=f"연도별 폭염·열대야 일수 ({month_label} 기준)",
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption(
            "이 막대그래프는 왼쪽 사이드바의 **'비교에 표시할 연도'**로 대상 연도를, **월 범위·임계값**으로 집계 기준을 정하면 "
            "원본 CSV에서 즉시 다시 계산됩니다. 예: 월 범위를 6\\~8월에서 7\\~9월로 옮기면 6월(폭염 적음)이 빠지고 9월(예측 기준, 폭염 0일)이 들어와 "
            "총 폭염일수가 달라지는 것을 바로 확인할 수 있습니다 — "
            f"`docs/REPORT.md`의 반례 검토(7\\~9월 재정의 시 {current_year}년 평균기온·폭염일수 재계산)를 숫자로 직접 재현하는 셈입니다."
        )

        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=dyn_summary_view["year"], y=dyn_summary_view["avg_temp"], mode="lines+markers", line=dict(color="#f59e0b", width=2.5), marker=dict(size=9)))
        fig_temp.update_layout(xaxis_title="연도", yaxis_title="평균기온(℃)", height=320, title=f"연도별 평균기온 ({month_label} 기준)")
        st.plotly_chart(fig_temp, use_container_width=True)
        st.caption("월 범위를 바꾸면 이 선도 함께 움직입니다 — 예를 들어 6월만 선택하면 아직 본격적인 더위가 오기 전이라 다른 달보다 낮은 평균기온대가 나타납니다.")

        st.markdown(f"**{month_label_md} 기준 연도별 집계표** (선택된 {len(selected_years)}개년)")
        st.dataframe(dyn_summary_view.round(2).rename(columns={"year": "연도", "avg_temp": "평균기온(℃)", "heatwave_days": "폭염일수", "tropical_nights": "열대야일수"}), use_container_width=True, hide_index=True)

with tab_timeline:
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
        fig.add_hline(y=heat_threshold, line_dash="dot", line_color="#dc2626", annotation_text=f"폭염 기준 {heat_threshold:.1f}℃")
        fig.update_layout(
            xaxis_title="여름 경과 일수 (0 = 6월 1일)", yaxis_title="최고기온(℃)",
            height=480, hovermode="x unified", legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "**읽는 법**: x축은 6월 1일을 0으로 놓은 '여름 경과 일수'라, 서로 다른 해를 같은 기준으로 겹쳐 비교할 수 있습니다. "
            f"빨간 점선(사이드바에서 설정한 폭염 기준 {heat_threshold:.1f}℃)을 넘는 구간이 폭염일입니다. 범례를 클릭해 특정 연도를 껐다 켜면서, 고온 구간이 "
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
        fig2.add_hline(y=heat_threshold, line_dash="dot", line_color="#dc2626")
        fig2.add_hline(y=trop_threshold, line_dash="dot", line_color="#2563eb")
        fig2.update_layout(xaxis_title="날짜", yaxis_title="기온(℃)", height=480, hovermode="x unified", legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "**읽는 법**: 실선(빨강=최고기온, 파랑=최저기온)은 관측 마지막 날까지의 실측치이고, 그 뒤로 이어지는 "
            "점선이 9월 예측(베이스라인 모델)입니다. 보라색 점선은 참고용으로 함께 그린 Holt 모델 예측인데, "
            "9월 하순으로 갈수록 베이스라인(하강)과 반대로 계속 올라가는 것이 보입니다 — 아래 'Holt 모델이 왜 이렇게 예측했나' 설명 참고. "
            f"가로 점선 두 개는 사이드바에서 설정한 폭염(≥{heat_threshold:.1f}℃)·열대야(≥{trop_threshold:.1f}℃) 판정 기준선입니다."
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

with tab_static:
    st.subheader("analysis.py가 생성한 4대 정적 차트 (원본 미션 기준: 6\\~8월, 폭염 33℃, 열대야 25℃ 고정)")
    st.caption("이 4개는 미션 제출용으로 고정된 기준값을 써서 미리 계산·저장해둔 원본 이미지입니다. 다른 조건으로 직접 탐색하려면 🎛️ 조건 탐색 탭을 이용하세요.")
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
    for fname, (caption, detail) in charts.items():
        path = os.path.join(IMG_DIR, fname)
        if os.path.exists(path):
            st.image(path, caption=caption, use_container_width=True)
            st.caption(detail)
            st.markdown("")
        else:
            st.warning(f"{fname} 이(가) 없습니다 — ./run.sh analyze 를 먼저 실행하세요.")

with tab_stl:
    st.subheader("(보너스) STL 시계열 분해 및 예측 모델 백테스트")
    st.markdown(
        "5개년(2021\\~2025) 여름 사이클을 이어붙여 **추세/계절성/잔차**로 분해하고, "
        "기존 베이스라인(평년+편차감쇄) 예측 모델을 통계적으로 더 정교한 **Holt 지수평활** 모델과 "
        "5개년 leave-one-year-out 백테스트로 정면 비교했습니다."
    )

    if df_stl.empty:
        st.warning("stl_decomposition.csv 이(가) 없습니다 — ./run.sh timeseries 를 먼저 실행하세요.")
    else:
        stl_years = sorted(df_stl["year"].unique())
        first_year, last_year = stl_years[0], stl_years[-1]
        season_len = int(df_stl[df_stl["year"] == first_year]["season_day"].max())

        st.markdown("#### ① 추세 (Trend) — 5개년 사이 여름철 기저 기온의 방향")
        tick_vals, tick_text, year_boundaries = cycle_index_ticks(df_stl)
        date_str = df_stl["date"].dt.strftime("%Y-%m-%d")
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=df_stl["cycle_index"], y=df_stl["observed"], name="실측 평균기온", line=dict(color="#cbd5e1", width=1), opacity=0.7, customdata=date_str, hovertemplate="%{customdata}<br>실측 %{y:.1f}℃<extra></extra>"))
        fig_trend.add_trace(go.Scatter(x=df_stl["cycle_index"], y=df_stl["trend"], name="STL 추세", line=dict(color="#dc2626", width=2.5), customdata=date_str, hovertemplate="%{customdata}<br>추세 %{y:.1f}℃<extra></extra>"))
        for b in year_boundaries:
            fig_trend.add_vline(x=b, line_dash="dot", line_color="#d1d5db", line_width=1)
        fig_trend.update_layout(xaxis_title="연도 (5개년 여름을 이어붙인 축 — 점선=연도 경계)", yaxis_title="평균기온(℃)", height=380, hovermode="x unified", legend=dict(orientation="h", y=-0.25))
        fig_trend.update_xaxes(tickmode="array", tickvals=tick_vals, ticktext=tick_text)
        y_pad = (df_stl["observed"].max() - df_stl["observed"].min()) * 0.05
        fig_trend.update_yaxes(range=[df_stl["observed"].min() - y_pad, df_stl["observed"].max() + y_pad])
        st.plotly_chart(fig_trend, use_container_width=True)
        trend_start = df_stl[df_stl["year"] == first_year]["trend"].mean()
        trend_end = df_stl[df_stl["year"] == last_year]["trend"].mean()
        st.caption(
            f"연한 회색 선이 실측 평균기온(날마다 들쭉날쭉), 굵은 빨간 선이 그 안에서 뽑아낸 장기 추세입니다. "
            f"{first_year}년 초입 평균 {trend_start:.2f}℃ → {last_year}년 말미 평균 {trend_end:.2f}℃로 "
            f"**{trend_end - trend_start:+.2f}℃** 이동했습니다 — 방향은 상승이지만, 표본이 {len(stl_years)}개년뿐이라 "
            "이것만으로 장기 온난화라 단정하기는 이릅니다(`README.md` 9장 향후 발전 과제 참고). "
            "**참고**: 범례를 눌러 실측(회색)을 꺼도 y축 범위는 고정되어 있습니다 — 추세의 실제 변화폭(약 1\\~2℃)은 "
            "실측의 하루 변동폭(약 15℃)보다 훨씬 작기 때문에, 축이 다시 확대되면 작은 변화가 커 보이는 착시가 생길 수 있어서입니다."
        )

        st.markdown("#### ② 계절성 (Seasonal) — 매년 반복되는 '여름 내부' 패턴")
        fig_season = go.Figure()
        cmap_stl = ["#94a3b8", "#60a5fa", "#34d399", "#fbbf24", "#f97316", "#dc2626"]
        for i, y in enumerate(stl_years):
            df_y = df_stl[df_stl["year"] == y].sort_values("season_day")
            fig_season.add_trace(go.Scatter(x=df_y["season_day"], y=df_y["seasonal"], name=f"{y}년", line=dict(color=cmap_stl[i % len(cmap_stl)], width=1.8)))
        fig_season.update_layout(xaxis_title="여름 경과 일수 (1 = 6월 1일)", yaxis_title="계절성 성분(℃)", height=380, hovermode="x unified", legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig_season, use_container_width=True)
        season_first = df_stl[df_stl["year"] == first_year].sort_values("season_day")
        peak_row = season_first.loc[season_first["seasonal"].idxmax()]
        peak_day = int(peak_row["season_day"])
        peak_date_approx = pd.Timestamp(f"{first_year}-06-01") + pd.Timedelta(days=peak_day - 1)
        seasonal_amp = season_first["seasonal"].max() - season_first["seasonal"].min()
        st.caption(
            f"연도별 곡선이 서로 거의 겹쳐 보인다면, 그해그해 날씨와 무관하게 '6월 서늘 → 여름 경과일 {peak_day}일차"
            f"(≈{peak_date_approx.strftime('%m/%d')} 전후) 정점 → 9월 하강'이라는 계절 패턴 자체는 5년 내내 안정적으로 "
            f"반복됐다는 뜻입니다. 진폭(정점-저점)은 **{seasonal_amp:.2f}℃**로, 이것이 매년 반복되는 여름의 '기본 굴곡'입니다."
        )

        st.markdown("#### ③ 잔차 (Residual) — 추세·계절성으로 설명 안 되는 날씨 노이즈")
        resid_std = df_stl["resid"].std()
        colors = np.where(df_stl["resid"] >= 0, "#ef4444", "#3b82f6")
        fig_resid = go.Figure()
        fig_resid.add_trace(go.Bar(x=df_stl["cycle_index"], y=df_stl["resid"], marker_color=colors, name="잔차", customdata=date_str, hovertemplate="%{customdata}<br>잔차 %{y:+.2f}℃<extra></extra>"))
        fig_resid.add_hline(y=0, line_color="#6b7280", line_width=1)
        for b in year_boundaries:
            fig_resid.add_vline(x=b, line_dash="dot", line_color="#d1d5db", line_width=1)
        fig_resid.update_layout(xaxis_title="연도 (5개년 여름을 이어붙인 축 — 점선=연도 경계)", yaxis_title="잔차(℃)", height=380, showlegend=False)
        fig_resid.update_xaxes(tickmode="array", tickvals=tick_vals, ticktext=tick_text)
        st.plotly_chart(fig_resid, use_container_width=True)
        top_hot = df_stl.nlargest(3, "resid")[["date", "observed", "resid"]]
        top_cold = df_stl.nsmallest(3, "resid")[["date", "observed", "resid"]]
        hot_str = ", ".join(f"{r.date.strftime('%Y-%m-%d')}({r.resid:+.2f}℃)" for r in top_hot.itertuples())
        cold_str = ", ".join(f"{r.date.strftime('%Y-%m-%d')}({r.resid:+.2f}℃)" for r in top_cold.itertuples())
        st.caption(
            f"빨강 막대(+)는 그 날짜의 추세·계절성 예상치보다 더 더웠던 날, 파랑 막대(-)는 더 서늘했던 날입니다. "
            f"표준편차는 **{resid_std:.2f}℃**로, 이것이 STL로도 설명 안 되는 순수 날씨 변동성(폭염 스파이크, 갑작스러운 냉각 등)의 크기입니다. "
            f"막대 위에 마우스를 올리면 날짜별 정확한 값을 볼 수 있습니다. **이례적 고온 Top3**: {hot_str}. **이례적 저온 Top3**: {cold_str}."
        )

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

    st.markdown("#### 예측 모델 백테스트 — 베이스라인 vs Holt, 어느 쪽이 더 정확했나")
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

with tab_data:
    st.subheader("원본 데이터 탐색")
    dataset_name = st.selectbox(
        "데이터셋 선택",
        ["여름 관측/예측 (summer_climate)", "9월 예측 (september_forecast)", "9월 과거 실측 (september_observed_history)", "STL 분해 결과 (stl_decomposition)"],
    )
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
        "STL 분해 결과 (stl_decomposition)": (
            "🔬 탭의 추세/계절성/잔차 차트를 그리는 데 쓰인 원본 수치입니다. `cycle_index`는 5개년을 122일씩 이어붙인 "
            "연속 인덱스, `observed`는 실측 평균기온, `trend`·`seasonal`·`resid`가 STL 분해 결과입니다."
        ),
    }
    if dataset_name.startswith("여름"):
        st.dataframe(df_summer, use_container_width=True, height=420)
    elif dataset_name.startswith("9월 예측"):
        st.dataframe(df_sep_fc, use_container_width=True, height=420)
    elif dataset_name.startswith("9월 과거"):
        st.dataframe(df_sep_hist, use_container_width=True, height=420)
    else:
        st.dataframe(df_stl, use_container_width=True, height=420)
    st.caption(dataset_notes[dataset_name])
    if not dataset_name.startswith("STL"):
        st.caption(
            "공통: `type` 컬럼으로 관측치/예측치를 구분합니다. 결측치는 기상청 API 수집 단계에서 선형보간으로 이미 처리되었습니다. "
            "`is_heatwave`·`is_tropical_night` 칸의 **회색 체크(✓)는 그날이 폭염/열대야로 판정됐다는 뜻**(True)이고, "
            "**빈 네모는 기준을 넘지 않았다는 뜻**(False)입니다 — 여기 표시된 기준은 🎛️ 조건 탐색 탭의 슬라이더와 무관하게 "
            "항상 고정값(폭염 최고기온 ≥33℃, 열대야 최저기온 ≥25℃)입니다. 체크박스가 회색인 건 이 표가 읽기 전용이라서일 뿐, "
            "그 외에 다른 의미는 없습니다."
        )

st.markdown("---")
st.caption("이 대시보드는 학습 미션의 보너스 심화 과제로 제작되었으며, 9월 예측은 실제 수치예보가 아닌 통계적 baseline 추정입니다.")
