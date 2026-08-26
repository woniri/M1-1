#!/bin/bash
set -e
cd "$(dirname "$0")"

case "$1" in
  build)
    echo "🔨 [Docker] M1-1-final 분석 이미지 빌드 중..."
    docker compose build
    ;;
  fetch)
    shift
    if [ -z "$KMA_SERVICE_KEY" ]; then
      echo "❌ 환경변수 KMA_SERVICE_KEY가 설정되어 있지 않습니다."
      echo '   예) export KMA_SERVICE_KEY="발급받은_인증키" 후 다시 실행하세요.'
      exit 1
    fi
    echo "🌐 [Docker] 기상청 실측 데이터 수집 중... (옵션: $*)"
    docker compose run --rm -e KMA_SERVICE_KEY="$KMA_SERVICE_KEY" analytics python fetch_kma_data.py "$@"
    ;;
  analyze)
    echo "🚀 [Docker] 기후 분석 스크립트 실행 중..."
    docker compose run --rm analytics python analysis.py
    ;;
  timeseries)
    echo "🔬 [Docker] STL 시계열 분해 + 예측 백테스트 실행 중..."
    docker compose run --rm analytics python timeseries_advanced.py
    ;;
  tutorial)
    echo "🔰 [Docker] 초보자 실습 스크립트 실행 중..."
    docker compose run --rm analytics python tutorial_practice.py
    ;;
  down)
    docker compose down
    ;;
  *)
    if [ -n "$1" ]; then
      echo "▶️ [Docker] 실행: $@"
      docker compose run --rm analytics python "$@"
    else
      echo "============================================================"
      echo "📊 M1-1-final 기후 분석 Docker 실행 도우미"
      echo "============================================================"
      echo "사용법:"
      echo "  ./run.sh build             # Docker 이미지 빌드"
      echo "  ./run.sh fetch              # 기상청 실측 데이터 수집 (KMA_SERVICE_KEY 필요)"
      echo "  ./run.sh fetch --station-id 159 --start-year 2019 --end-year 2024 --location-name 부산"
      echo "                              # 다른 지점/기간으로 재수집"
      echo "  ./run.sh analyze            # 분석 + 시각화 실행"
      echo "  ./run.sh timeseries         # STL 분해 + 예측 백테스트(보너스 심화) 실행"
      echo "  ./run.sh tutorial           # 초보자 실습 스크립트 실행"
      echo "  ./run.sh <script.py>        # 임의의 파이썬 스크립트 Docker 내 실행"
      echo "============================================================"
    fi
    ;;
esac
