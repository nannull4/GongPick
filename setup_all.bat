@echo off
chcp 65001 >nul
echo [INFO] GongPick 프로젝트 자동 설치 시작...

REM 1. Miniconda 설치 확인
where conda >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [WARN] Miniconda가 설치되어 있지 않습니다. 설치를 시작합니다...
    curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
    echo [INFO] Miniconda 설치 중...
    start /wait "" Miniconda3-latest-Windows-x86_64.exe /InstallationType=JustMe /AddToPath=1 /S /D=%UserProfile%\Miniconda3
    del Miniconda3-latest-Windows-x86_64.exe
)

REM 2. Conda init (PowerShell에 적용)
echo [INFO] PowerShell에 conda 초기화 적용...
call %UserProfile%\Miniconda3\Scripts\conda.exe init powershell

REM 3. 기존 환경 삭제
echo [INFO] 기존 gongpick-env 제거 중...
call conda deactivate
call conda env remove -n gongpick-env -y

REM 4. 환경 재생성
echo [INFO] gongpick-env 생성 중 (environment.yml 사용)...
call conda env create -f environment.yml

REM 5. 환경 활성화 및 모델 학습
echo [INFO] 모델 학습 스크립트 실행...
call conda activate gongpick-env
python train_model.py

REM 6. 완료 안내
echo.
echo [DONE] 모든 준비가 완료되었습니다!
echo Streamlit 실행 방법:
echo     conda activate gongpick-env
echo     streamlit run app/streamlit_app.py
echo.
pause
