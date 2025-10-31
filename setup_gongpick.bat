@echo off
chcp 65001 >nul
powershell -command "$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8"

REM echo [INFO] GongPick 프로젝트 자동 설치 시작...

REM 1. Miniconda 설치 확인
where conda >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    REM echo [WARN] Miniconda가 설치되어 있지 않습니다. 설치를 시작합니다...
    curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
    REM echo [INFO] Miniconda 설치 중...
    start /wait "" Miniconda3-latest-Windows-x86_64.exe /InstallationType=JustMe /AddToPath=1 /S /D=%UserProfile%\Miniconda3
    del Miniconda3-latest-Windows-x86_64.exe
)

REM 2. Conda init (PowerShell에 적용)
REM echo [INFO] PowerShell에 conda 초기화 적용...
%UserProfile%\Miniconda3\Scripts\conda.exe init powershell

REM 3. 기존 환경 삭제
REM echo [INFO] 기존 gongpick-env 제거 중...
conda deactivate
conda env remove -n gongpick-env -y

REM 4. 환경 재생성
REM echo [INFO] gongpick-env 생성 중 (environment.yml 사용)...
conda env create -f environment.yml

