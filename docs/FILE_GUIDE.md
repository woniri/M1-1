# 🗂️ 파일 가이드 — 폴더 구성, 실행 방법, 결과 활용법

## 1. 폴더 전체 지도

```
.
├── README.md                    → 프로젝트 개요, 실행 방법, 요구사항 체크리스트
│
├── docs/
│   ├── REPORT.md                → 최종 분석 리포트 (제출 핵심 산출물)
│   ├── ANALYSIS_EXPLANATION.md  → 수식·차트 심층 해설
│   ├── LEARNING_GUIDE.md        → 초보자 종합 학습서
│   ├── TUTORIAL.md              → 초보자 실습 가이드 (판다스 문법)
│   └── FILE_GUIDE.md            → (이 문서) 실행/활용 안내
│
├── 코드 (Docker 컨테이너 안에서 실행)
│   ├── fetch_kma_data.py         → 기상청 ASOS API 실측 데이터 수집 (API 키 필요)
│   ├── analysis.py               → 통계 분석 + 4대 시각화 (data/의 CSV만 있으면 API 키 불필요)
│   ├── timeseries_advanced.py    → (보너스) STL 분해 + 예측 모델 백테스트
│   ├── dashboard.py              → (보너스) Streamlit 인터랙티브 대시보드
│   ├── tutorial_practice.py      → 초보자 실습용 미니 스크립트
│   └── requirements.txt          → 의존성 목록
│
└── 결과물
    ├── data/*.csv                 → 기상청 실측 데이터 + 백테스트 결과 (이미 포함됨)
    └── images/*.png                → analysis.py(4종) + timeseries_advanced.py(2종) + 실습(1종) 차트
```

## 2. 실행 방법 (Docker 기반)

이 프로젝트는 로컬 `venv`를 만들지 않고, `Dockerfile` + `docker-compose.yml`로 구성된 컨테이너 안에서만 파이썬을 실행합니다.

### Step 1. 이미지 빌드 (최초 1회)

```bash
./run.sh build
```

### Step 2. 분석 실행 — API 키 없이 바로 가능

이 저장소에는 이미 실측 데이터(`data/*.csv`)가 포함되어 있으므로, **기상청 API 키가 없어도** 바로 분석·시각화를 재현할 수 있습니다.

```bash
./run.sh analyze
```

실행하면 터미널에 다음이 순서대로 출력됩니다:
1. 데이터 로드 로그
2. 연도별 통계 표(연도, 평균기온, 폭염일수, 열대야일수)
3. 올해 vs 과거 평균 비교 요약(편차는 부호 포함 — 예: `-5.2일`처럼 음수도 정상 출력)
4. `images/` 폴더에 PNG 4개 생성 로그

### Step 3. (선택, API 키 필요) 데이터를 새로 수집하고 싶다면

`analysis.py`는 데이터를 읽기만 합니다. 데이터 자체를 최신 날짜 기준으로 새로 받아오려면:

```bash
export KMA_SERVICE_KEY="발급받은_인증키"    # data.go.kr에서 개인 발급
./run.sh fetch
```

- 인증키가 없으면 `run.sh`가 즉시 안내 메시지를 출력하고 종료합니다.
- `run.sh fetch`는 호스트의 `KMA_SERVICE_KEY`를 컨테이너 실행 시점에만 `-e` 옵션으로 전달합니다 — 이미지·코드에는 저장되지 않습니다.
- 실행하는 "오늘" 날짜를 기준으로 어제까지의 실측 데이터를 수집하므로, 시간이 지난 뒤 재실행하면 실측 구간이 늘어나고 예측 구간이 줄어들며 수치가 달라집니다. **재현성이 필요하면 이미 저장된 `data/*.csv`를 건드리지 마세요.**
- 실행 후 `./run.sh analyze`를 다시 실행해 차트를 갱신하세요.

### Step 3-1. (선택, 보너스) STL 분해 + 예측 모델 백테스트

```bash
./run.sh timeseries
```

`analysis.py`와 마찬가지로 `data/*.csv`만 있으면 API 키 없이 바로 실행됩니다. `images/05_stl_decomposition.png`·`06_forecast_backtest_comparison.png`와 `data/forecast_backtest_results.csv`·`data/september_forecast_model_comparison.csv`가 생성됩니다. 자세한 해석은 `docs/ANALYSIS_EXPLANATION.md` 7장, `docs/REPORT.md` 부록을 참고하세요.

### Step 3-2. (선택, 보너스) 인터랙티브 대시보드 기동

```bash
./run.sh dashboard
```

Streamlit 기반 웹 대시보드가 `http://localhost:8501`에서 뜹니다(종료: 터미널에서 `Ctrl+C`). `data/*.csv`와 `images/*.png`만 있으면 API 키 없이 바로 실행되며, KPI 카드·연도 선택형 인터랙티브 타임라인·정적 차트 갤러리·STL/백테스트 결과·원본 데이터 탐색 탭으로 구성됩니다. 데이터를 갱신했다면(`./run.sh fetch` 또는 `./run.sh timeseries` 재실행) 브라우저를 새로고침하면 반영됩니다.

**배포판**: Streamlit Community Cloud에 `woniri/M1-1` 저장소(`main` 브랜치, `dashboard.py`)를 연동해 **https://seoul-summer.streamlit.app** 로 공개 배포되어 있습니다. 저장소에 커밋을 푸시하면 자동으로 재배포됩니다.

### Step 4. (선택) 초보자 실습 스크립트

```bash
./run.sh tutorial
```

`data/summer_climate.csv`를 불러와 필터링·집계·시각화를 한 번씩 연습해보는 미니 스크립트입니다.

### Step 5. 결과 확인

- `docs/REPORT.md`를 마크다운 뷰어(VS Code, GitHub 등)로 열면 `images/*.png`가 문서 안에 바로 보입니다.
- CSV는 엑셀/Numbers로 바로 열립니다.

## 3. 각 산출물을 어떻게 "활용"하면 되는가

| 산출물 | 활용 방법 |
| :--- | :--- |
| `docs/REPORT.md` | 미션 제출용 핵심 문서. GitHub에 올리면 이미지가 자동으로 렌더링됩니다. |
| `images/*.png` | 발표 자료에 그대로 붙여넣기 가능한 고해상도(200dpi) 이미지 |
| `data/*.csv` | 엑셀 피벗테이블, Google Sheets, 다른 파이썬 스크립트의 입력으로 재사용 가능. `type` 컬럼으로 관측치/예측치 구분 |
| `fetch_kma_data.py` | 다른 지점·기간으로 바로 재사용 가능한 실측 데이터 수집 템플릿 |
| `analysis.py` | 임계값(33℃/25℃)이나 연도 범위만 바꾸면 다른 분석에도 재사용 가능한 템플릿 |

### 다른 주제로 재활용하는 법 (예: 다른 도시, 다른 기간)

```bash
export KMA_SERVICE_KEY="발급받은_인증키"
./run.sh fetch --station-id 159 --start-year 2019 --end-year 2024 --location-name 부산
./run.sh analyze
```

| 옵션 | 환경변수 대안 | 기본값 | 설명 |
| :--- | :--- | :---: | :--- |
| `--station-id` | `KMA_STATION_ID` | `108`(서울) | 기상청 ASOS 지점코드 — 주요 지점: 서울 108, 부산 159, 인천 112, 대구 143, 광주 156, 대전 133, 제주 184 |
| `--start-year` | `KMA_START_YEAR` | `2021` | 수집 시작 연도 |
| `--end-year` | `KMA_END_YEAR` | `2026` | 수집 종료 연도(진행 중인 해도 가능 — 자동으로 어제까지만 수집) |
| `--location-name` | `KMA_LOCATION_NAME` | `서울` | 실행 로그에 표시할 지역 이름 |

지역/기간을 바꿔도 `analysis.py`는 코드 수정이 필요 없습니다. 다만 차트 제목의 "서울" 표기나 문서에 서술된 지역명은 별도로 고쳐야 합니다.

## 4. 트러블슈팅

| 증상 | 원인 | 해결 |
| :--- | :--- | :--- |
| `docker: command not found` | Docker(또는 OrbStack)가 설치/실행 중이지 않음 | Docker Desktop 또는 OrbStack을 설치하고 실행한 뒤 재시도 |
| `❌ data/ 폴더에 필요한 CSV 파일이 없습니다` | `data/*.csv`가 삭제된 상태 | 이 저장소에는 기본적으로 CSV가 포함되어 있어야 합니다. 없다면 2장 Step 3대로 API 키를 발급받아 `./run.sh fetch` 실행 |
| `❌ 환경변수 KMA_SERVICE_KEY가 설정되어 있지 않습니다` | `export KMA_SERVICE_KEY=...`를 실행하지 않음 | 같은 터미널 세션에서 export 후 바로 `./run.sh fetch` 실행 (터미널을 새로 열면 다시 export 필요) |
| 차트의 한글이 네모(□)로 깨짐 | Docker 밖에서 직접 실행한 경우 | `Dockerfile`에 `fonts-nanum`이 이미 설치되어 있어 컨테이너 안에서는 정상 출력됩니다. 반드시 `./run.sh`로 실행하세요. |
