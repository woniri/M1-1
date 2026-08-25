# -*- coding: utf-8 -*-
"""초보자를 위한 파이썬 기후 데이터 분석 입문 실습 스크립트"""

import os
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "summer_climate.csv")
IMG_DIR = os.path.join(BASE_DIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)

print("=" * 60)
print("🔰 [실습 1] 데이터셋 로드 및 기본 구조 탐색")
print("=" * 60)

df = pd.read_csv(DATA_PATH, parse_dates=["date"])
print(f"• 전체 데이터 행 수: {len(df)}개")
print(f"• 데이터 컬럼 목록: {list(df.columns)}")
print("\n[상위 3개 행 미리보기]")
print(df.head(3))

print("\n" + "=" * 60)
print("🔰 [실습 2] 불리언 인덱싱(조건 검색) 활용하기")
print("=" * 60)

super_heat = df[df["max_temp"] >= 35.0]
print(f"• 전체 기간 중 35℃ 이상 초폭염 일수: 총 {len(super_heat)}일")

latest_year = int(df["year"].max())
trop_latest = df[(df["year"] == latest_year) & (df["is_tropical_night"])]
print(f"• {latest_year}년 여름철 열대야 일수: 총 {len(trop_latest)}일")

print("\n" + "=" * 60)
print("🔰 [실습 3] groupby로 연도별 기후 요약표 만들기")
print("=" * 60)

summary = df.groupby("year").agg(
    여름평균기온=("avg_temp", "mean"),
    최고기온평균=("max_temp", "mean"),
    폭염일수=("is_heatwave", "sum"),
    열대야일수=("is_tropical_night", "sum"),
).reset_index()
summary["여름평균기온"] = summary["여름평균기온"].round(2)
summary["최고기온평균"] = summary["최고기온평균"].round(2)
print(summary.to_string(index=False))

print("\n" + "=" * 60)
print("🔰 [실습 4] 나만의 첫 번째 데이터 시각화 차트 그리기")
print("=" * 60)

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(summary["year"], summary["여름평균기온"], marker="o", color="#dc2626", linewidth=2.5, markersize=8)
ax.set_title("연도별 여름철 평균기온 추이", fontsize=13, fontweight="bold", pad=12)
ax.set_xlabel("연도")
ax.set_ylabel("평균기온 (℃)")
ax.grid(True, linestyle="--", alpha=0.6)
for _, row in summary.iterrows():
    ax.annotate(f"{row['여름평균기온']}℃", xy=(row["year"], row["여름평균기온"]), xytext=(0, 7),
                textcoords="offset points", ha="center", fontweight="bold", color="#991b1b")

save_path = os.path.join(IMG_DIR, "tutorial_yearly_avg_temp.png")
plt.tight_layout()
plt.savefig(save_path, dpi=180)
plt.close()
print(f"🎉 실습 차트 생성 완료: {save_path}")

print("\n" + "=" * 60)
print("🎯 [스스로 해보는 퀴즈 미션]")
print("=" * 60)
print("1. df[df['month'] == 8]로 8월의 최고기온 평균을 구해보세요.")
print("2. summary 데이터프레임에서 폭염일수가 가장 많았던 연도를 찾아보세요.")
print("=" * 60)
