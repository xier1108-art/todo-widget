@echo off
chcp 65001 > nul
echo.
echo ====================================================
echo   할일위젯 EXE 빌드
echo ====================================================
echo.

:: PyInstaller 설치 확인
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [설치 중] PyInstaller 설치...
    pip install pyinstaller
)

:: pystray / Pillow 설치 확인
python -c "import pystray, PIL" 2>nul
if errorlevel 1 (
    echo [설치 중] pystray, Pillow 설치...
    pip install pystray Pillow
)

echo.
echo [빌드 중] 할일위젯.exe 생성 중...
pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "할일위젯" ^
    --add-data "todos.json;." 2>nul ^
    todo_widget.py

if errorlevel 1 (
    echo.
    echo [오류] 빌드 실패. 위 메시지를 확인하세요.
    pause
    exit /b 1
)

echo.
echo ====================================================
echo   완료! dist\할일위젯.exe 에 저장되었습니다.
echo   todos.json 파일을 같은 폴더에 함께 복사하세요.
echo ====================================================
echo.
pause
