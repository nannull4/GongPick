@echo off
chcp 65001 >nul
powershell -command "$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8"

echo [INFO] GongPick ������Ʈ �ڵ� ��ġ ����...

REM 1. Miniconda ��ġ Ȯ��
where conda >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [WARN] Miniconda�� ��ġ�Ǿ� ���� �ʽ��ϴ�. ��ġ�� �����մϴ�...
    curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
    echo [INFO] Miniconda ��ġ ��...
    start /wait "" Miniconda3-latest-Windows-x86_64.exe /InstallationType=JustMe /AddToPath=1 /S /D=%UserProfile%\Miniconda3
    del Miniconda3-latest-Windows-x86_64.exe
)

REM 2. Conda init (PowerShell�� ����)
echo [INFO] PowerShell�� conda �ʱ�ȭ ����...
%UserProfile%\Miniconda3\Scripts\conda.exe init powershell

REM 3. ���� ȯ�� ����
echo [INFO] ���� gongpick-env ���� ��...
conda deactivate
conda env remove -n gongpick-env -y

REM 4. ȯ�� �����
echo [INFO] gongpick-env ���� �� (environment.yml ���)...
conda env create -f environment.yml

REM 5. ���� �ȳ�
echo.
echo [DONE] ��� �غ� �Ϸ�Ǿ����ϴ�!
echo ����:
echo     conda activate gongpick-env
echo     python scripts\\convert\\pdf_to_csv.py
echo     python scripts\\analysis\\kakao_search.py
echo.
pause
