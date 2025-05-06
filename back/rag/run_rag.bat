@echo on
setlocal

echo 현재 작업 디렉토리 확인:
cd

:: 가상환경 생성
if not exist "app\venv" (
    echo [🔧] 가상환경 생성 중...
    python -m venv app\venv
)

:: 가상환경 활성화
echo [🚀] 가상환경 활성화...
call app\venv\Scripts\activate

:: 의존성 설치
echo [📦] requirements 설치 중...
cd app
pip install -r requirements.txt
cd ..

:: 서버 실행
echo [🔥] FastAPI 서버 실행 중...
python -m uvicorn app.main:app --reload --port 9000

endlocal
pause
