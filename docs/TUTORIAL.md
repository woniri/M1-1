# 🔰 초보자용 단계별 실습 가이드

이 문서는 `tutorial_practice.py`를 따라가며 판다스(pandas) 기초 문법을 익히는 가이드입니다. 코드를 직접 실행해보려면 [`FILE_GUIDE.md`](FILE_GUIDE.md)의 실행 방법을 먼저 확인하세요.

```bash
./run.sh tutorial
```

## Step 1. 데이터 로드 및 구조 확인

```python
df = pd.read_csv(DATA_PATH, parse_dates=["date"])
print(df.head(3))
```

`pd.read_csv`로 CSV를 데이터프레임으로 불러옵니다. `parse_dates=["date"]`를 지정하면 `date` 컬럼이 문자열이 아니라 날짜 타입으로 인식되어, 이후 `.dt.year`, `.dt.month` 같은 날짜 연산을 쓸 수 있습니다.

## Step 2. 불리언 인덱싱(조건 검색)

```python
super_heat = df[df["max_temp"] >= 35.0]
```

`df["max_temp"] >= 35.0`은 각 행이 조건을 만족하는지 여부를 `True`/`False`로 반환합니다. 이 결과를 `df[...]`에 넣으면 조건을 만족하는 행만 골라낸 새 데이터프레임이 됩니다.

조건을 여러 개 합칠 때는 `&`(그리고), `|`(또는)를 쓰고, 각 조건은 괄호로 감쌉니다:

```python
trop_2026 = df[(df["year"] == 2026) & (df["is_tropical_night"] == True)]
```

## Step 3. groupby로 요약표 만들기

```python
summary = df.groupby("year").agg(
    여름평균기온=("avg_temp", "mean"),
    폭염일수=("is_heatwave", "sum"),
).reset_index()
```

`groupby("year")`는 같은 연도끼리 데이터를 묶습니다. `.agg(...)`는 묶인 그룹마다 어떤 집계(평균, 합계 등)를 할지 지정합니다. `("avg_temp", "mean")`은 "avg_temp 컬럼의 평균을 구해서 새 컬럼 이름으로 저장"이라는 뜻입니다.

## Step 4. 첫 번째 시각화

```python
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(summary["year"], summary["여름평균기온"], marker="o")
plt.savefig("images/tutorial_yearly_avg_temp.png")
```

`fig, ax = plt.subplots()`로 그래프를 그릴 도화지(`fig`)와 좌표축(`ax`)을 만들고, `ax.plot(x, y)`로 선 그래프를 그립니다. `plt.savefig(...)`로 파일로 저장합니다.

## 스스로 해보는 연습 문제

1. `df[df["month"] == 8]`을 사용해 8월의 최고기온 평균을 구해보세요. (힌트: `.["max_temp"].mean()`)
2. `summary` 데이터프레임에서 폭염일수가 가장 많았던 연도를 찾아보세요. (힌트: `.sort_values("폭염일수", ascending=False)`)
3. `fetch_kma_data.py`의 `HEATWAVE_THRESHOLD`(33.0)를 34.0으로 바꾸고 `./run.sh fetch`(API 키 필요)로 다시 수집하면 폭염일수가 어떻게 달라지는지 확인해보세요.

막히면 [`LEARNING_GUIDE.md`](LEARNING_GUIDE.md)의 핵심 개념 설명을 참고하세요.
